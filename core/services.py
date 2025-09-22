from django.db.models import Q
from .models import Game


class StatsCalculator:
    """Service class for calculating team statistics in real-time."""
    
    def __init__(self):
        self._cache = {}
    
    def calculate_team_stats(self, team, season):
        """Calculate statistics for a team in a given season."""
        cache_key = f"{team.id}_{season.id if season else 'all'}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get all completed games for this team in this season
        games_filter = Q(home_team=team) | Q(away_team=team)
        games_filter &= Q(home_score__isnull=False, away_score__isnull=False)
        
        if season:
            games_filter &= Q(season=season)
        
        games = Game.objects.filter(games_filter).select_related('home_team', 'away_team')
        
        # Initialize stats
        wins = losses = ties = 0
        runs_scored = runs_against = 0
        
        for game in games:
            is_home = game.home_team == team
            team_score = game.home_score if is_home else game.away_score
            opponent_score = game.away_score if is_home else game.home_score
            
            runs_scored += team_score
            runs_against += opponent_score
            
            if team_score > opponent_score:
                wins += 1
            elif team_score < opponent_score:
                losses += 1
            else:
                ties += 1
        
        # Calculate derived stats
        games_played = wins + losses + ties
        points = (2 * wins) + ties
        percentage = float(wins) / float(games_played) if games_played > 0 else 0.0
        run_differential = runs_scored - runs_against
        
        stats = {
            'team': team,
            'season': season,
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'games_played': games_played,
            'points': points,
            'percentage': percentage,
            'runs_scored': runs_scored,
            'runs_against': runs_against,
            'run_differential': run_differential,
        }
        
        self._cache[cache_key] = stats
        return stats
    
    def calculate_all_team_stats(self, season):
        """Calculate statistics for all teams in a season."""
        from .models import Team
        
        teams = Team.objects.all().order_by('name')
        all_stats = []
        
        for team in teams:
            stats = self.calculate_team_stats(team, season)
            if stats['games_played'] > 0:  # Only include teams that have played games
                all_stats.append(stats)
        
        # Sort by points (desc), then percentage (desc), then runs_against (asc)
        all_stats.sort(
            key=lambda x: (-x['points'], -x['percentage'], x['runs_against'])
        )
        
        return all_stats