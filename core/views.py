from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
import json
from .models import Team, Game, Season, Stats
from news.models import News
from gallery.models import Category, Photo
from .services import StatsCalculator


def home(request):
    """Home page with upcoming games, latest scores, and recent news."""
    current_season = Season.objects.current()
    recent_news = News.objects.filter(display_on_home=True).order_by('-posted_on')
    
    # Get upcoming games
    upcoming_games = Game.objects.filter(
        starts_at__gte=timezone.now()
    ).order_by('starts_at')[:4]
    
    # Get latest completed games with scores
    latest_scores = Game.objects.filter(
        starts_at__lt=timezone.now(),
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-starts_at')[:4]
    
    context = {
        'recent_news': recent_news,
        'upcoming_games': upcoming_games,
        'latest_scores': latest_scores,
        'current_season': current_season,
    }
    return render(request, 'core/home.html', context)


def schedule(request):
    """Display game schedule."""
    current_season = Season.objects.current()
    
    # Get season from query param or use current
    season_id = request.GET.get('season')
    if season_id:
        try:
            season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            season = current_season
    else:
        season = current_season
    
    games = Game.objects.filter(season=season).order_by('-starts_at')
    seasons = Season.objects.all()
    
    context = {
        'games': games,
        'seasons': seasons,
        'current_season': season,
    }
    return render(request, 'core/schedule.html', context)


def standings(request):
    """Display team standings with SPO tie-breaking."""
    current_season = Season.objects.current()

    # Get season from query param or use current
    season_id = request.GET.get('season')
    if season_id:
        try:
            season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            season = current_season
    else:
        season = current_season

    if season:
        # Apply SPO tie-breaking rules
        standings = Stats.objects.apply_spo_standings(season)
        # Filter out teams with no games played
        standings = [s for s in standings if s.games_played() > 0]

        # Collect tie-breaking explanations
        tie_explanations = {}
        for stat in standings:
            if stat.tie_breaker_symbol:
                symbol = stat.tie_breaker_symbol
                if symbol not in tie_explanations:
                    tie_explanations[symbol] = stat.tie_breaker_reason
    else:
        standings = []
        tie_explanations = {}

    seasons = Season.objects.all()

    context = {
        'standings': standings,
        'seasons': seasons,
        'current_season': season,
        'tie_explanations': tie_explanations,
    }
    return render(request, 'core/standings.html', context)


def teams(request):
    """Display all teams."""
    teams = Team.objects.all().order_by('name')
    
    context = {
        'teams': teams,
    }
    return render(request, 'core/teams.html', context)


def team_detail(request, team_id):
    """Display team details."""
    team = get_object_or_404(Team, id=team_id)
    current_season = Season.objects.current()
    calculator = StatsCalculator()
    
    # Calculate team stats for current season in real-time
    current_stats = None
    if current_season:
        current_stats = calculator.calculate_team_stats(team, current_season)
        # Only include stats if team has played games
        if current_stats['games_played'] == 0:
            current_stats = None
    
    # Get all seasons this team has played in
    team_seasons = Season.objects.filter(
        Q(games__home_team=team) | Q(games__away_team=team)
    ).distinct().order_by('-starts')
    
    # Calculate historical stats for each season
    historical_stats = []
    total_games = 0
    total_wins = 0
    total_losses = 0
    total_ties = 0
    total_runs_scored = 0
    total_runs_against = 0
    win_percentage_data = []  # For charting
    
    for season in team_seasons:
        season_stats = calculator.calculate_team_stats(team, season)
        if season_stats['games_played'] > 0:
            historical_stats.append(season_stats)
            total_games += season_stats['games_played']
            total_wins += season_stats['wins']
            total_losses += season_stats['losses']
            total_ties += season_stats['ties']
            total_runs_scored += season_stats['runs_scored']
            total_runs_against += season_stats['runs_against']
            
            # Add to chart data
            win_percentage_data.append({
                'season': season.title,
                'percentage': round(season_stats['percentage'] * 100, 1),
                'games': season_stats['games_played']
            })
    
    # Calculate career stats
    career_stats = {
        'games_played': total_games,
        'wins': total_wins,
        'losses': total_losses,
        'ties': total_ties,
        'points': (2 * total_wins) + total_ties,
        'percentage': float(total_wins) / float(total_games) if total_games > 0 else 0.0,
        'runs_scored': total_runs_scored,
        'runs_against': total_runs_against,
        'run_differential': total_runs_scored - total_runs_against,
    }
    
    # Get games grouped by season (show all seasons)
    games_by_season = {}
    for season in team_seasons:  # Show all seasons
        season_games = team.games_played().filter(season=season)
        if season_games:
            games_by_season[season] = season_games
    
    # Get players
    players = team.players.all().order_by('number', 'user__last_name')
    
    context = {
        'team': team,
        'current_stats': current_stats,
        'current_season': current_season,
        'historical_stats': historical_stats,
        'career_stats': career_stats,
        'games_by_season': games_by_season,
        'players': players,
        'win_percentage_data': win_percentage_data,
        'win_percentage_json': json.dumps(win_percentage_data),
    }
    return render(request, 'core/team_detail.html', context)


def news(request):
    """Display news list."""
    news_list = News.objects.all().order_by('-posted_on')
    
    context = {
        'news_list': news_list,
    }
    return render(request, 'core/news.html', context)


def gallery(request):
    """Display photo gallery categories."""
    categories = Category.objects.all().order_by('name')
    
    # Calculate total photo count
    total_photos = sum(category.photos.count() for category in categories)
    
    context = {
        'categories': categories,
        'total_photos': total_photos,
    }
    return render(request, 'core/gallery.html', context)


def gallery_category(request, slug):
    """Display photos in a category."""
    category = get_object_or_404(Category, slug=slug)
    photos = category.photos.all().order_by('-uploaded_at')
    
    context = {
        'category': category,
        'photos': photos,
    }
    return render(request, 'core/gallery_category.html', context)


def rules(request):
    """Display league rules and regulations."""
    return render(request, 'core/rules.html')


def contact(request):
    """Display contact information and form."""
    return render(request, 'core/contact.html')
