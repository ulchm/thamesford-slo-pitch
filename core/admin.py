from django.contrib import admin
from .models import Team, Player, Location, Season, Game, Stats


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'logo']
    search_fields = ['name']
    list_filter = ['name']
    readonly_fields = ['is_active']
    
    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = 'Active'


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'number', 'is_captain']
    list_filter = ['team', 'is_captain']
    search_fields = ['user__first_name', 'user__last_name', 'user__username']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['title', 'starts']
    list_filter = ['starts']
    ordering = ['-starts']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['starts_at', 'away_team', 'home_team', 'home_score', 'away_score', 'season']
    list_filter = ['season', 'location']
    search_fields = ['home_team__name', 'away_team__name']
    date_hierarchy = 'starts_at'
    ordering = ['-starts_at']


@admin.register(Stats)
class StatsAdmin(admin.ModelAdmin):
    list_display = ['team', 'season', 'wins', 'losses', 'ties', 'points', 'percentage']
    list_filter = ['season']
    search_fields = ['team__name']
    readonly_fields = ['wins', 'losses', 'ties', 'points', 'percentage', 'runs_scored', 'runs_against']


