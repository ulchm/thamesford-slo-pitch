from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('schedule/', views.schedule, name='schedule'),
    path('standings/', views.standings, name='standings'),
    path('teams/', views.teams, name='teams'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('news/', views.news, name='news'),
    path('gallery/', views.gallery, name='gallery'),
    path('gallery/<slug:slug>/', views.gallery_category, name='gallery_category'),
    path('rules/', views.rules, name='rules'),
    path('contact/', views.contact, name='contact'),
]