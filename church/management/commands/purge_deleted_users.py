from django.core.management.base import BaseCommand
from django.utils import timezone
from church.models import CustomUser, AuditLog

class Command(BaseCommand):
    help = 'Permanently purges soft-deleted user accounts whose 3-month (90-day) retention period has expired.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_users = CustomUser.objects.filter(
            is_deleted=True,
            scheduled_deletion_date__lte=now
        )
        
        count = expired_users.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No expired user accounts pending permanent purge."))
            return

        self.stdout.write(f"Found {count} account(s) past 3-month retention window. Permanently purging...")
        
        for user in expired_users:
            username = user.username
            user_id = user.pk
            role = user.role
            
            # Log final security audit before hard delete
            AuditLog.objects.create(
                user=None,
                user_display='System / Retention Task',
                action_type='DELETE',
                module='User Management',
                description=f"Permanently purged expired user account '{username}' (ID: {user_id}, Role: {role}) after 3-month retention window",
                ip_address='127.0.0.1'
            )
            
            user.delete()
            self.stdout.write(self.style.WARNING(f"Permanently deleted user '{username}' (ID: {user_id})"))

        self.stdout.write(self.style.SUCCESS(f"Purge complete. Successfully deleted {count} expired user account(s)."))
