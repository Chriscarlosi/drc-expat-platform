from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    help = 'Force reset the superuser password'

    def handle(self, *args, **options):
        # We will default to 'administrator' if the env var is missing
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'administrator')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'AdminPassword123!')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')

        # Find the user or create them if they don't exist
        user, created = User.objects.get_or_create(username=username)

        # Force the new password and permissions
        user.set_password(password)
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created NEW superuser: {username} / {password}'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'FORCE RESET password for existing superuser: {username} to {password}'))