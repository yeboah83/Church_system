import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from church.models import (
    Department, Member, Visitor, AttendanceSession, AttendanceRecord,
    Event, FinanceTransaction, Sermon, Announcement
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with mock data for testing'

    def handle(self, *args, **options):
        # 1. Clear existing data to avoid duplicates
        self.stdout.write("Clearing existing data...")
        AttendanceRecord.objects.all().delete()
        AttendanceSession.objects.all().delete()
        Member.objects.all().delete()
        Visitor.objects.all().delete()
        FinanceTransaction.objects.all().delete()
        Event.objects.all().delete()
        Sermon.objects.all().delete()
        Announcement.objects.all().delete()
        Department.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # 2. Create Users
        self.stdout.write("Creating users...")
        super_admin = User.objects.filter(username='admin').first()
        if not super_admin:
            super_admin = User.objects.create_superuser('admin', 'admin@church.com', 'admin123', role='Super Admin')
        
        pastor = User.objects.create_user('pastor', 'pastor@church.com', 'pastor123', role='Pastor', phone_number='0241112223')
        secretary = User.objects.create_user('secretary', 'secretary@church.com', 'secretary123', role='Secretary', phone_number='0242223334')
        finance = User.objects.create_user('finance', 'finance@church.com', 'finance123', role='Finance Officer', phone_number='0243334445')
        
        # Department leaders
        choir_leader = User.objects.create_user('choir_leader', 'choir@church.com', 'leader123', role='Department Leader', phone_number='0244445556')
        youth_leader = User.objects.create_user('youth_leader', 'youth@church.com', 'leader123', role='Department Leader', phone_number='0245556667')
        ushers_leader = User.objects.create_user('ushers_leader', 'ushers@church.com', 'leader123', role='Department Leader', phone_number='0246667778')

        # 3. Create Departments
        self.stdout.write("Creating departments...")
        depts_data = [
            ('Choir', choir_leader, 'Responsible for music, worship leading, and special numbers in services.'),
            ('Ushers', ushers_leader, 'Welcome congregation, assist with seating, and collect offerings.'),
            ('Children\'s Ministry', None, 'Sunday school and biblical foundations for children.'),
            ('Youth', youth_leader, 'Youth fellowship and spiritual growth activities.'),
            ('Women\'s Ministry', None, 'Fellowship, prayers, and empowerment for women.'),
            ('Men\'s Ministry', None, 'Fellowship, leadership development, and service projects for men.'),
            ('Media Team', None, 'Handles audio, video, live streaming, and social media.'),
            ('Protocol', None, 'Ensures order, guest reception, and pastoral security.'),
        ]
        departments = {}
        for name, leader, desc in depts_data:
            dept = Department.objects.create(name=name, leader=leader, description=desc)
            departments[name] = dept

        # 4. Create Members
        self.stdout.write("Creating members...")
        today = datetime.date.today()
        members_data = [
            ('John Doe', 'Male', datetime.date(1985, 5, 12), '0240000001', '12 Main St, Accra', 'Married', True, datetime.date(2020, 1, 15), 'Men\'s Ministry', 'Alpha Cell', 'Active'),
            ('Jane Smith', 'Female', datetime.date(1990, 8, 22), '0240000002', '34 High St, Kumasi', 'Married', True, datetime.date(2021, 3, 10), 'Choir', 'Beta Cell', 'Active'),
            ('Samuel Anim', 'Male', datetime.date(1995, 12, 1), '0240000003', '56 Lake View, Koforidua', 'Single', True, datetime.date(2022, 6, 20), 'Youth', 'Omega Cell', 'Active'),
            ('Grace Osei', 'Female', datetime.date(today.year - 25, today.month, today.day), '0240000004', '78 Ring Road, Accra', 'Single', False, datetime.date(2023, 11, 5), 'Choir', 'Alpha Cell', 'Active'),  # Birthday today!
            ('David Mensah', 'Male', datetime.date(1978, 2, 14), '0240000005', '90 Palm Ave, Takoradi', 'Married', True, datetime.date(2018, 5, 1), 'Men\'s Ministry', 'Beta Cell', 'Active'),
            ('Mary Appiah', 'Female', datetime.date(1988, 7, 19), '0240000006', '11 Orchard Rd, Tema', 'Widowed', True, datetime.date(2019, 8, 12), 'Women\'s Ministry', 'Omega Cell', 'Active'),
            ('Kofi Boadu', 'Male', datetime.date(2002, 10, 30), '0240000007', '22 Sunset Blvd, Accra', 'Single', False, datetime.date(2024, 2, 22), 'Youth', 'Beta Cell', 'Active'),
            ('Abena Frimpong', 'Female', datetime.date(1993, 4, 5), '0240000008', '44 Hill View, Kumasi', 'Divorced', True, datetime.date(2020, 10, 11), 'Women\'s Ministry', 'Alpha Cell', 'Inactive'),
            ('Peter Mensah', 'Male', datetime.date(2010, 1, 1), '0240000009', '55 Park Side, Tema', 'Single', False, datetime.date(2025, 1, 10), 'Children\'s Ministry', '', 'Active'),
            ('Sarah Addo', 'Female', datetime.date(2005, 3, 18), '0240000010', '88 Valley View, Accra', 'Single', True, datetime.date(2024, 7, 1), 'Youth', 'Omega Cell', 'Active'),
        ]
        
        members = []
        for name, gender, dob, phone, addr, marital, baptized, joined, dept_name, cell, status in members_data:
            dept = departments.get(dept_name) if dept_name else None
            m = Member.objects.create(
                full_name=name, gender=gender, date_of_birth=dob, phone_number=phone,
                address=addr, marital_status=marital, baptized=baptized, date_joined=joined,
                department=dept, cell_group=cell, status=status
            )
            members.append(m)

        # 5. Create Visitors
        self.stdout.write("Creating visitors...")
        visitors_data = [
            ('Charles Owusu', '0551112220', '15 Garden St, Accra', 'John Doe', today - datetime.timedelta(days=15)),
            ('Evelyn Asare', '0551112221', '67 Bridge St, Tema', 'Jane Smith', today - datetime.timedelta(days=7)),
            ('Emmanuel Boateng', '0551112222', '39 Castle Rd, Osu', 'Self Invited', today),
            ('Francisca Cobbah', '0551112223', '92 Ridge Rd, Accra', 'Samuel Anim', today - datetime.timedelta(days=14)),
        ]
        visitors = []
        for name, phone, addr, invited, fv_date in visitors_data:
            v = Visitor.objects.create(
                name=name, phone=phone, address=addr, invited_by=invited, first_visit_date=fv_date
            )
            visitors.append(v)

        # 6. Create Attendance Sessions & Records
        self.stdout.write("Creating attendance records...")
        # 4 Sundays
        sundays = []
        for i in range(1, 5):
            sundays.append(today - datetime.timedelta(days=today.weekday() + 1 + 7*(i-1)))
        
        # We can add services
        sessions = []
        for s_date in sundays:
            sess = AttendanceSession.objects.create(service_type='Sunday Service', date=s_date, description=f"Sunday Worship Session on {s_date}")
            sessions.append(sess)
            # Members attendance
            for m in members:
                status = 'Present' if (m.status == 'Active' and hash(m.full_name + str(s_date)) % 10 != 0) else 'Absent'
                AttendanceRecord.objects.create(session=sess, member=m, status=status)
            # Visitors attendance
            for v in visitors:
                if v.first_visit_date <= s_date:
                    AttendanceRecord.objects.create(session=sess, visitor=v, status='Present')

        # Add a Midweek session
        midweek_date = today - datetime.timedelta(days=today.weekday() + 4)
        midweek_sess = AttendanceSession.objects.create(service_type='Midweek Service', date=midweek_date, description=f"Midweek Bible Study on {midweek_date}")
        for m in members:
            status = 'Present' if (m.status == 'Active' and hash(m.full_name + str(midweek_date)) % 3 != 0) else 'Absent'
            AttendanceRecord.objects.create(session=midweek_sess, member=m, status=status)

        # Add Today's Attendance
        today_sess = AttendanceSession.objects.create(service_type='Prayer Meeting', date=today, description="Today's Prayer Service")
        for m in members[:7]:
            AttendanceRecord.objects.create(session=today_sess, member=m, status='Present')
        for m in members[7:]:
            AttendanceRecord.objects.create(session=today_sess, member=m, status='Absent')

        # 7. Create Events
        self.stdout.write("Creating events...")
        Event.objects.create(
            event_name='Annual Youth Conference 2026', event_type='Conference',
            date=today + datetime.timedelta(days=14), time=datetime.time(9, 0),
            venue='Main Chapel auditorium', description='A two-day gathering of youth from all cell groups for spiritual renewal and leadership talks.',
            organizer='Youth Department'
        )
        Event.objects.create(
            event_name='Couples Dinner Night', event_type='Social',
            date=today + datetime.timedelta(days=5), time=datetime.time(18, 30),
            venue='Royal Palace Hotel', description='A special night for married couples to fellowship and strengthen their marriages.',
            organizer='Women & Men Ministry'
        )
        Event.objects.create(
            event_name='Community Medical Outreach', event_type='Outreach',
            date=today - datetime.timedelta(days=12), time=datetime.time(8, 0),
            venue='Town Square', description='Free medical checkup and drugs donation to the local community.',
            organizer='Protocol & Ushers'
        )

        # 8. Create Finance Transactions
        self.stdout.write("Creating finance transactions...")
        # Past Transactions
        for i in range(1, 30):
            tx_date = today - datetime.timedelta(days=i)
            # Add some offering and tithes on Sundays
            if tx_date.weekday() == 6:
                FinanceTransaction.objects.create(
                    transaction_type='Income', category='Offering', amount=1200.00 + i*10,
                    date=tx_date, description=f"Sunday offering for {tx_date}", recorded_by=finance
                )
                FinanceTransaction.objects.create(
                    transaction_type='Income', category='Tithe', amount=2500.00 + i*5,
                    date=tx_date, description=f"Sunday tithes for {tx_date}", recorded_by=finance
                )
            if i % 5 == 0:
                FinanceTransaction.objects.create(
                    transaction_type='Expense', category='Utilities', amount=250.00 + i*5,
                    date=tx_date, description=f"Electricity/Water bill payment on {tx_date}", recorded_by=finance
                )
            if i % 7 == 0:
                FinanceTransaction.objects.create(
                    transaction_type='Expense', category='Maintenance', amount=150.00,
                    date=tx_date, description=f"Chapel cleaning and repairs on {tx_date}", recorded_by=finance
                )

        # Current Month Salaries and Thanksgiving
        curr_month_start = today.replace(day=1)
        FinanceTransaction.objects.create(
            transaction_type='Expense', category='Salaries', amount=4500.00,
            date=curr_month_start, description="Monthly salaries for staff", recorded_by=finance
        )
        FinanceTransaction.objects.create(
            transaction_type='Income', category='Thanksgiving', amount=1500.00,
            date=curr_month_start + datetime.timedelta(days=3), description="Special thanks offering", recorded_by=finance
        )
        FinanceTransaction.objects.create(
            transaction_type='Income', category='Building Fund', amount=5000.00,
            date=curr_month_start + datetime.timedelta(days=10), description="Building extension donation", recorded_by=finance
        )

        # 9. Create Sermons
        self.stdout.write("Creating sermons...")
        Sermon.objects.create(
            title='Walking in Covenant Blessings', speaker='Pastor Anim',
            date=today - datetime.timedelta(days=7), scripture='Deuteronomy 28:1-14',
            notes='Key points:\n1. Obedience is the key to covenant blessings.\n2. The blessings overtake you.\n3. Head and not the tail.'
        )
        Sermon.objects.create(
            title='The Power of Prayer and Fasting', speaker='Rev. John Doe',
            date=today - datetime.timedelta(days=14), scripture='Matthew 17:14-21',
            notes='Key points:\n1. Some challenges only go by prayer and fasting.\n2. Building spiritual capacity.\n3. Active faith defeats doubt.'
        )
        Sermon.objects.create(
            title='Living a Purpose-Driven Life', speaker='Pastor Anim',
            date=today - datetime.timedelta(days=21), scripture='Ephesians 2:8-10',
            notes='Key points:\n1. We are created for good works.\n2. Discovering your God-given potentials.\n3. Standing firm in your call.'
        )

        # 10. Create Announcements
        self.stdout.write("Creating announcements...")
        Announcement.objects.create(
            title='Church Building Fund Contribution Notice',
            content='Dear Members, we are launching our building fund phase 2. Let us support the Lord\'s house generously.',
            author=pastor
        )
        Announcement.objects.create(
            title='Joint Fellowship this Friday',
            content='All cell groups will meet at the main auditorium for a joint prayer and worship session starting at 6:30 PM.',
            author=pastor
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
