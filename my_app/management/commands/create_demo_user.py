# my_app/management/commands/create_demo_user.py

from django.core.management.base import BaseCommand
from my_app.models import User, UserWallet, StudentProgress
import bcrypt

class Command(BaseCommand):
    help = 'Create a demo user account for testing'

    def handle(self, *args, **options):
        email = 'demo@codingacademy.com'
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'User with email {email} already exists!')
            )
            return

        # Create user
        pw = bcrypt.hashpw('demo123456'.encode(), bcrypt.gensalt()).decode()
        user = User.objects.create(
            first_name='Demo',
            last_name='Student',
            email=email,
            password=pw,
            subscription_tier='basic',  # Give them basic access
            image_url='/static/avatar_placeholder.png'
        )

        # Create wallet and progress
        wallet = UserWallet.objects.create(user=user)
        progress = StudentProgress.objects.create(student=user)

        self.stdout.write(
            self.style.SUCCESS(
                f'Created demo user:\n'
                f'   Email: {email}\n'
                f'   Password: demo123456\n'
                f'   Subscription: {user.subscription_tier}\n'
            )
        )