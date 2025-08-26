# my_app/admin.py
from django.contrib import admin
from .models import (
    User, Track, Course, Section, TrackEnrollment,
    SectionCompletion, StudentProgress,
    Movie, Quote, Comment, UserQuote,
    CodeChallenge, ChallengeSolution,
    PointStructure, PointTransaction, UserWallet
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'date_joined', 'is_active']
    list_filter = ['is_active', 'date_joined']
    search_fields = ['first_name', 'last_name', 'email']
    ordering = ['-date_joined']

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'total_earnings', 'pending_payout', 'payout_email', 'payout_threshold']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    ordering = ['-total_earnings']

@admin.register(PointStructure)
class PointStructureAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'base_points', 'cash_value_per_point', 'is_active']
    list_filter = ['is_active']
    search_fields = ['content_type']
    ordering = ['content_type']

@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'points_earned', 'cash_value', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'description']
    ordering = ['-created_at']

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['name', 'track_type', 'access_level', 'order', 'is_active', 'created_at']
    list_filter = ['track_type', 'access_level', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'track', 'difficulty', 'estimated_hours', 'order', 'is_active']
    list_filter = ['track', 'difficulty', 'is_active']
    search_fields = ['name', 'description', 'track__name']
    ordering = ['track', 'order']
    filter_horizontal = ['prerequisites']

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    # NOTE: removed non-existent 'points'
    list_display = ['title', 'course', 'section_type', 'estimated_minutes', 'order', 'is_active']
    list_filter = ['course__track', 'course', 'section_type', 'is_active']
    search_fields = ['title', 'description', 'course__name']
    ordering = ['course', 'order']

@admin.register(TrackEnrollment)
class TrackEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'track', 'enrolled_at', 'is_active']
    list_filter = ['track', 'is_active', 'enrolled_at']
    search_fields = ['student__first_name', 'student__last_name', 'track__name']
    ordering = ['-enrolled_at']

@admin.register(SectionCompletion)
class SectionCompletionAdmin(admin.ModelAdmin):
    list_display = ['student', 'section', 'completed_at', 'score']
    list_filter = ['section__course__track', 'section__course', 'completed_at']
    search_fields = ['student__first_name', 'student__last_name', 'section__title']
    ordering = ['-completed_at']

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    # NOTE: removed non-existent 'total_points_earned'
    list_display = ['student', 'total_sections_completed', 'current_streak', 'last_activity']
    list_filter = ['last_activity']
    search_fields = ['student__first_name', 'student__last_name']
    ordering = ['-total_sections_completed']

@admin.register(CodeChallenge)
class CodeChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'is_standalone', 'is_active']
    list_filter = ['difficulty', 'is_standalone', 'is_active']
    search_fields = ['title', 'description']
    ordering = ['title']

@admin.register(ChallengeSolution)
class ChallengeSolutionAdmin(admin.ModelAdmin):
    # NOTE: don't reference 'created_at' since your model doesn’t have it
    list_display = ['student', 'challenge', 'is_correct']
    list_filter = ['is_correct']  # removed created_at
    search_fields = ['student__first_name', 'student__last_name', 'challenge__title']
    ordering = ['-id']

# Legacy models kept minimal to avoid missing fields
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'genre', 'poster']
    list_filter = ['genre']
    search_fields = ['title']

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote', 'poster', 'movie']
    list_filter = ['movie']
    search_fields = ['quote', 'movie__title']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['comment', 'poster', 'quote']
    list_filter = []
    search_fields = ['comment', 'poster__first_name', 'poster__last_name']

@admin.register(UserQuote)
class UserQuoteAdmin(admin.ModelAdmin):
    # NOTE: removed non-existent 'created_at'
    list_display = ['user', 'quote']
    search_fields = ['user__first_name', 'user__last_name', 'quote__quote']
    ordering = ['-id']

# ---- Optional inlines (only for fields you actually have) ----

class CourseInline(admin.TabularInline):
    model = Course
    extra = 0
    fields = ['name', 'difficulty', 'estimated_hours', 'order', 'is_active']

class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ['title', 'section_type', 'estimated_minutes', 'order', 'is_active']

# Attach inlines safely
TrackAdmin.inlines = [CourseInline]
CourseAdmin.inlines = [SectionInline]