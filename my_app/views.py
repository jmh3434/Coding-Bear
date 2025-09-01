# my_app/views.py - COMPLETE OVERHAUL
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, Count
from django.utils import timezone
import json
from decimal import Decimal

from .models import (
    User, Track, Course, Section, TrackEnrollment,
    SectionCompletion, StudentProgress, UserWallet,
    PointTransaction, PointStructure, CodeChallenge,
    ChallengeSolution, Movie, Quote, Comment
)

def _ensure_user_logged_in(request):
    """Helper to check if user is logged in"""
    if 'user' not in request.session:
        return None
    try:
        return User.objects.get(id=request.session['user'])
    except User.DoesNotExist:
        request.session.flush()
        return None

def _get_or_create_wallet_and_progress(user):
    """Helper to get or create user wallet and progress"""
    wallet, _ = UserWallet.objects.get_or_create(user=user)
    progress, _ = StudentProgress.objects.get_or_create(student=user)
    return wallet, progress

# ===== PUBLIC PAGES =====

def home(request):
    """Public landing page"""
    user = _ensure_user_logged_in(request)
    if user:
        return redirect('/dashboard/')
    
    context = {
        'total_students': User.objects.count(),
        'total_challenges': CodeChallenge.objects.filter(is_active=True).count(),
        'total_tracks': Track.objects.filter(is_active=True).count(),
    }
    return render(request, 'home.html', context)

def login(request):
    """Login page"""
    if request.method == "GET":
        # Redirect if already logged in
        user = _ensure_user_logged_in(request)
        if user:
            return redirect('/dashboard/')
        return render(request, 'index.html')

    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, "Please provide both email and password")
            return redirect('/login/')
            
        if User.objects.authenticate(email, password):
            user = User.objects.filter(email=email).first()
            request.session['user'] = user.id
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect('/dashboard/')
        else:
            messages.error(request, "Invalid email or password")
            return redirect('/login/')

def register(request):
    """Registration page"""
    if request.method == "GET":
        user = _ensure_user_logged_in(request)
        if user:
            return redirect('/dashboard/')
        return render(request, 'index.html')

    if request.method == "POST":
        errors = User.objects.validate(request.POST)
        if errors:
            for _, value in errors.items():
                messages.error(request, value)
            return redirect('/')

        new_user = User.objects.register(request.POST)
        request.session['user'] = new_user.id
        
        # Create user wallet and progress
        _get_or_create_wallet_and_progress(new_user)
        
        messages.success(request, "Welcome to Coding Academy! Start learning and earning!")
        return redirect('/dashboard/')

def logout(request):
    """Logout"""
    request.session.flush()
    messages.success(request, "Successfully logged out!")
    return redirect('/')

# ===== MAIN DASHBOARD =====

def dashboard(request):
    """Main dashboard - renamed from index for clarity"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    # Get user data
    wallet, progress = _get_or_create_wallet_and_progress(user)
    
    # Get enrolled tracks with progress
    enrolled_tracks = []
    enrollments = TrackEnrollment.objects.filter(student=user, is_active=True).select_related('track')
    for enrollment in enrollments:
        track = enrollment.track
        track.progress = track.get_student_progress(user)
        enrolled_tracks.append(track)

    # Get available tracks (not enrolled)
    enrolled_track_ids = [t.id for t in enrolled_tracks]
    available_tracks = Track.objects.filter(is_active=True).exclude(id__in=enrolled_track_ids)
    
    # Filter by access level
    accessible_tracks = []
    for track in available_tracks:
        if track.is_accessible_to_user(user):
            accessible_tracks.append(track)

    # Get recent activity
    recent_completions = SectionCompletion.objects.filter(
        student=user
    ).select_related('section', 'section__course', 'section__course__track').order_by('-completed_at')[:3]

    recent_transactions = PointTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    # Get quick challenges
    solved_challenge_ids = ChallengeSolution.objects.filter(
        student=user, is_correct=True
    ).values_list('challenge_id', flat=True)
    
    available_challenges = CodeChallenge.objects.filter(
        is_standalone=True, is_active=True
    ).exclude(id__in=solved_challenge_ids)[:3]

    # Update streak
    progress.update_streak()

    context = {
        'user': user,
        'wallet': wallet,
        'progress_summary': progress,
        'enrolled_tracks': enrolled_tracks,
        'available_tracks': accessible_tracks,
        'recent_completions': recent_completions,
        'recent_transactions': recent_transactions,
        'available_challenges': available_challenges,
        'has_enrolled_tracks': len(enrolled_tracks) > 0,
        'overall_progress': user.get_overall_progress(),
    }
    return render(request, 'success.html', context)

# ===== LEARNING PAGES =====

def tracks(request):
    """All available tracks"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    all_tracks = Track.objects.filter(is_active=True).order_by('order', 'name')
    
    # Add enrollment and access info
    for track in all_tracks:
        track.is_enrolled = TrackEnrollment.objects.filter(
            student=user, track=track, is_active=True
        ).exists()
        track.is_accessible = track.is_accessible_to_user(user)
        if track.is_enrolled:
            track.progress = track.get_student_progress(user)
        else:
            track.progress = 0

    context = {
        'user': user,
        'tracks': all_tracks,
    }
    return render(request, 'tracks.html', context)

# Add this view to your views.py file

def my_courses(request):
    """My courses page showing enrolled tracks and progress"""
    if 'user' not in request.session:
        return redirect('/login/')

    try:
        user = User.objects.get(id=request.session['user'])
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    # Get enrolled tracks with progress
    enrolled_tracks = []
    enrollments = TrackEnrollment.objects.filter(
        student=user, is_active=True
    ).select_related('track').order_by('track__order', 'track__name')
    
    for enrollment in enrollments:
        track = enrollment.track
        track.student_progress = track.get_student_progress(user)
        track.is_accessible = track.is_accessible_to_user(user)
        enrolled_tracks.append(track)

    # Get wallet and progress info
    wallet, progress = _get_or_create_wallet_and_progress(user)
    
    # Recent activity
    recent_completions = SectionCompletion.objects.filter(
        student=user
    ).select_related('section', 'section__course', 'section__course__track').order_by('-completed_at')[:5]

    context = {
        'user': user,
        'enrolled_tracks': enrolled_tracks,
        'wallet': wallet,
        'progress': progress,
        'recent_completions': recent_completions,
        'total_earnings': wallet.total_earnings,
        'total_points': wallet.total_points,
    }
    return render(request, 'my_courses.html', context)


    context = {
        'user': user,
        'enrolled_tracks': enrolled_tracks,
        'wallet': wallet,
        'progress': progress,
        'recent_completions': recent_completions,
        'total_earnings': wallet.total_earnings,
        'total_points': wallet.total_points,
    }
    return render(request, 'my_courses.html', context)

    # Get recent completions
    recent_completions = SectionCompletion.objects.filter(
        student=user
    ).select_related('section', 'section__course', 'section__course__track').order_by('-completed_at')[:10]

    # Get stats
    wallet, progress = _get_or_create_wallet_and_progress(user)
    total_sections_completed = SectionCompletion.objects.filter(student=user).count()
    total_sections_available = Section.objects.filter(
        course__track__in=[t.id for t in enrolled_tracks], is_active=True
    ).count()

    context = {
        'user': user,
        'enrolled_tracks': enrolled_tracks,
        'recent_completions': recent_completions,
        'wallet': wallet,
        'progress_summary': progress,
        'total_sections_completed': total_sections_completed,
        'total_sections_available': total_sections_available,
        'completion_percentage': (total_sections_completed / total_sections_available * 100) if total_sections_available > 0 else 0,
    }
    return render(request, 'my_courses.html', context)

def track_detail(request, track_id):
    """Individual track page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    track = get_object_or_404(Track, id=track_id, is_active=True)
    
    # Check access
    if not track.is_accessible_to_user(user):
        messages.warning(request, f"This track requires a {track.get_access_level_display()} subscription.")
        return redirect('/tracks/')

    # Check enrollment
    is_enrolled = TrackEnrollment.objects.filter(
        student=user, track=track, is_active=True
    ).exists()
    
    # Get courses
    courses = Course.objects.filter(track=track, is_active=True).order_by('order')
    for course in courses:
        course.progress = course.get_student_progress(user)
        course.is_unlocked = course.is_unlocked_for_student(user)
        course.sections_count = course.sections.filter(is_active=True).count()

    # Get track progress
    track_progress = track.get_student_progress(user) if is_enrolled else 0

    # Get recent completions in this track
    recent_completions = SectionCompletion.objects.filter(
        student=user, section__course__track=track
    ).select_related('section', 'section__course').order_by('-completed_at')[:5]

    context = {
        'user': user,
        'track': track,
        'courses': courses,
        'is_enrolled': is_enrolled,
        'track_progress': track_progress,
        'recent_completions': recent_completions,
        'total_courses': courses.count(),
        'completed_courses': sum(1 for c in courses if c.progress >= 100),
    }
    return render(request, 'track_detail.html', context)

def course_detail(request, course_id):
    """Individual course page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Check access and enrollment
    if not course.track.is_accessible_to_user(user):
        messages.warning(request, "You don't have access to this track.")
        return redirect('/tracks/')

    is_enrolled = TrackEnrollment.objects.filter(
        student=user, track=course.track, is_active=True
    ).exists()
    
    if not is_enrolled:
        messages.warning(request, "You must enroll in the track first!")
        return redirect(f'/track/{course.track.id}/')

    # Check prerequisites
    if not course.is_unlocked_for_student(user):
        messages.warning(request, "Complete the prerequisite courses first!")
        return redirect(f'/track/{course.track.id}/')

    # Get sections
    sections = Section.objects.filter(course=course, is_active=True).order_by('order')
    for section in sections:
        section.is_completed = SectionCompletion.objects.filter(
            student=user, section=section
        ).exists()
        section.is_unlocked = section.is_unlocked_for_student(user)

    # Get course progress
    course_progress = course.get_student_progress(user)
    next_section = course.get_next_incomplete_section(user)

    context = {
        'user': user,
        'course': course,
        'sections': sections,
        'course_progress': course_progress,
        'next_section': next_section,
        'total_sections': sections.count(),
        'completed_sections': sum(1 for s in sections if s.is_completed),
    }
    return render(request, 'course_detail.html', context)

def section_detail(request, section_id):
    """Individual section/lesson page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    section = get_object_or_404(Section, id=section_id, is_active=True)
    
    # Check access
    if not section.course.track.is_accessible_to_user(user):
        messages.warning(request, "You don't have access to this content.")
        return redirect('/tracks/')

    # Check if section is unlocked
    if not section.is_unlocked_for_student(user):
        messages.warning(request, "Complete the previous sections first!")
        return redirect(f'/course/{section.course.id}/')

    # Check completion
    is_completed = SectionCompletion.objects.filter(
        student=user, section=section
    ).exists()

    # Get section challenges
    challenges = section.code_challenges.filter(is_active=True)
    
    # Get next and previous sections
    next_section = Section.objects.filter(
        course=section.course, order__gt=section.order, is_active=True
    ).order_by('order').first()
    
    prev_section = Section.objects.filter(
        course=section.course, order__lt=section.order, is_active=True
    ).order_by('-order').first()

    context = {
        'user': user,
        'section': section,
        'is_completed': is_completed,
        'challenges': challenges,
        'next_section': next_section,
        'prev_section': prev_section,
        'point_value': section.get_point_value(),
    }
    return render(request, 'section_detail.html', context)

# ===== CHALLENGES =====

def challenges(request):
    """Coding challenges page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    # Get all challenges
    all_challenges = CodeChallenge.objects.filter(is_active=True)
    
    # Filter by difficulty if requested
    difficulty_filter = request.GET.get('difficulty')
    if difficulty_filter in ['easy', 'medium', 'hard']:
        all_challenges = all_challenges.filter(difficulty=difficulty_filter)

    # Separate by difficulty
    easy_challenges = all_challenges.filter(difficulty='easy')
    medium_challenges = all_challenges.filter(difficulty='medium') 
    hard_challenges = all_challenges.filter(difficulty='hard')

    # Get solved challenges
    solved_challenge_ids = list(
        ChallengeSolution.objects.filter(student=user, is_correct=True)
        .values_list('challenge_id', flat=True)
    )

    context = {
        'user': user,
        'easy_challenges': easy_challenges,
        'medium_challenges': medium_challenges,
        'hard_challenges': hard_challenges,
        'solved_challenge_ids': solved_challenge_ids,
        'total_challenges': all_challenges.count(),
        'total_solved': len(solved_challenge_ids),
        'difficulty_filter': difficulty_filter,
    }
    return render(request, 'challenges.html', context)

def challenge_detail(request, challenge_id):
    """Individual challenge page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    challenge = get_object_or_404(CodeChallenge, id=challenge_id, is_active=True)
    
    # Get existing solution
    existing_solution = ChallengeSolution.objects.filter(
        student=user, challenge=challenge
    ).first()

    # Get point value
    points, cash_value = challenge.get_point_value()

    context = {
        'user': user,
        'challenge': challenge,
        'existing_solution': existing_solution,
        'point_value': points,
        'cash_value': cash_value,
        'is_solved': existing_solution and existing_solution.is_correct,
    }
    return render(request, 'challenge_detail.html', context)

# ===== USER PAGES =====

def profile(request, user_id):
    """User profile page"""
    current_user = _ensure_user_logged_in(request)
    if not current_user:
        return redirect('/login/')

    profile_user = get_object_or_404(User, id=user_id)
    wallet, progress = _get_or_create_wallet_and_progress(profile_user)

    # Get enrolled tracks with progress
    enrolled_tracks = []
    for enrollment in TrackEnrollment.objects.filter(student=profile_user, is_active=True).select_related('track'):
        track = enrollment.track
        track.progress = track.get_student_progress(profile_user)
        enrolled_tracks.append(track)

    # Get recent activity
    recent_completions = SectionCompletion.objects.filter(
        student=profile_user
    ).select_related('section', 'section__course').order_by('-completed_at')[:10]

    recent_transactions = PointTransaction.objects.filter(
        user=profile_user
    ).order_by('-created_at')[:10]

    # Get challenge stats
    challenges_solved = ChallengeSolution.objects.filter(
        student=profile_user, is_correct=True
    ).count()
    
    total_challenges = CodeChallenge.objects.filter(is_active=True).count()

    context = {
        'user': current_user,
        'profile_user': profile_user,
        'wallet': wallet,
        'progress_summary': progress,
        'enrolled_tracks': enrolled_tracks,
        'recent_completions': recent_completions,
        'recent_transactions': recent_transactions,
        'challenges_solved': challenges_solved,
        'total_challenges': total_challenges,
        'is_own_profile': current_user.id == profile_user.id,
    }
    return render(request, 'profile.html', context)

def settings(request, user_id):
    """User settings page"""
    current_user = _ensure_user_logged_in(request)
    if not current_user:
        return redirect('/login/')
        
    if current_user.id != int(user_id):
        messages.error(request, "You can only edit your own settings.")
        return redirect(f'/profile/{current_user.id}/')

    wallet, _ = _get_or_create_wallet_and_progress(current_user)

    if request.method == 'POST':
        # Update user info
        current_user.first_name = request.POST.get('first_name', current_user.first_name)
        current_user.last_name = request.POST.get('last_name', current_user.last_name)
        current_user.image_url = request.POST.get('image_url', current_user.image_url)
        current_user.save()

        # Update wallet settings
        wallet.payout_email = request.POST.get('payout_email', wallet.payout_email)
        try:
            wallet.payout_threshold = Decimal(request.POST.get('payout_threshold', wallet.payout_threshold))
        except (ValueError, TypeError):
            pass
        wallet.save()

        messages.success(request, "Settings updated successfully!")
        return redirect(f'/settings/{user_id}/')

    context = {
        'user': current_user,
        'wallet': wallet,
    }
    return render(request, 'settings.html', context)

def activity(request):
    """User activity page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    # Get activity data
    recent_completions = SectionCompletion.objects.filter(
        student=user
    ).select_related('section', 'section__course', 'section__course__track').order_by('-completed_at')[:20]

    recent_solutions = ChallengeSolution.objects.filter(
        student=user
    ).select_related('challenge').order_by('-submitted_at')[:20]

    recent_transactions = PointTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:20]

    # Get enrollments
    enrollments = TrackEnrollment.objects.filter(
        student=user, is_active=True
    ).select_related('track')

    # Get stats
    wallet, progress = _get_or_create_wallet_and_progress(user)

    context = {
        'user': user,
        'recent_completions': recent_completions,
        'recent_solutions': recent_solutions,
        'recent_transactions': recent_transactions,
        'enrollments': enrollments,
        'wallet': wallet,
        'total_points': wallet.total_points,
        'total_earnings': wallet.total_earnings,
        'can_payout': wallet.can_request_payout,
        'current_streak': progress.current_streak,
        'overall_progress': user.get_overall_progress(),
        'now': timezone.now(),
    }
    return render(request, 'activity.html', context)

def leaderboard(request):
    """Leaderboard page"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')

    # Get top earners
    top_earners = []
    users_with_wallets = User.objects.filter(wallet__isnull=False).select_related('wallet')
    for u in users_with_wallets:
        if u.wallet and u.wallet.total_earnings > 0:
            top_earners.append(u)
    
    top_earners.sort(key=lambda x: x.wallet.total_earnings, reverse=True)
    top_earners = top_earners[:50]

    # Get users with most points
    most_points = []
    for u in users_with_wallets:
        if u.wallet:
            total_points = u.wallet.learning_points + u.wallet.challenge_points + u.wallet.bonus_points
            if total_points > 0:
                most_points.append({'user': u, 'total_points': total_points})
    
    most_points.sort(key=lambda x: x['total_points'], reverse=True)
    most_points = most_points[:50]

    context = {
        'user': user,
        'top_earners': top_earners,
        'most_points': most_points,
        'now': timezone.now(),
    }
    return render(request, 'leaderboard.html', context)

# ===== ACTIONS =====

@csrf_exempt
def enroll_track(request, track_id):
    """Enroll in a track"""
    user = _ensure_user_logged_in(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Not logged in'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    track = get_object_or_404(Track, id=track_id)
    
    # Check access
    if not track.is_accessible_to_user(user):
        return JsonResponse({
            'success': False, 
            'error': f'This track requires a {track.get_access_level_display()} subscription'
        })

    # Create enrollment
    enrollment, created = TrackEnrollment.objects.get_or_create(
        student=user, track=track,
        defaults={'is_active': True}
    )
    
    if not created and not enrollment.is_active:
        enrollment.is_active = True
        enrollment.save()

    return JsonResponse({'success': True, 'message': f'Successfully enrolled in {track.name}!'})

@csrf_exempt  
def complete_section(request, section_id):
    """Mark section as completed"""
    user = _ensure_user_logged_in(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Not logged in'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    section = get_object_or_404(Section, id=section_id)
    
    # Check if section is unlocked
    if not section.is_unlocked_for_student(user):
        return JsonResponse({'success': False, 'error': 'Section is locked'})

    # Create completion
    completion, created = SectionCompletion.objects.get_or_create(
        student=user, section=section,
        defaults={'score': request.POST.get('score')}
    )

    if created:
        # Update progress
        progress, _ = StudentProgress.objects.get_or_create(student=user)
        progress.total_sections_completed += 1
        progress.last_activity = timezone.now()
        progress.update_streak()

        return JsonResponse({
            'success': True, 
            'created': True,
            'message': f'Section completed! Earned {section.get_point_value()} points!'
        })
    else:
        return JsonResponse({
            'success': True, 
            'created': False,
            'message': 'Section already completed'
        })

@csrf_exempt
def submit_challenge_solution(request, challenge_id):
    """Submit solution for coding challenge"""
    user = _ensure_user_logged_in(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Not logged in'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    challenge = get_object_or_404(CodeChallenge, id=challenge_id)
    
    try:
        data = json.loads(request.body)
        solution_code = data.get('code', '')
    except json.JSONDecodeError:
        solution_code = request.POST.get('code', '')

    # Simple validation (you can make this more sophisticated)
    is_correct = validate_challenge_solution(solution_code, challenge)

    # Save solution
    solution, created = ChallengeSolution.objects.get_or_create(
        student=user, challenge=challenge,
        defaults={
            'solution_code': solution_code, 
            'is_correct': is_correct
        }
    )
    
    if not created:
        solution.solution_code = solution_code
        solution.is_correct = is_correct
        solution.save()

    if is_correct:
        points, cash_value = challenge.get_point_value()
        return JsonResponse({
            'success': True,
            'correct': True,
            'points': points,
            'cash_value': float(cash_value),
            'message': f'Correct! Earned {points} points (${cash_value})!'
        })
    else:
        return JsonResponse({
            'success': True,
            'correct': False,
            'message': 'Not quite right. Try again!'
        })

def validate_challenge_solution(code, challenge):
    """Simple challenge validation - you can make this more sophisticated"""
    code_lower = code.lower().strip()
    
    if "hello" in challenge.title.lower():
        return "hello" in code_lower and "world" in code_lower
    elif "sum" in challenge.title.lower():
        return "return" in code_lower and ("a + b" in code_lower or "a+b" in code_lower)
    elif "maximum" in challenge.title.lower() or "max" in challenge.title.lower():
        return "max(" in code_lower or "maximum" in code_lower
    elif "vowel" in challenge.title.lower():
        return "vowel" in code_lower and ("count" in code_lower or "sum" in code_lower)
    elif "fibonacci" in challenge.title.lower():
        return "fibonacci" in code_lower or ("fib" in code_lower and "append" in code_lower)
    elif "palindrome" in challenge.title.lower():
        return "palindrome" in code_lower or ("::-1" in code_lower or "reverse" in code_lower)
    else:
        # Default validation - just check if it's not empty
        return len(code.strip()) > 10

# ===== LEGACY VIEWS (keep for compatibility) =====

def swift_html(request, page_num):
    """Legacy Swift pages"""
    user = _ensure_user_logged_in(request)
    if not user:
        return redirect('/login/')
    return render(request, 'swift.html', {
        'user': user, 
        'page_num': page_num, 
        'next_page': page_num + 1
    })

@csrf_exempt
def submit_code(request, expected_output=None):
    """Legacy code submission"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    
    try:
        data = json.loads(request.body or '{}')
        code = data.get('code', '').strip()
        
        if not expected_output:
            if "print" in code.lower() and "hello world" in code.lower():
                return JsonResponse({
                    'status': 'success', 
                    'points': 50,
                    'output_code': 'Hello, World!'
                })
            return JsonResponse({
                'status': 'error', 
                'message': 'Incorrect solution',
                'output_code': 'No output'
            })
        
        # Extract print statements
        import re
        print_matches = re.findall(r'print\s*\(\s*["\']([^"\']*)["\']', code)
        
        if print_matches:
            actual_output = print_matches[0]
            if actual_output.strip() == expected_output.strip():
                return JsonResponse({
                    'status': 'success',
                    'points': 50,
                    'output_code': actual_output
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Output doesn\'t match expected',
                    'output_code': actual_output,
                    'expected': expected_output
                })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No output detected',
                'output_code': 'No output'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': f'Error processing code: {str(e)}',
            'output_code': 'Error'
        })

def api_user_progress(request, user_id):
    """API endpoint for user progress"""
    current_user = _ensure_user_logged_in(request)
    if not current_user:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        user = User.objects.get(id=user_id)
        wallet, _ = _get_or_create_wallet_and_progress(user)
        
        enrolled_tracks = []
        for enrollment in TrackEnrollment.objects.filter(student=user, is_active=True):
            track = enrollment.track
            progress = track.get_student_progress(user)
            enrolled_tracks.append({
                'id': track.id, 
                'name': track.name, 
                'progress': progress
            })

        return JsonResponse({
            'user_id': user.id,
            'full_name': user.full_name,
            'overall_progress': user.get_overall_progress(),
            'total_points': wallet.total_points,
            'total_earnings': float(wallet.total_earnings),
            'enrolled_tracks': enrolled_tracks
        })
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)



