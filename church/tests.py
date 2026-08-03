import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Member, Visitor, Department, FinanceTransaction, AttendanceSession, AttendanceRecord
from .crypto import encrypt_val, decrypt_val
from .validators import StrongPasswordValidator

User = get_user_model()

class ChurchModelTests(TestCase):
    def test_member_id_autogeneration(self):
        """Verify membership IDs are correctly generated sequentially."""
        year_yy = datetime.date.today().strftime('%y')
        
        member1 = Member.objects.create(
            full_name="John Test 1",
            gender="Male",
            date_of_birth=datetime.date(1990, 1, 1),
            phone_number="0000000001",
            address="Test address 1",
            marital_status="Single",
            baptized=True
        )
        self.assertEqual(member1.membership_id, f"RACI{year_yy}/001")
        
        member2 = Member.objects.create(
            full_name="Jane Test 2",
            gender="Female",
            date_of_birth=datetime.date(1992, 2, 2),
            phone_number="0000000002",
            address="Test address 2",
            marital_status="Married",
            baptized=False
        )
        self.assertEqual(member2.membership_id, f"RACI{year_yy}/002")

    def test_visitor_id_autogeneration(self):
        """Verify visitor IDs are generated sequentially."""
        current_year = datetime.date.today().year
        v1 = Visitor.objects.create(
            name="Guest One",
            phone="111111",
            address="Address One",
            invited_by="Flyer"
        )
        self.assertEqual(v1.visitor_id, f"VIS-{current_year}-0001")


class SecurityAndEncryptionTests(TestCase):
    def test_strong_password_validator(self):
        """Test strong password rules: uppercase, lowercase, digit, special character."""
        validator = StrongPasswordValidator(min_length=8)
        
        # Weak passwords
        with self.assertRaises(ValidationError):
            validator.validate("short")
        with self.assertRaises(ValidationError):
            validator.validate("alllowercase123!")
        with self.assertRaises(ValidationError):
            validator.validate("ALLUPPERCASE123!")
        with self.assertRaises(ValidationError):
            validator.validate("NoDigitsHere!")
        with self.assertRaises(ValidationError):
            validator.validate("NoSpecialChar123")

        # Valid strong password
        try:
            validator.validate("StrongP@ssw0rd")
        except ValidationError:
            self.fail("StrongP@ssw0rd should pass validation")

    def test_field_encryption_at_rest(self):
        """Verify data is stored encrypted at rest in database and decrypted in memory."""
        mem = Member.objects.create(
            full_name="Encrypted Member",
            gender="Male",
            date_of_birth=datetime.date(1995, 5, 5),
            phone_number="0241234567",
            address="123 Secret Street",
            marital_status="Single"
        )
        
        # In memory instance should be decrypted
        self.assertEqual(mem.phone_number, "0241234567")
        self.assertEqual(mem.address, "123 Secret Street")

        # Directly checking database row value should yield Fernet token starting with 'gAAAAA'
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT phone_number, address FROM church_member WHERE membership_id = %s", [mem.membership_id])
            row = cursor.fetchone()
            db_phone, db_address = row[0], row[1]
            self.assertTrue(db_phone.startswith('gAAAAA'), f"Expected ciphertext starting with gAAAAA, got {db_phone}")
            self.assertTrue(db_address.startswith('gAAAAA'), f"Expected ciphertext starting with gAAAAA, got {db_address}")

    def test_account_lockout_after_3_failed_attempts(self):
        """Verify account lockout after 3 consecutive failed login attempts."""
        user = User.objects.create_user(
            username='lockout_user', password='StrongPass123!', role='Secretary'
        )
        
        # Failed attempt 1
        response = self.client.post(reverse('login'), {'username': 'lockout_user', 'password': 'wrongpassword'})
        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, 1)
        self.assertFalse(user.is_locked_out())

        # Failed attempt 2
        response = self.client.post(reverse('login'), {'username': 'lockout_user', 'password': 'wrongpassword'})
        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, 2)
        self.assertFalse(user.is_locked_out())

        # Failed attempt 3 -> Triggers lockout
        response = self.client.post(reverse('login'), {'username': 'lockout_user', 'password': 'wrongpassword'})
        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, 3)
        self.assertTrue(user.is_locked_out())
        self.assertContains(response, "has been locked for 15 minutes")

        # Attempting login with CORRECT password while locked should be blocked
        response_correct = self.client.post(reverse('login'), {'username': 'lockout_user', 'password': 'StrongPass123!'})
        self.assertContains(response_correct, "temporarily locked")


class ChurchPermissionTests(TestCase):
    def setUp(self):
        self.pastor = User.objects.create_user(
            username='test_pastor', password='StrongPass123!', role='Pastor'
        )
        self.secretary = User.objects.create_user(
            username='test_secretary', password='StrongPass123!', role='Secretary'
        )
        self.finance = User.objects.create_user(
            username='test_finance', password='StrongPass123!', role='Finance Officer'
        )

    def test_unauthenticated_redirect(self):
        """Verify unauthenticated requests redirect to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_secretary_can_access_member_create(self):
        """Verify a secretary can view member registration page."""
        self.client.login(username='test_secretary', password='StrongPass123!')
        response = self.client.get(reverse('member_create'))
        self.assertEqual(response.status_code, 200)

    def test_finance_blocked_from_member_create(self):
        """Verify a Finance Officer is blocked from member registration and redirected."""
        self.client.login(username='test_finance', password='StrongPass123!')
        response = self.client.get(reverse('member_create'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_finance_blocked_from_attendance(self):
        """Verify a Finance Officer is blocked from attendance page and redirected."""
        self.client.login(username='test_finance', password='StrongPass123!')
        response = self.client.get(reverse('attendance_list'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_finance_navbar_no_attendance(self):
        """Verify the attendance link is omitted from the navigation bar for Finance Officer."""
        self.client.login(username='test_finance', password='StrongPass123!')
        response = self.client.get(reverse('finance_dashboard'))
        self.assertContains(response, 'Finance')
        self.assertNotContains(response, 'href="' + reverse('attendance_list') + '"')


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_test', password='StrongAdminPass123!', role='Super Admin'
        )
        self.regular_user = User.objects.create_user(
            username='user_test', password='StrongUserPass123!', role='Secretary'
        )

    def test_admin_can_access_user_list(self):
        self.client.login(username='admin_test', password='StrongAdminPass123!')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user_test')

    def test_non_admin_blocked_from_user_list(self):
        self.client.login(username='user_test', password='StrongUserPass123!')
        response = self.client.get(reverse('user_list'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_can_add_user(self):
        self.client.login(username='admin_test', password='StrongAdminPass123!')
        response = self.client.post(reverse('user_create'), {
            'username': 'new_staff',
            'email': 'staff@church.com',
            'first_name': 'New',
            'last_name': 'Staff',
            'role': 'Pastor',
            'phone_number': '0501234567',
            'password': 'StrongStaffPass123!',
            'confirm_password': 'StrongStaffPass123!',
            'is_active': True
        })
        self.assertRedirects(response, reverse('user_list'))
        self.assertTrue(User.objects.filter(username='new_staff').exists())
        new_user = User.objects.get(username='new_staff')
        self.assertEqual(new_user.role, 'Pastor')
        self.assertTrue(new_user.check_password('StrongStaffPass123!'))

    def test_admin_can_update_user(self):
        self.client.login(username='admin_test', password='StrongAdminPass123!')
        response = self.client.post(reverse('user_update', kwargs={'pk': self.regular_user.pk}), {
            'username': 'user_test_updated',
            'email': 'updated@church.com',
            'first_name': 'UpdatedName',
            'last_name': 'UpdatedLast',
            'role': 'Finance Officer',
            'phone_number': '0240001112',
            'is_active': True
        })
        self.assertRedirects(response, reverse('user_list'))
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.username, 'user_test_updated')
        self.assertEqual(self.regular_user.role, 'Finance Officer')

    def test_admin_can_change_user_password(self):
        self.client.login(username='admin_test', password='StrongAdminPass123!')
        response = self.client.post(reverse('user_change_password', kwargs={'pk': self.regular_user.pk}), {
            'new_password': 'NewStrongPassword123!',
            'confirm_password': 'NewStrongPassword123!'
        })
        self.assertRedirects(response, reverse('user_list'))
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password('NewStrongPassword123!'))


class QRAttendanceTests(TestCase):
    def setUp(self):
        self.secretary = User.objects.create_user(
            username='sec_test', password='StrongPass123!', role='Secretary'
        )
        self.member = Member.objects.create(
            full_name="Alice QR",
            gender="Female",
            date_of_birth=datetime.date(1995, 5, 5),
            phone_number="0241112233",
            address="Accra",
            marital_status="Single",
            membership_id="RACI26/001"
        )
        self.session = AttendanceSession.objects.create(
            service_type="Sunday Service",
            date=datetime.date.today(),
            description="Test Service"
        )

    def test_qr_code_page_access(self):
        self.client.login(username='sec_test', password='StrongPass123!')
        response = self.client.get(reverse('attendance_session_qr', kwargs={'pk': self.session.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QR Code Poster")

    def test_public_self_checkin_page_get(self):
        response = self.client.get(reverse('attendance_self_checkin', kwargs={'pk': self.session.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunday Service")

    def test_member_self_checkin_success(self):
        response = self.client.post(reverse('attendance_self_checkin', kwargs={'pk': self.session.pk}), {
            'user_type': 'member',
            'identifier': 'RACI26/001'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance Registered!")
        rec = AttendanceRecord.objects.get(session=self.session, member=self.member)
        self.assertEqual(rec.status, 'Present')

    def test_member_self_checkin_invalid_id(self):
        response = self.client.post(reverse('attendance_self_checkin', kwargs={'pk': self.session.pk}), {
            'user_type': 'member',
            'identifier': 'INVALID_ID_999'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No member found matching")





