# Create at: my_app/management/commands/seed_point_structures.py
from django.core.management.base import BaseCommand
from decimal import Decimal
from my_app.models import PointStructure

class Command(BaseCommand):
    help = 'Seed the database with default point structures'

    def handle(self, *args, **options):
        point_structures = [
            ('section_lesson', 20, Decimal('0.02')),
            ('section_exercise', 30, Decimal('0.03')),
            ('section_quiz', 40, Decimal('0.04')),
            ('section_project', 100, Decimal('0.10')),
            ('coding_challenge_easy', 50, Decimal('0.05')),
            ('coding_challenge_medium', 150, Decimal('0.15')),
            ('coding_challenge_hard', 300, Decimal('0.30')),
            ('track_completion', 1000, Decimal('1.00')),
            ('daily_streak', 10, Decimal('0.01')),
            ('referral_bonus', 500, Decimal('0.50')),
        ]

        created_count = 0
        updated_count = 0

        for content_type, points, cash_per_point in point_structures:
            ps, created = PointStructure.objects.get_or_create(
                content_type=content_type,
                defaults={
                    'base_points': points,
                    'cash_value_per_point': cash_per_point,
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {content_type} - {points} pts (${cash_per_point}/pt)'))
            else:
                if ps.base_points != points or ps.cash_value_per_point != cash_per_point:
                    ps.base_points = points
                    ps.cash_value_per_point = cash_per_point
                    ps.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'Updated: {content_type}'))

        self.stdout.write(self.style.SUCCESS(
            f'Point structures seeded successfully. Created: {created_count}, Updated: {updated_count}'
        ))