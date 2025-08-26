from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime, timedelta
import re
import bcrypt
from django.utils import timezone
from decimal import Decimal
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')


# ---------------------------
# Managers
# ---------------------------

class UserManager(models.Manager):
    def validate(self, form):
        errors = {}
        if len(form['first_name']) < 2:
            errors['first_name'] = 'First Name must be at least 2 characters'

        if len(form['last_name']) < 2:
            errors['last_name'] = 'Last Name must be at least 2 characters'

        if not EMAIL_REGEX.match(form['email']):
            errors['email'] = 'Invalid Email Address'
        
        email_check = self.filter(email=form['email'])
        if email_check:
            errors['email'] = "Email already in use"

        if len(form['password']) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        
        if form['password'] != form['confirm']:
            errors['password'] = 'Passwords do not match'
        
        return errors
    
    def authenticate(self, email, password):
        users = self.filter(email=email)
        if not users:
            return False
        user = users[0]
        return bcrypt.checkpw(password.encode(), user.password.encode())

    def register(self, form):
        pw = bcrypt.hashpw(form['password'].encode(), bcrypt.gensalt()).decode()
        user = self.create(
            first_name=form['first_name'],
            last_name=form['last_name'],
            email=form['email'],
            password=pw,
        )
        # Create wallet for new user
        UserWallet.objects.create(user=user)
        return user


class TrackManager(models.Manager):
    def get_with_progress(self, student):
        """Get all tracks with student's progress"""
        tracks = self.all()
        for track in tracks:
            track.student_progress = track.get_student_progress(student)
            track.is_enrolled = track.enrollments.filter(student=student).exists()
            track.is_accessible = track.is_accessible_to_user(student)
        return tracks


class CourseManager(models.Manager):
    def get_with_progress(self, student, track=None):
        queryset = self.all()
        if track:
            queryset = queryset.filter(track=track)
        for course in queryset:
            course.student_progress = course.get_student_progress(student)
            course.is_unlocked = course.is_unlocked_for_student(student)
        return queryset


class SectionManager(models.Manager):
    def get_with_progress(self, student, course=None):
        queryset = self.all()
        if course:
            queryset = queryset.filter(course=course)
        for section in queryset:
            section.is_completed = section.completions.filter(student=student).exists()
            section.is_unlocked = section.is_unlocked_for_student(student)
        return queryset


# ---------------------------
# Core Models
# ---------------------------

class User(models.Model):
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    image_url = models.CharField(default="/static/profile.png", max_length=255, null=True)
    
    # Subscription and access
    subscription_tier = models.CharField(max_length=20, default='free', choices=[
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium')
    ])
    subscription_expires = models.DateTimeField(null=True, blank=True)
    
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def has_active_subscription(self):
        if self.subscription_tier == 'free':
            return False
        if self.subscription_expires and self.subscription_expires < timezone.now():
            return False
        return True

    def get_enrolled_tracks(self):
        return Track.objects.filter(enrollments__student=self, enrollments__is_active=True)

    def get_overall_progress(self):
        enrolled_tracks = self.get_enrolled_tracks()
        if not enrolled_tracks:
            return 0
        total_progress = sum(track.get_student_progress(self) for track in enrolled_tracks)
        return total_progress / len(enrolled_tracks)

    def get_current_streak(self):
        """Calculate current daily completion streak"""
        today = timezone.now().date()
        streak = 0
        check_date = today
        
        while True:
            if SectionCompletion.objects.filter(
                student=self, 
                completed_at__date=check_date
            ).exists():
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        return streak

    def get_total_earnings(self):
        return self.wallet.total_earnings if hasattr(self, 'wallet') else Decimal('0.00')


class UserWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    learning_points = models.IntegerField(default=0)  # Educational progress points
    challenge_points = models.IntegerField(default=0)  # Coding challenge points
    bonus_points = models.IntegerField(default=0)     # Streak/achievement bonuses
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_payout = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    lifetime_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Payout settings
    payout_threshold = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('10.00'))
    payout_email = models.EmailField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name}'s Wallet"

    @property
    def total_points(self):
        return self.learning_points + self.challenge_points + self.bonus_points

    @property
    def can_request_payout(self):
        return self.total_earnings >= self.payout_threshold


class PointStructure(models.Model):
    content_type = models.CharField(max_length=50, choices=[
        ('section_lesson', 'Section - Lesson'),
        ('section_exercise', 'Section - Exercise'),
        ('section_quiz', 'Section - Quiz'),
        ('section_project', 'Section - Project'),
        ('coding_challenge_easy', 'Coding Challenge - Easy'),
        ('coding_challenge_medium', 'Coding Challenge - Medium'),
        ('coding_challenge_hard', 'Coding Challenge - Hard'),
        ('track_completion', 'Track Completion'),
        ('daily_streak', 'Daily Streak'),
        ('referral_bonus', 'Referral Bonus'),
    ])
    base_points = models.IntegerField()
    cash_value_per_point = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.01'))  # $0.01 per point default
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['content_type']

    def __str__(self):
        return f"{self.content_type}: {self.base_points} pts (${self.cash_value_per_point}/pt)"

    @property
    def total_cash_value(self):
        return self.base_points * self.cash_value_per_point


class PointTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('section_complete', 'Section Completed'),
        ('challenge_solve', 'Coding Challenge Solved'),
        ('track_complete', 'Track Completed'),
        ('daily_streak', 'Daily Streak Bonus'),
        ('referral_bonus', 'Referral Bonus'),
        ('manual_adjustment', 'Manual Adjustment'),
        ('payout_request', 'Payout Requested'),
        ('payout_processed', 'Payout Processed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    points_earned = models.IntegerField()
    cash_value = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Reference to what earned the points
    related_section_id = models.IntegerField(null=True, blank=True)
    related_challenge_id = models.IntegerField(null=True, blank=True)
    related_track_id = models.IntegerField(null=True, blank=True)
    
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=True)  # False for pending transactions

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name}: {self.points_earned} pts (${self.cash_value}) - {self.transaction_type}"


class Track(models.Model):
    TRACK_TYPES = [
        ('programming_basics', 'Programming Basics'),
        ('frontend', 'Front End'),
        ('backend', 'Back End'),
        ('mobile', 'Mobile'),
        ('fullstack', 'Full Stack'),
        ('data_science', 'Data Science'),
    ]
    
    ACCESS_LEVELS = [
        ('free', 'Free Access'),
        ('basic', 'Basic Subscription Required'),
        ('premium', 'Premium Subscription Required'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    track_type = models.CharField(max_length=50, choices=TRACK_TYPES)
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='free')
    image_url = models.CharField(max_length=255, null=True, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Pricing
    one_time_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = TrackManager()

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def is_accessible_to_user(self, user):
        """Check if user has access to this track"""
        if self.access_level == 'free':
            return True
        elif self.access_level == 'basic':
            return user.subscription_tier in ['basic', 'premium'] and user.has_active_subscription
        elif self.access_level == 'premium':
            return user.subscription_tier == 'premium' and user.has_active_subscription
        return False

    def get_student_progress(self, student):
        total_sections = Section.objects.filter(course__track=self).count()
        if total_sections == 0:
            return 0
        completed_sections = SectionCompletion.objects.filter(
            student=student, section__course__track=self
        ).count()
        return (completed_sections / total_sections) * 100

    def get_total_possible_points(self):
        """Calculate total points available in this track"""
        return sum(
            section.get_point_value() for section in 
            Section.objects.filter(course__track=self)
        )


class Course(models.Model):
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='courses')
    image_url = models.CharField(max_length=255, null=True, blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, default='beginner')
    estimated_hours = models.IntegerField(default=10)
    order = models.IntegerField(default=0)
    prerequisites = models.ManyToManyField('self', blank=True, symmetrical=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = CourseManager()

    class Meta:
        ordering = ['track', 'order', 'name']

    def __str__(self):
        return f"{self.track.name} - {self.name}"

    def get_student_progress(self, student):
        total_sections = self.sections.count()
        if total_sections == 0:
            return 0
        completed_sections = SectionCompletion.objects.filter(
            student=student, section__course=self
        ).count()
        return (completed_sections / total_sections) * 100

    def is_unlocked_for_student(self, student):
        if not self.prerequisites.exists():
            return True
        for prereq in self.prerequisites.all():
            if prereq.get_student_progress(student) < 100:
                return False
        return True

    def get_next_incomplete_section(self, student):
        completed_ids = SectionCompletion.objects.filter(
            student=student, section__course=self
        ).values_list('section_id', flat=True)
        return self.sections.exclude(id__in=completed_ids).first()


class Section(models.Model):
    SECTION_TYPES = [
        ('lesson', 'Lesson'),
        ('exercise', 'Exercise'),
        ('project', 'Project'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, default='lesson')
    content = models.TextField()
    video_url = models.URLField(null=True, blank=True)
    estimated_minutes = models.IntegerField(default=30)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = SectionManager()

    class Meta:
        ordering = ['course', 'order', 'title']

    def __str__(self):
        return f"{self.course.name} - {self.title}"

    def is_unlocked_for_student(self, student):
        if self.order <= 1:  # first section
            return True
        previous_section = Section.objects.filter(
            course=self.course, order__lt=self.order
        ).order_by('-order').first()
        if not previous_section:
            return True
        return SectionCompletion.objects.filter(student=student, section=previous_section).exists()

    def get_point_value(self):
        """Get point value for this section based on type and difficulty"""
        content_type_map = {
            'lesson': 'section_lesson',
            'exercise': 'section_exercise',
            'quiz': 'section_quiz',
            'project': 'section_project',
            'assignment': 'section_exercise',
        }
        
        content_type = content_type_map.get(self.section_type, 'section_lesson')
        try:
            point_structure = PointStructure.objects.get(content_type=content_type)
            return point_structure.base_points
        except PointStructure.DoesNotExist:
            # Default points based on estimated time
            return max(10, self.estimated_minutes // 3)


class TrackEnrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='track_enrollments')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['student', 'track']

    def __str__(self):
        return f"{self.student.full_name} enrolled in {self.track.name}"


class SectionCompletion(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='section_completions')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['student', 'section']

    def __str__(self):
        return f"{self.student.full_name} completed {self.section.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Award points for completion
            self.award_completion_points()

    def award_completion_points(self):
        """Award points when section is completed"""
        section_type_map = {
            'lesson': 'section_lesson',
            'exercise': 'section_exercise',
            'quiz': 'section_quiz',
            'project': 'section_project',
            'assignment': 'section_exercise',
        }
        
        content_type = section_type_map.get(self.section.section_type, 'section_lesson')
        
        try:
            point_structure = PointStructure.objects.get(content_type=content_type)
            points = point_structure.base_points
            cash_value = point_structure.total_cash_value
        except PointStructure.DoesNotExist:
            points = self.section.get_point_value()
            cash_value = Decimal(str(points * 0.01))  # Default $0.01 per point

        # Update wallet
        wallet = self.student.wallet
        wallet.learning_points += points
        wallet.total_earnings += cash_value
        wallet.save()

        # Create transaction record
        PointTransaction.objects.create(
            user=self.student,
            transaction_type='section_complete',
            points_earned=points,
            cash_value=cash_value,
            related_section_id=self.section.id,
            description=f"Completed: {self.section.title}"
        )


class StudentProgress(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress_summary')
    total_sections_completed = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.full_name} Progress Summary"

    def update_streak(self):
        """Update streak based on recent activity"""
        current_streak = self.student.get_current_streak()
        self.current_streak = current_streak
        if current_streak > self.longest_streak:
            self.longest_streak = current_streak
        self.save()


# ---------------------------
# Code Challenges (Enhanced)
# ---------------------------

class CodeChallenge(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='easy')
    input_example = models.TextField()
    output_example = models.TextField()
    solution = models.TextField()
    
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE,
        related_name='code_challenges',
        null=True, blank=True
    )
    
    # Standalone challenges (not tied to sections)
    is_standalone = models.BooleanField(default=False)
    tags = models.CharField(max_length=255, blank=True)  # comma-separated
    
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.difficulty})"

    def get_point_value(self):
        """Get point value based on difficulty"""
        difficulty_map = {
            'easy': 'coding_challenge_easy',
            'medium': 'coding_challenge_medium',
            'hard': 'coding_challenge_hard',
        }
        
        content_type = difficulty_map.get(self.difficulty, 'coding_challenge_easy')
        try:
            point_structure = PointStructure.objects.get(content_type=content_type)
            return point_structure.base_points, point_structure.total_cash_value
        except PointStructure.DoesNotExist:
            # Default values
            defaults = {'easy': (50, 0.50), 'medium': (150, 1.50), 'hard': (300, 3.00)}
            points, cash = defaults.get(self.difficulty, (50, 0.50))
            return points, Decimal(str(cash))


class ChallengeSolution(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(CodeChallenge, on_delete=models.CASCADE)
    solution_code = models.TextField()
    is_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    execution_time = models.FloatField(null=True, blank=True)  # in milliseconds

    class Meta:
        unique_together = ['student', 'challenge']

    def __str__(self):
        return f"{self.student.full_name} - {self.challenge.title} ({'✓' if self.is_correct else '✗'})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.is_correct:
            self.award_challenge_points()

    def award_challenge_points(self):
        """Award points for solving challenge"""
        points, cash_value = self.challenge.get_point_value()
        
        # Update wallet
        wallet = self.student.wallet
        wallet.challenge_points += points
        wallet.total_earnings += cash_value
        wallet.save()

        # Create transaction record
        PointTransaction.objects.create(
            user=self.student,
            transaction_type='challenge_solve',
            points_earned=points,
            cash_value=cash_value,
            related_challenge_id=self.challenge.id,
            description=f"Solved: {self.challenge.title} ({self.challenge.difficulty})"
        )


# ---------------------------
# Legacy Models (Movies/Quotes/Comments) - Keep for now
# ---------------------------

class Movie(models.Model):
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=255)
    image_url = models.CharField(max_length=255, null=True)
    poster = models.ForeignKey(User, related_name='user_movies', on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class Quote(models.Model):
    quote = models.CharField(max_length=255)
    poster = models.ForeignKey(User, related_name='user_quotes', on_delete=models.CASCADE)
    user_likes = models.ManyToManyField(User, related_name='liked_quotes', through='UserQuote')
    movie = models.ForeignKey(Movie, related_name="movie_quotes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.quote


class Comment(models.Model):
    comment = models.CharField(max_length=255)
    poster = models.ForeignKey(User, related_name='user_comments', on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, related_name="quote_comments", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.comment


class UserQuote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)