import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Member, Visitor, Department, FinanceTransaction

User = get_user_model()

class ChurchModelTests(TestCase):
    def test_member_id_autogeneration(self):
        """Verify membership IDs are correctly generated sequentially."""
        current_year = datetime.date.today().year
        
        member1 = Member.objects.create(
            full_name="John Test 1",
            gender="Male",
            date_of_birth=datetime.date(1990, 1, 1),
            phone_number="0000000001",
            address="Test address 1",
            marital_status="Single",
            baptized=True
        )
        self.assertEqual(member1.membership_id, f"MEM-{current_year}-0001")
        
        member2 = Member.objects.create(
            full_name="Jane Test 2",
            gender="Female",
            date_of_birth=datetime.date(1992, 2, 2),
            phone_number="0000000002",
            address="Test address 2",
            marital_status="Married",
            baptized=False
        )
        self.assertEqual(member2.membership_id, f"MEM-{current_year}-0002")

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


class ChurchPermissionTests(TestCase):
    def setUp(self):
        self.pastor = User.objects.create_user(
            username='test_pastor', password='password123', role='Pastor'
        )
        self.secretary = User.objects.create_user(
            username='test_secretary', password='password123', role='Secretary'
        )
        self.finance = User.objects.create_user(
            username='test_finance', password='password123', role='Finance Officer'
        )

    def test_unauthenticated_redirect(self):
        """Verify unauthenticated requests redirect to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_secretary_can_access_member_create(self):
        """Verify a secretary can view member registration page."""
        self.client.login(username='test_secretary', password='password123')
        response = self.client.get(reverse('member_create'))
        self.assertEqual(response.status_code, 200)

    def test_finance_blocked_from_member_create(self):
        """Verify a Finance Officer is blocked from member registration and redirected."""
        self.client.login(username='test_finance', password='password123')
        response = self.client.get(reverse('member_create'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_finance_blocked_from_attendance(self):
        """Verify a Finance Officer is blocked from attendance page and redirected."""
        self.client.login(username='test_finance', password='password123')
        response = self.client.get(reverse('attendance_list'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_finance_navbar_no_attendance(self):
        """Verify the attendance link is omitted from the navigation bar for Finance Officer."""
        self.client.login(username='test_finance', password='password123')
        response = self.client.get(reverse('finance_dashboard'))
        self.assertContains(response, 'Finance')
        self.assertNotContains(response, 'href="' + reverse('attendance_list') + '"')


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_test', password='adminpassword123', role='Super Admin'
        )
        self.regular_user = User.objects.create_user(
            username='user_test', password='userpassword123', role='Secretary'
        )

    def test_admin_can_access_user_list(self):
        self.client.login(username='admin_test', password='adminpassword123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user_test')

    def test_non_admin_blocked_from_user_list(self):
        self.client.login(username='user_test', password='userpassword123')
        response = self.client.get(reverse('user_list'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_can_add_user(self):
        self.client.login(username='admin_test', password='adminpassword123')
        response = self.client.post(reverse('user_create'), {
            'username': 'new_staff',
            'email': 'staff@church.com',
            'first_name': 'New',
            'last_name': 'Staff',
            'role': 'Pastor',
            'phone_number': '0501234567',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'is_active': True
        })
        self.assertRedirects(response, reverse('user_list'))
        self.assertTrue(User.objects.filter(username='new_staff').exists())
        new_user = User.objects.get(username='new_staff')
        self.assertEqual(new_user.role, 'Pastor')
        self.assertTrue(new_user.check_password('newpassword123'))

    def test_admin_can_update_user(self):
        self.client.login(username='admin_test', password='adminpassword123')
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
        self.client.login(username='admin_test', password='adminpassword123')
        response = self.client.post(reverse('user_change_password', kwargs={'pk': self.regular_user.pk}), {
            'new_password': 'changedpassword123',
            'confirm_password': 'changedpassword123'
        })
        self.assertRedirects(response, reverse('user_list'))
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password('changedpassword123'))



