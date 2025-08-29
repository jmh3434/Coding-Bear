from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    # Public landing page
    path('', views.home, name='home'),

    # Authentication
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    # add this so /accounts/login/ works too
    path('accounts/login/', RedirectView.as_view(url='/login/', permanent=False)),

    # Main pages
    path('success/', views.index, name='dashboard'),

    # User profiles and settings
    path('profile/<int:user_id>/', views.profile, name='profile'),
    path('settings/<int:user_id>/', views.settings, name='settings'),

    # Learning paths
    path('tracks/', views.tracks, name='tracks'),
    path('track/<int:track_id>/', views.track_detail, name='track_detail'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('section/<int:section_id>/', views.section_detail, name='section_detail'),

    path("challenges/", views.challenges, name="challenges"),
    path("challenge/<int:challenge_id>/", views.challenge_detail, name="challenge_detail"),  # assumed existing
    # ...rest of your urls...
    path('challenge/<int:challenge_id>/submit/', views.submit_challenge_solution, name='submit_challenge'),

    

    # Actions
    path('enroll/<int:track_id>/', views.enroll_track, name='enroll_track'),
    path('complete/<int:section_id>/', views.complete_section, name='complete_section'),

    # Community & Progress
    path('activity/', views.activity, name='activity'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Swift Course Pages / API (unchanged)
    path('swift_html/<int:page_num>/', views.swift_html, name='swift_html'),
    path('submit_code/', views.submit_code, name='submit_code'),
    path('api/user/<int:user_id>/progress/', views.api_user_progress, name='api_user_progress'),
]