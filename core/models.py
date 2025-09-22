from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from tinymce.models import HTMLField


GAME_TYPE_CHOICES = [
    (1, "Regular Season"),
    (2, "Play-offs"),
    (3, "Pre-Season"),
]

GAME_CANCELLATION_CHOICES = [
    (1, 'Forfeit'),
    (2, 'Weather'),
    (3, 'Other'),
]


class Team(models.Model):
    name = models.CharField(max_length=128)
    biography = HTMLField(null=True, blank=True)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def get_streak(self):
        """Calculate current win/loss streak."""
        streak_count = 0        
        streak_type = "L"
        games = self.games_played()
        
        if not games:
            return "0 -"
            
        first_game = games[0]
        if ((first_game.home_team == self and first_game.home_score > first_game.away_score) or 
            (first_game.away_team == self and first_game.away_score > first_game.home_score)):
            streak_type = "W"
        
        for game in games:
            # Check if won
            if ((game.home_team == self and game.home_score > game.away_score) or 
                (game.away_team == self and game.away_score > game.home_score)) and streak_type == "W":
                streak_count += 1
            # Check if lost
            elif ((game.home_team == self and game.home_score < game.away_score) or 
                  (game.away_team == self and game.away_score < game.home_score)) and streak_type == "L":
                streak_count += 1
            else:
                break
                
        return f"{streak_count} {streak_type}"
        
    def games_played(self):
        """Return completed games for this team, ordered by most recent."""
        return Game.objects.filter(
            Q(home_team=self) | Q(away_team=self)
        ).exclude(home_score__isnull=True).order_by('-starts_at')
    
    def current_season_stats(self):
        """Get stats for current season, creating if needed."""
        current_season = Season.objects.current()
        if current_season:
            stats, created = Stats.objects.get_or_create(
                team=self, 
                season=current_season
            )
            return stats
        return None
    
    def is_active(self):
        """Check if team is active (has games in last 2 seasons)."""
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        # Get seasons from last 2 years
        cutoff_date = timezone.now().date() - timedelta(days=730)
        recent_seasons = Season.objects.filter(starts__gte=cutoff_date)
        
        # Check if team has games in any recent season
        has_recent_games = Game.objects.filter(
            models.Q(home_team=self) | models.Q(away_team=self),
            season__in=recent_seasons
        ).exists()
        
        return has_recent_games
    
    def get_logo_url(self):
        """Get logo URL or return None for placeholder."""
        if self.logo:
            return self.logo.url
        return None


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, related_name="players", on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    hide_contact = models.BooleanField(default=True)
    number = models.IntegerField(null=True, blank=True)
    is_captain = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['number', 'user__last_name']
        
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Location(models.Model):
    name = models.CharField(max_length=128)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name


class SeasonManager(models.Manager):
    def current(self):
        """Return the current season based on start date."""
        try:
            return self.filter(starts__lte=timezone.now().date()).order_by('-starts').first()
        except Exception:
            return None


class Season(models.Model):
    starts = models.DateField(default=timezone.now)
    title = models.CharField(max_length=128)
    objects = SeasonManager()
    
    class Meta:
        ordering = ['-starts']
        
    def __str__(self):
        return self.title


class StatsManager(models.Manager):
    def update_team_stats(self, team, season):
        """Calculate and update team statistics for a season."""
        w, l, t, p, s, a = 0, 0, 0, 0, 0, 0
        stats, created = Stats.objects.get_or_create(team=team, season=season)
        
        # Get all completed games for this team in this season
        home_games = team.home_games.filter(season=season).exclude(home_score__isnull=True)
        away_games = team.away_games.filter(season=season).exclude(home_score__isnull=True)
        games = list(home_games) + list(away_games)
        
        if games:
            for game in games:
                if game.home_score == game.away_score:
                    # Tie
                    t += 1
                    if game.home_team == team:
                        s += game.home_score
                        a += game.away_score
                    else:
                        s += game.away_score
                        a += game.home_score
                elif game.home_score > game.away_score:
                    # Home team won
                    if game.home_team == team:
                        w += 1
                        s += game.home_score
                        a += game.away_score
                    else:
                        l += 1
                        s += game.away_score
                        a += game.home_score
                else:
                    # Away team won
                    if game.home_team == team:
                        l += 1
                        s += game.home_score
                        a += game.away_score
                    else:
                        w += 1
                        s += game.away_score
                        a += game.home_score
                        
        # Calculate points (2 for win, 1 for tie)
        p = (2 * w) + t
        
        # Update stats
        stats.runs_scored = s
        stats.runs_against = a
        stats.points = p
        stats.ties = t
        stats.wins = w
        stats.losses = l
        
        # Calculate winning percentage
        try:
            total_games = stats.games_played()
            if total_games > 0:
                stats.percentage = float(w) / float(total_games)
            else:
                stats.percentage = 0.0
        except ZeroDivisionError:
            stats.percentage = 0.0

        stats.save(update_stats=False)

    def apply_spo_standings(self, season):
        """Apply Slo-Pitch Ontario tie-breaking rules to all teams in season"""
        # First ensure Stats objects exist for all teams that have games in this season
        teams_with_games = set()
        for game in Game.objects.filter(season=season, home_score__isnull=False):
            teams_with_games.add(game.home_team)
            teams_with_games.add(game.away_team)

        for team in teams_with_games:
            stats, created = Stats.objects.get_or_create(team=team, season=season)
            if created:
                self.update_team_stats(team, season)

        stats_list = list(Stats.objects.filter(season=season))

        # Clear previous tie-breaking data
        for stat in stats_list:
            stat.tie_breaker_rank = 0
            stat.tie_breaker_reason = ""
            stat.tie_breaker_symbol = ""
            stat.save(update_stats=False)

        # Sort by basic record first (wins, then points, then percentage)
        stats_list.sort(key=lambda s: (-s.wins, -s.points, -float(s.percentage or 0)))

        final_standings = []
        remaining_teams = stats_list[:]

        while remaining_teams:
            # Find teams tied with the first remaining team
            leader = remaining_teams[0]
            tied_teams = [team for team in remaining_teams
                         if team.wins == leader.wins and team.losses == leader.losses and team.ties == leader.ties]

            if len(tied_teams) == 1:
                # No tie, just add to final standings
                final_standings.append(tied_teams[0])
                remaining_teams.remove(tied_teams[0])
            else:
                # Break the tie
                resolved = self._break_tie(tied_teams, len(final_standings) + 1)
                final_standings.extend(resolved)
                for team in resolved:
                    remaining_teams.remove(team)

        # Update tie_breaker_rank for all teams
        for i, stat in enumerate(final_standings):
            stat.tie_breaker_rank = i + 1
            stat.save(update_stats=False)

        return final_standings

    def _break_tie(self, tied_teams, starting_rank):
        """Break ties using SPO rules"""
        if len(tied_teams) <= 1:
            return tied_teams

        # Two-way tie
        if len(tied_teams) == 2:
            return self._break_two_way_tie(tied_teams, starting_rank)

        # Multi-way tie
        return self._break_multi_way_tie(tied_teams, starting_rank)

    def _break_two_way_tie(self, teams, starting_rank):
        """Break two-way tie using SPO rules"""
        team1, team2 = teams[0], teams[1]

        # 1. Head-to-head record
        h2h_pct1 = team1.head_to_head_percentage(team2.team)
        h2h_pct2 = team2.head_to_head_percentage(team1.team)

        if h2h_pct1 is not None and h2h_pct1 != h2h_pct2:
            if h2h_pct1 > h2h_pct2:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1

            winner.tie_breaker_reason = "Head-to-head record"
            winner.tie_breaker_symbol = "*"
            loser.tie_breaker_reason = "Head-to-head record"
            loser.tie_breaker_symbol = "*"
            return [winner, loser]

        # 2. Run differential (capped)
        diff1 = team1.run_differential_capped()
        diff2 = team2.run_differential_capped()

        if diff1 != diff2:
            if diff1 > diff2:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1

            winner.tie_breaker_reason = "Run differential"
            winner.tie_breaker_symbol = "**"
            loser.tie_breaker_reason = "Run differential"
            loser.tie_breaker_symbol = "**"
            return [winner, loser]

        # 3. Least runs against
        if team1.runs_against != team2.runs_against:
            if team1.runs_against < team2.runs_against:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1

            winner.tie_breaker_reason = "Fewest runs against"
            winner.tie_breaker_symbol = "***"
            loser.tie_breaker_reason = "Fewest runs against"
            loser.tie_breaker_symbol = "***"
            return [winner, loser]

        # 4. Most runs for
        if team1.runs_scored != team2.runs_scored:
            if team1.runs_scored > team2.runs_scored:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1

            winner.tie_breaker_reason = "Most runs scored"
            winner.tie_breaker_symbol = "****"
            loser.tie_breaker_reason = "Most runs scored"
            loser.tie_breaker_symbol = "****"
            return [winner, loser]

        # 5. Coin toss (manual resolution needed)
        team1.tie_breaker_reason = "Requires manual resolution"
        team1.tie_breaker_symbol = "†"
        team2.tie_breaker_reason = "Requires manual resolution"
        team2.tie_breaker_symbol = "†"
        return teams  # Keep original order

    def _break_multi_way_tie(self, teams, starting_rank):
        """Break multi-way tie using SPO rules"""
        # Check if one team beat all others
        for team in teams:
            beat_all_others = True
            for other in teams:
                if team != other:
                    h2h_pct = team.head_to_head_percentage(other.team)
                    if h2h_pct is None or h2h_pct <= 0.5:
                        beat_all_others = False
                        break

            if beat_all_others:
                team.tie_breaker_reason = "Beat all tied teams"
                team.tie_breaker_symbol = "†"
                remaining = [t for t in teams if t != team]

                # Recursively resolve remaining teams
                if len(remaining) > 1:
                    resolved_remaining = self._break_tie(remaining, starting_rank + 1)
                else:
                    resolved_remaining = remaining

                return [team] + resolved_remaining

        # Check if one team lost to all others
        for team in teams:
            lost_to_all_others = True
            for other in teams:
                if team != other:
                    h2h_pct = team.head_to_head_percentage(other.team)
                    if h2h_pct is None or h2h_pct >= 0.5:
                        lost_to_all_others = False
                        break

            if lost_to_all_others:
                team.tie_breaker_reason = "Lost to all tied teams"
                team.tie_breaker_symbol = "†"
                remaining = [t for t in teams if t != team]

                # Recursively resolve remaining teams
                if len(remaining) > 1:
                    resolved_remaining = self._break_tie(remaining, starting_rank)
                else:
                    resolved_remaining = remaining

                return resolved_remaining + [team]

        # No dominant team, use other tie-breakers
        # Sort by run differential, then runs against, then runs for
        teams.sort(key=lambda t: (-t.run_differential_capped(), t.runs_against, -t.runs_scored))

        for team in teams:
            team.tie_breaker_reason = "Multi-team tie resolution"
            team.tie_breaker_symbol = "†"

        return teams


class Stats(models.Model):
    team = models.ForeignKey(Team, related_name='stats', on_delete=models.CASCADE)
    season = models.ForeignKey(Season, related_name='stats', on_delete=models.CASCADE)
    wins = models.IntegerField(default=0, editable=False)
    losses = models.IntegerField(default=0, editable=False)
    ties = models.IntegerField(default=0, editable=False)
    points = models.IntegerField(default=0, editable=False)
    percentage = models.DecimalField(
        max_digits=4, decimal_places=3, default=0, 
        null=True, blank=True, editable=False
    )
    runs_scored = models.IntegerField(default=0, editable=False)
    runs_against = models.IntegerField(default=0, editable=False)
    games_back = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True
    )
    tie_breaker_rank = models.IntegerField(default=0, editable=False)
    tie_breaker_reason = models.CharField(max_length=100, blank=True, editable=False)
    tie_breaker_symbol = models.CharField(max_length=10, blank=True, editable=False)

    objects = StatsManager()

    class Meta:
        unique_together = [["team", "season"]]
        ordering = ['-season__starts', '-points', '-percentage', 'runs_against']
        verbose_name_plural = "stats"

    def __str__(self):
        return f"{self.team.name} - {self.season.title}"

    def games_played(self):
        """Return number of games played by this team in this season."""
        return self.team.games_played().filter(season=self.season).count()

    def save(self, update_stats=True, *args, **kwargs):
        super().save(*args, **kwargs)
        if update_stats:
            Stats.objects.update_team_stats(self.team, self.season)
    
    def run_differential(self):
        """Calculate run differential (runs scored - runs against)."""
        return self.runs_scored - self.runs_against

    def run_differential_capped(self):
        """Calculate run differential with SPO rule: max ±7 per game"""
        total_diff = 0
        games = self.team.games_played().filter(season=self.season)
        for game in games:
            if game.home_team == self.team:
                game_diff = min(7, max(-7, game.home_score - game.away_score))
            else:
                game_diff = min(7, max(-7, game.away_score - game.home_score))
            total_diff += game_diff
        return total_diff

    def head_to_head_record(self, other_team):
        """Get head-to-head record against another team (wins, losses, ties)"""
        w, l, t = 0, 0, 0
        games = Game.objects.filter(
            season=self.season,
            home_score__isnull=False
        ).filter(
            (Q(home_team=self.team) & Q(away_team=other_team)) |
            (Q(home_team=other_team) & Q(away_team=self.team))
        )

        for game in games:
            if game.home_score == game.away_score:
                t += 1
            elif (game.home_team == self.team and game.home_score > game.away_score) or \
                 (game.away_team == self.team and game.away_score > game.home_score):
                w += 1
            else:
                l += 1
        return w, l, t

    def head_to_head_percentage(self, other_team):
        """Calculate head-to-head winning percentage"""
        w, l, t = self.head_to_head_record(other_team)
        total_games = w + l + t
        if total_games == 0:
            return None
        return (w + 0.5 * t) / total_games


class Game(models.Model):
    season = models.ForeignKey(Season, related_name='games', on_delete=models.CASCADE)
    location = models.ForeignKey(Location, related_name='games', on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, related_name="home_games", on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name="away_games", on_delete=models.CASCADE)
    starts_at = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True, default=None)
    away_score = models.IntegerField(null=True, blank=True, default=None)
    cancellation = models.IntegerField(
        choices=GAME_CANCELLATION_CHOICES, null=True, blank=True
    )
    
    class Meta:
        ordering = ['-starts_at']
        indexes = [
            models.Index(fields=['season', 'home_team']),
            models.Index(fields=['season', 'away_team']),
            models.Index(fields=['home_score', 'away_score']),
            models.Index(fields=['starts_at']),
        ]
        
    def __str__(self):
        return f"{self.starts_at.strftime('%Y-%m-%d %H:%M')} {self.away_team} @ {self.home_team}"
    
    def winner(self):
        """Return winner indicator: 'H' for home, 'A' for away, 'T' for tie, None if not played."""
        if self.home_score is None or self.away_score is None:
            return None
        elif self.home_score > self.away_score:
            return "H"
        elif self.home_score < self.away_score:
            return "A"
        else:
            return "T"
    
    def is_completed(self):
        """Check if game has been completed (scores entered)."""
        return self.home_score is not None and self.away_score is not None
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Note: Stats are now calculated in real-time, no need to update stored stats
        
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Note: Stats are now calculated in real-time, no need to update stored stats


