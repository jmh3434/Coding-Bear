from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('register', views.register),
    path('login', views.login),
    path('logout', views.logout),
    path('success', views.success),
    path('process_movie', views.process_movie),
    path('add_quote',views.add_quote),
    path('quiz',views.quiz),
    path('submit_answer/<int:quote_id>',views.submit_answer),
    path('clear',views.clear),
    path('sample',views.sample),
    path('profile/<int:id>',views.profile),
    path('choose_genre',views.choose_genre),
    path('delete_quote/<int:id>',views.delete_quote),
    path('activity',views.activity),
    path('edit/<int:id>',views.edit),
    path('add_comment/<int:id>',views.add_comment),
    path('delete_comment/<int:id>',views.delete_comment),
    path('show_quiz',views.show_quiz),
    path('settings/<int:id>',views.settings),
    path('swift',views.swift),
    path('swiftui',views.swiftui),
]