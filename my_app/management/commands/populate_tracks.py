
# my_app/management/commands/populate_tracks.py

from django.core.management.base import BaseCommand
from my_app.models import Track, Course, Section, PointStructure, CodeChallenge
from decimal import Decimal

class Command(BaseCommand):
    help = 'Populate database with sample tracks, courses, and sections'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample learning content...')
        
        # Create point structures first
        self.create_point_structures()
        
        # Create tracks with content
        self.create_programming_basics_track()
        self.create_web_development_track() 
        self.create_mobile_development_track()
        
        # Create sample challenges
        self.create_sample_challenges()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created all sample content!')
        )

    def create_point_structures(self):
        """Create default point structures"""
        self.stdout.write('Creating point structures...')
        
        structures = [
            ('section_lesson', 20, Decimal('0.10')),
            ('section_exercise', 50, Decimal('0.25')), 
            ('section_quiz', 30, Decimal('0.15')),
            ('section_project', 100, Decimal('0.50')),
            ('coding_challenge_easy', 50, Decimal('0.25')),
            ('coding_challenge_medium', 150, Decimal('0.75')),
            ('coding_challenge_hard', 300, Decimal('1.50')),
            ('track_completion', 1000, Decimal('10.00')),
            ('daily_streak', 10, Decimal('0.05')),
        ]
        
        for content_type, points, total_cash in structures:
            obj, created = PointStructure.objects.get_or_create(
                content_type=content_type,
                defaults={
                    'base_points': points,
                    'cash_value_per_point': total_cash / points,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  ✓ {obj.get_content_type_display()}: {points} pts = ${total_cash}')

    def create_programming_basics_track(self):
        """Create Programming Basics track (FREE)"""
        self.stdout.write('Creating Programming Basics track...')
        
        track, created = Track.objects.get_or_create(
            name="Programming Basics",
            defaults={
                'description': 'Learn fundamental programming concepts that apply to any language. Perfect for complete beginners.',
                'track_type': 'programming_basics',
                'access_level': 'free',  # FREE!
                'order': 1,
                'image_url': '/static/programmingbasics.png',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'  ✓ Created track: {track.name}')

        # Course 1: Variables and Data Types
        course1, _ = Course.objects.get_or_create(
            name="Variables and Data Types",
            track=track,
            defaults={
                'description': 'Master variables, constants, and data types - the building blocks of all programming.',
                'difficulty': 'beginner',
                'estimated_hours': 3,
                'order': 1,
                'is_active': True,
            }
        )

        sections_c1 = [
            ("What are Variables?", "lesson", "Understand what variables are and why every programmer needs them."),
            ("Creating Your First Variable", "exercise", "Practice declaring and using variables in code."),
            ("Data Types Explained", "lesson", "Learn about numbers, text, and boolean values."),
            ("Working with Strings", "lesson", "Master text manipulation and string operations."),
            ("Numbers and Math", "exercise", "Practice mathematical operations in programming."),
            ("Variables Quiz", "quiz", "Test your understanding of variables and data types."),
        ]

        for i, (title, section_type, description) in enumerate(sections_c1):
            Section.objects.get_or_create(
                title=title,
                course=course1,
                defaults={
                    'description': description,
                    'section_type': section_type,
                    'content': self.generate_content(title, description, section_type),
                    'estimated_minutes': 25 if section_type == 'lesson' else 35,
                    'order': i + 1,
                    'is_active': True,
                }
            )

        # Course 2: Control Flow  
        course2, _ = Course.objects.get_or_create(
            name="Control Flow and Logic",
            track=track,
            defaults={
                'description': 'Learn to control program execution with conditionals, loops, and logical operations.',
                'difficulty': 'beginner',
                'estimated_hours': 4,
                'order': 2,
                'is_active': True,
            }
        )

        sections_c2 = [
            ("Making Decisions with If Statements", "lesson", "Learn how programs make choices with conditional logic."),
            ("Else and Multiple Conditions", "lesson", "Handle complex decision-making with else and elif."),
            ("Loops: Repeating Code Efficiently", "lesson", "Understand for loops and while loops."),
            ("Building a Number Guessing Game", "project", "Apply everything you've learned in a fun project."),
            ("Logic and Flow Quiz", "quiz", "Test your understanding of program control flow."),
        ]

        for i, (title, section_type, description) in enumerate(sections_c2):
            Section.objects.get_or_create(
                title=title,
                course=course2,
                defaults={
                    'description': description,
                    'section_type': section_type,
                    'content': self.generate_content(title, description, section_type),
                    'estimated_minutes': 30 if section_type == 'lesson' else 60,
                    'order': i + 1,
                    'is_active': True,
                }
            )

    def create_web_development_track(self):
        """Create Web Development track (BASIC subscription)"""
        self.stdout.write('Creating Web Development track...')
        
        track, created = Track.objects.get_or_create(
            name="Web Development",
            defaults={
                'description': 'Build modern, responsive websites from scratch. Learn HTML, CSS, and JavaScript.',
                'track_type': 'frontend',
                'access_level': 'basic',  # Requires subscription
                'order': 2,
                'image_url': '/static/frontend.png',
                'one_time_price': Decimal('99.00'),
                'is_active': True,
            }
        )

        course1, _ = Course.objects.get_or_create(
            name="HTML Fundamentals",
            track=track,
            defaults={
                'description': 'Master HTML - the backbone of every website.',
                'difficulty': 'beginner',
                'estimated_hours': 6,
                'order': 1,
                'is_active': True,
            }
        )

        sections_c1 = [
            ("What is HTML?", "lesson", "Introduction to HTML and how web pages work."),
            ("HTML Document Structure", "lesson", "Learn the essential structure of every HTML document."),
            ("Text Elements and Formatting", "lesson", "Master headings, paragraphs, and text styling."),
            ("Links and Navigation", "exercise", "Create clickable links and navigation menus."),
            ("Build Your First Website", "project", "Create a complete personal portfolio website."),
        ]

        for i, (title, section_type, description) in enumerate(sections_c1):
            Section.objects.get_or_create(
                title=title,
                course=course1,
                defaults={
                    'description': description,
                    'section_type': section_type,
                    'content': self.generate_content(title, description, section_type),
                    'estimated_minutes': 35 if section_type == 'lesson' else 75,
                    'order': i + 1,
                    'is_active': True,
                }
            )

    def create_mobile_development_track(self):
        """Create iOS Development track (PREMIUM subscription)"""
        self.stdout.write('Creating iOS Development track...')
        
        track, created = Track.objects.get_or_create(
            name="iOS Development with Swift",
            defaults={
                'description': 'Build native iOS apps using Swift and SwiftUI.',
                'track_type': 'mobile',
                'access_level': 'premium',  # Requires premium
                'order': 3,
                'image_url': '/static/mobile.png',
                'one_time_price': Decimal('199.00'),
                'is_active': True,
            }
        )

        course1, _ = Course.objects.get_or_create(
            name="Swift Language Fundamentals",
            track=track,
            defaults={
                'description': 'Master the Swift programming language.',
                'difficulty': 'intermediate',
                'estimated_hours': 8,
                'order': 1,
                'is_active': True,
            }
        )

        sections_c1 = [
            ("Swift Syntax and Variables", "lesson", "Learn Swift's clean, powerful syntax."),
            ("Functions in Swift", "lesson", "Write reusable, efficient code with Swift functions."),
            ("Classes and Structs", "lesson", "Object-oriented programming concepts in Swift."),
            ("Build a Swift Calculator", "project", "Create a command-line calculator using Swift."),
        ]

        for i, (title, section_type, description) in enumerate(sections_c1):
            Section.objects.get_or_create(
                title=title,
                course=course1,
                defaults={
                    'description': description,
                    'section_type': section_type,
                    'content': self.generate_content(title, description, section_type),
                    'estimated_minutes': 45 if section_type == 'lesson' else 90,
                    'order': i + 1,
                    'is_active': True,
                }
            )

    def create_sample_challenges(self):
        """Create sample coding challenges"""
        self.stdout.write('Creating coding challenges...')
        
        challenges = [
            {
                'title': 'Hello, World!',
                'description': 'Print "Hello, World!" to the console.',
                'difficulty': 'easy',
                'input_example': '',
                'output_example': 'Hello, World!',
                'solution': 'print("Hello, World!")',
                'is_standalone': True,
                'tags': 'beginner,printing,basics',
            },
            {
                'title': 'Sum Two Numbers',
                'description': 'Write a function that takes two numbers and returns their sum.',
                'difficulty': 'easy',
                'input_example': '5, 3',
                'output_example': '8',
                'solution': 'def sum_numbers(a, b):\n    return a + b',
                'is_standalone': True,
                'tags': 'functions,math,beginner',
            },
            {
                'title': 'Find Maximum Number',
                'description': 'Given a list of numbers, find and return the largest one.',
                'difficulty': 'easy',
                'input_example': '[12, 45, 67, 23, 9]',
                'output_example': '67',
                'solution': 'def find_max(numbers):\n    return max(numbers)',
                'is_standalone': True,
                'tags': 'arrays,algorithms,loops',
            },
            {
                'title': 'Count Vowels',
                'description': 'Count the number of vowels in a given string.',
                'difficulty': 'medium',
                'input_example': '"Hello World"',
                'output_example': '3',
                'solution': 'def count_vowels(text):\n    vowels = "aeiouAEIOU"\n    return sum(1 for char in text if char in vowels)',
                'is_standalone': True,
                'tags': 'strings,counting,loops',
            },
            {
                'title': 'Palindrome Checker',
                'description': 'Check if a word reads the same forwards and backwards.',
                'difficulty': 'medium',
                'input_example': '"racecar"',
                'output_example': 'True',
                'solution': 'def is_palindrome(text):\n    return text == text[::-1]',
                'is_standalone': True,
                'tags': 'strings,algorithms,logic',
            },
        ]

        for challenge_data in challenges:
            challenge, created = CodeChallenge.objects.get_or_create(
                title=challenge_data['title'],
                defaults=challenge_data
            )
            if created:
                points, cash = challenge.get_point_value()
                self.stdout.write(f'  ✓ {challenge.title} ({challenge.difficulty}) - {points} pts = ${cash}')

    def generate_content(self, title, description, section_type):
        """Generate sample content for sections"""
        return f"""<h1>{title}</h1>
<p>{description}</p>

<h2>What You'll Learn</h2>
<p>In this {section_type}, we'll cover the fundamental concepts that every programmer needs to know.</p>

<h2>Key Points</h2>
<ul>
<li>Core programming principles</li>
<li>Best practices and patterns</li>
<li>Real-world applications</li>
</ul>

<div class="alert alert-info">
<strong>💡 Pro Tip:</strong> Take your time with each concept. Understanding the fundamentals deeply will make advanced topics much easier.
</div>
"""