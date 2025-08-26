from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.utils import timezone
import json
from decimal import Decimal

from .models import (
    User, Track, Course, Section, TrackEnrollment,
    SectionCompletion, StudentProgress, UserWallet,
    PointTransaction, PointStructure, CodeChallenge,
    ChallengeSolution, Movie, Quote, Comment
)


def _get_or_create_wallet_and_progress(user):
    wallet, _ = UserWallet.objects.get_or_create(user=user)
    progress, _ = StudentProgress.objects.get_or_create(student=user)
    return wallet, progress


def index(request):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    tracks = Track.objects.get_with_progress(user)

    # ✅ compute once in Python (safe + readable)
    has_enrolled_tracks = any(getattr(t, 'is_enrolled', False) for t in tracks)

    recent_completions = SectionCompletion.objects.filter(
        student=user
    ).order_by('-completed_at')[:5].select_related('section', 'section__course')

    recent_transactions = PointTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    wallet, _ = UserWallet.objects.get_or_create(user=user)
    progress_summary, _ = StudentProgress.objects.get_or_create(student=user)
    progress_summary.update_streak()

    available_challenges = CodeChallenge.objects.filter(
        is_standalone=True, is_active=True
    ).exclude(
        id__in=ChallengeSolution.objects.filter(
            student=user, is_correct=True
        ).values_list('challenge_id', flat=True)
    )

    context = {
        'user': user,
        'tracks': tracks,
        'has_enrolled_tracks': has_enrolled_tracks,  # 👈 add this
        'recent_completions': recent_completions,
        'recent_transactions': recent_transactions,
        'wallet': wallet,
        'progress_summary': progress_summary,
        'available_challenges': available_challenges[:3],
        'overall_progress': user.get_overall_progress(),
    }
    return render(request, 'success.html', context)


def login(request):
    if request.method == "GET":
        return render(request, 'index.html')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        if User.objects.authenticate(email, password):
            user = User.objects.filter(email=email)[0]
            request.session['user'] = user.id
            return redirect('/success')
        messages.error(request, "Invalid email or password")
        return redirect('/login')
    




def register(request):
    if request.method == "GET":
        return render(request, 'index.html')

    if request.method == "POST":
        errors = User.objects.validate(request.POST)
        if errors:
            for _, value in errors.items():
                messages.error(request, value)
            return redirect('/register')

        new_user = User.objects.register(request.POST)
        request.session['user'] = new_user.id
        StudentProgress.objects.create(student=new_user)
        create_default_point_structures()
        messages.success(request, "Registration successful! Welcome to Coding Academy!")
        return redirect('/success')


def logout(request):
    request.session.flush()
    return redirect('/login')


def profile(request, user_id):
    if 'user' not in request.session:
        return redirect('/login')

    current_user = User.objects.get(id=request.session['user'])
    profile_user = get_object_or_404(User, id=user_id)

    wallet, progress_summary = _get_or_create_wallet_and_progress(profile_user)

    enrolled_tracks = []
    for enrollment in TrackEnrollment.objects.filter(student=profile_user, is_active=True).select_related('track'):
        track = enrollment.track
        track.progress = track.get_student_progress(profile_user)
        enrolled_tracks.append(track)

    recent_completions = (SectionCompletion.objects
                          .filter(student=profile_user)
                          .order_by('-completed_at')[:10]
                          .select_related('section', 'section__course'))

    recent_transactions = (PointTransaction.objects
                           .filter(user=profile_user)
                           .order_by('-created_at')[:10])

    challenges_solved = ChallengeSolution.objects.filter(student=profile_user, is_correct=True).count()

    payout_progress_percent = 0
    remaining_to_payout = Decimal('0.00')
    if wallet.payout_threshold and wallet.payout_threshold > 0:
        payout_progress_percent = min(
            100,
            int((wallet.total_earnings / wallet.payout_threshold) * 100)
        )
        remaining_to_payout = max(wallet.payout_threshold - wallet.total_earnings, Decimal('0.00'))

    context = {
        'user': current_user,
        'profile_user': profile_user,
        'wallet': wallet,
        'progress_summary': progress_summary,
        'enrolled_tracks': enrolled_tracks,
        'recent_completions': recent_completions,
        'recent_transactions': recent_transactions,
        'challenges_solved': challenges_solved,
        'total_challenges': CodeChallenge.objects.filter(is_active=True).count(),
        'is_own_profile': current_user.id == profile_user.id,
        'payout_progress_percent': payout_progress_percent,
        'remaining_to_payout': remaining_to_payout,
        'total_completions': progress_summary.total_sections_completed,
    }
    return render(request, 'profile.html', context)


def tracks(request):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    all_tracks = Track.objects.get_with_progress(user)
    context = {'user': user, 'tracks': all_tracks}
    return render(request, 'tracks.html', context)


def track_detail(request, track_id):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    track = get_object_or_404(Track, id=track_id)

    if not track.is_accessible_to_user(user):
        messages.warning(request, f"This track requires a {track.access_level} subscription.")
        return redirect('/tracks')

    is_enrolled = TrackEnrollment.objects.filter(student=user, track=track, is_active=True).exists()
    courses = Course.objects.get_with_progress(user, track=track)
    track_progress = track.get_student_progress(user)

    track_leaders = (User.objects
                     .filter(point_transactions__related_track_id=track_id,
                             point_transactions__transaction_type='section_complete')
                     .annotate(
                         track_points=Sum('point_transactions__points_earned',
                                          filter=Q(point_transactions__related_section_id__in=Section.objects
                                                   .filter(course__track=track).values_list('id', flat=True)))
                     )
                     .order_by('-track_points')[:10])

    context = {
        'user': user,
        'track': track,
        'courses': courses,
        'is_enrolled': is_enrolled,
        'track_progress': track_progress,
        'track_leaders': track_leaders,
        'total_possible_points': track.get_total_possible_points(),
    }
    return render(request, 'track_detail.html', context)


def course_detail(request, course_id):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    course = get_object_or_404(Course, id=course_id)

    if not course.track.is_accessible_to_user(user):
        messages.warning(request, "You don't have access to this track.")
        return redirect('/tracks')

    if not course.is_unlocked_for_student(user):
        messages.warning(request, "Complete the prerequisite courses first!")
        return redirect(f'/track/{course.track.id}')

    is_enrolled = TrackEnrollment.objects.filter(student=user, track=course.track, is_active=True).exists()
    if not is_enrolled:
        messages.warning(request, "You must enroll in the track first!")
        return redirect(f'/track/{course.track.id}')

    sections = Section.objects.get_with_progress(user, course=course)
    course_progress = course.get_student_progress(user)
    next_section = course.get_next_incomplete_section(user)

    context = {
        'user': user,
        'course': course,
        'sections': sections,
        'course_progress': course_progress,
        'next_section': next_section,
    }
    return render(request, 'course_detail.html', context)


def section_detail(request, section_id):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    section = get_object_or_404(Section, id=section_id)

    if not section.course.track.is_accessible_to_user(user):
        messages.warning(request, "You don't have access to this content.")
        return redirect('/tracks')

    if not section.is_unlocked_for_student(user):
        messages.warning(request, "Complete the previous sections first!")
        return redirect(f'/course/{section.course.id}')

    is_completed = SectionCompletion.objects.filter(student=user, section=section).exists()
    code_challenges = section.code_challenges.all()
    point_value = section.get_point_value()

    context = {
        'user': user,
        'section': section,
        'is_completed': is_completed,
        'code_challenges': code_challenges,
        'point_value': point_value,
    }
    return render(request, 'section_detail.html', context)


@csrf_exempt
def enroll_track(request, track_id):
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not logged in'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    user = User.objects.get(id=request.session['user'])
    track = get_object_or_404(Track, id=track_id)

    if not track.is_accessible_to_user(user):
        return JsonResponse({'success': False, 'error': f'Requires {track.access_level} subscription'})

    enrollment, created = TrackEnrollment.objects.get_or_create(
        student=user, track=track, defaults={'is_active': True}
    )
    if not created:
        enrollment.is_active = True
        enrollment.save()

    messages.success(request, f"Successfully enrolled in {track.name}!")
    return JsonResponse({'success': True})


@csrf_exempt
def complete_section(request, section_id):
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not logged in'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    user = User.objects.get(id=request.session['user'])
    section = get_object_or_404(Section, id=section_id)

    if not section.is_unlocked_for_student(user):
        return JsonResponse({'success': False, 'error': 'Section is locked'})

    completion, created = SectionCompletion.objects.get_or_create(
        student=user, section=section, defaults={'score': request.POST.get('score')}
    )

    if created:
        progress, _ = StudentProgress.objects.get_or_create(student=user)
        progress.total_sections_completed += 1
        progress.last_activity = timezone.now()
        progress.update_streak()

        track_completion_check(user, section.course.track)
        messages.success(request, f"Completed: {section.title}! Earned {section.get_point_value()} points!")
    else:
        messages.info(request, "Section already completed.")

    return JsonResponse({'success': True, 'created': created})


def challenges(request):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])

    easy_challenges = CodeChallenge.objects.filter(difficulty='easy', is_standalone=True, is_active=True)
    medium_challenges = CodeChallenge.objects.filter(difficulty='medium', is_standalone=True, is_active=True)
    hard_challenges = CodeChallenge.objects.filter(difficulty='hard', is_standalone=True, is_active=True)

    solved_challenge_ids = ChallengeSolution.objects.filter(
        student=user, is_correct=True
    ).values_list('challenge_id', flat=True)

    context = {
        'user': user,
        'easy_challenges': easy_challenges,
        'medium_challenges': medium_challenges,
        'hard_challenges': hard_challenges,
        'solved_challenge_ids': list(solved_challenge_ids),
    }
    return render(request, 'challenges.html', context)


def challenge_detail(request, challenge_id):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    challenge = get_object_or_404(CodeChallenge, id=challenge_id)

    existing_solution = ChallengeSolution.objects.filter(
        student=user, challenge=challenge
    ).first()

    points, cash_value = challenge.get_point_value()

    context = {
        'user': user,
        'challenge': challenge,
        'existing_solution': existing_solution,
        'point_value': points,
        'cash_value': cash_value,
    }
    return render(request, 'challenge_detail.html', context)


@csrf_exempt
def submit_challenge_solution(request, challenge_id):
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not logged in'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    user = User.objects.get(id=request.session['user'])
    challenge = get_object_or_404(CodeChallenge, id=challenge_id)

    data = json.loads(request.body or '{}')
    solution_code = data.get('code', '')

    is_correct = validate_solution(solution_code, challenge)

    solution, created = ChallengeSolution.objects.get_or_create(
        student=user, challenge=challenge,
        defaults={'solution_code': solution_code, 'is_correct': is_correct}
    )
    if not created:
        solution.solution_code = solution_code
        solution.is_correct = is_correct
        solution.save()

    if is_correct:
        points, cash_value = challenge.get_point_value()
        return JsonResponse({'success': True, 'correct': True, 'points': points, 'cash_value': float(cash_value)})
    return JsonResponse({'success': True, 'correct': False})


def leaderboard(request):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])

    top_earners = User.objects.select_related('wallet').order_by('-wallet__total_earnings')[:50]

    top_points = (User.objects.select_related('wallet')
                  .annotate(total_points=F('wallet__learning_points') +
                            F('wallet__challenge_points') +
                            F('wallet__bonus_points'))
                  .order_by('-total_points')[:50])

    recent_activity = (SectionCompletion.objects.select_related(
        'student', 'section', 'section__course', 'section__course__track'
    ).order_by('-completed_at')[:20])

    context = {
        'user': user,
        'top_earners': top_earners,
        'top_points': top_points,
        'recent_activity': recent_activity,
    }
    return render(request, 'leaderboard.html', context)


def activity(request):
    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.get(id=request.session['user'])
    recent_transactions = PointTransaction.objects.select_related('user').order_by('-created_at')[:50]
    paginator = Paginator(recent_transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'user': user, 'transactions': page_obj}
    return render(request, 'activity.html', context)


def settings(request, user_id):
    if 'user' not in request.session:
        return redirect('/login')

    current_user = User.objects.get(id=request.session['user'])
    if current_user.id != int(user_id):
        messages.error(request, "You can only edit your own settings.")
        return redirect(f'/profile/{current_user.id}')

    wallet, _ = _get_or_create_wallet_and_progress(current_user)

    if request.method == 'POST':
        current_user.first_name = request.POST.get('first_name', current_user.first_name)
        current_user.last_name = request.POST.get('last_name', current_user.last_name)
        current_user.image_url = request.POST.get('image_url', current_user.image_url)
        current_user.save()

        wallet.payout_email = request.POST.get('payout_email', wallet.payout_email)
        threshold_raw = request.POST.get('payout_threshold', wallet.payout_threshold)
        try:
            wallet.payout_threshold = Decimal(threshold_raw)
        except Exception:
            pass
        wallet.save()

        messages.success(request, "Settings updated successfully!")
        return redirect(f'/settings/{user_id}')

    payout_progress_percent = 0
    remaining_to_payout = Decimal('0.00')
    if wallet.payout_threshold and wallet.payout_threshold > 0:
        payout_progress_percent = min(
            100,
            int((wallet.total_earnings / wallet.payout_threshold) * 100)
        )
        remaining_to_payout = max(wallet.payout_threshold - wallet.total_earnings, Decimal('0.00'))

    context = {
        'user': current_user,
        'wallet': wallet,
        'payout_progress_percent': payout_progress_percent,
        'remaining_to_payout': remaining_to_payout,
    }
    return render(request, 'settings.html', context)


# Helper functions

def create_default_point_structures():
    defaults = [
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
    for content_type, points, cash_per_point in defaults:
        PointStructure.objects.get_or_create(
            content_type=content_type,
            defaults={'base_points': points, 'cash_value_per_point': cash_per_point}
        )


def track_completion_check(user, track):
    total_sections = Section.objects.filter(course__track=track).count()
    completed_sections = SectionCompletion.objects.filter(
        student=user, section__course__track=track
    ).count()

    if total_sections > 0 and completed_sections >= total_sections:
        already_awarded = PointTransaction.objects.filter(
            user=user, transaction_type='track_complete', related_track_id=track.id
        ).exists()
        if not already_awarded:
            try:
                ps = PointStructure.objects.get(content_type='track_completion')
                points = ps.base_points
                cash_value = ps.total_cash_value
            except PointStructure.DoesNotExist:
                points = 1000
                cash_value = Decimal('10.00')

            wallet = user.wallet
            wallet.bonus_points += points
            wallet.total_earnings += cash_value
            wallet.save()

            PointTransaction.objects.create(
                user=user,
                transaction_type='track_complete',
                points_earned=points,
                cash_value=cash_value,
                related_track_id=track.id,
                description=f"Track Completed: {track.name}"
            )


def validate_solution(code, challenge):
    return ("print" in (code or "").lower()) and ("hello world" in (code or "").lower())


# Legacy/compat views for Swift pages
def swift_html(request, page_num):
    if 'user' not in request.session:
        return redirect('/login')
    user = User.objects.get(id=request.session['user'])
    return render(request, 'swift.html', {'user': user, 'page_num': page_num, 'next_page': page_num + 1})


@csrf_exempt
def submit_code(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    try:
        data = json.loads(request.body or '{}')
        code = data.get('code', '')
        if "print" in code.lower() and "hello world" in code.lower():
            return JsonResponse({'status': 'success', 'points': 50})
        return JsonResponse({'status': 'error', 'message': 'Incorrect solution'})
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def api_user_progress(request, user_id):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        user = User.objects.get(id=user_id)
        wallet = user.wallet
        enrolled_tracks = []
        for enrollment in TrackEnrollment.objects.filter(student=user, is_active=True):
            track = enrollment.track
            progress = track.get_student_progress(user)
            enrolled_tracks.append({'id': track.id, 'name': track.name, 'progress': progress})

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
    

def home(request):
    """Public landing page (marketing + overview)."""
    user = None
    if 'user' in request.session:
        try:
            user = User.objects.get(id=request.session['user'])
        except User.DoesNotExist:
            user = None
    return render(request, 'home.html', {'user': user})