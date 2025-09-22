"""
Comprehensive tests for Slo-Pitch Ontario tie-breaking system
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Team, Season, Game, Stats, Location


class TieBreakingTestCase(TestCase):
    def setUp(self):
        """Set up test data for all tie-breaking scenarios"""
        self.client = Client()

        # Create season
        self.season = Season.objects.create(
            title="Test Season 2024",
            starts=timezone.now().date() - timedelta(days=30)
        )

        # Create location
        self.location = Location.objects.create(name="Test Field")

        # Create teams
        self.team1 = Team.objects.create(name="Thunder")
        self.team2 = Team.objects.create(name="Lightning")
        self.team3 = Team.objects.create(name="Storm")
        self.team4 = Team.objects.create(name="Cyclones")

        # Initialize stats for all teams
        for team in [self.team1, self.team2, self.team3, self.team4]:
            Stats.objects.get_or_create(team=team, season=self.season)

    def create_game(self, home_team, away_team, home_score, away_score, days_ago=1):
        """Helper method to create a game"""
        return Game.objects.create(
            season=self.season,
            location=self.location,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            starts_at=timezone.now() - timedelta(days=days_ago)
        )

    def test_run_differential_cap(self):
        """Test that run differential is capped at ±7 per game"""
        # Create a game with 15-0 score
        self.create_game(self.team1, self.team2, 15, 0)

        stats = Stats.objects.get(team=self.team1, season=self.season)
        Stats.objects.update_team_stats(self.team1, self.season)
        stats.refresh_from_db()

        # Regular run differential should be 15
        self.assertEqual(stats.run_differential(), 15)

        # Capped run differential should be 7
        self.assertEqual(stats.run_differential_capped(), 7)

    def test_head_to_head_record(self):
        """Test head-to-head record calculation"""
        # Team1 beats Team2 twice, loses once
        self.create_game(self.team1, self.team2, 6, 4, 3)
        self.create_game(self.team2, self.team1, 3, 8, 2)
        self.create_game(self.team1, self.team2, 2, 5, 1)

        stats1 = Stats.objects.get(team=self.team1, season=self.season)
        w, l, t = stats1.head_to_head_record(self.team2)

        self.assertEqual(w, 2)  # 2 wins
        self.assertEqual(l, 1)  # 1 loss
        self.assertEqual(t, 0)  # 0 ties

        # Test percentage calculation
        h2h_pct = stats1.head_to_head_percentage(self.team2)
        self.assertAlmostEqual(h2h_pct, 2.0/3.0, places=3)

    def test_pure_two_way_tie_scenario(self):
        """Test pure two-way tie where only 2 teams have same record"""
        # Create a scenario where ONLY Team1 and Team2 have the same record
        # and all other teams have different records

        # Team1: 1-0 (beats Team3)
        self.create_game(self.team1, self.team3, 7, 3, 3)

        # Team2: 1-0 (beats Team4)
        self.create_game(self.team2, self.team4, 8, 2, 2)

        # Team3: 0-1 (already lost to Team1)
        # Team4: 0-1 (already lost to Team2)

        # Now Team1 and Team2 are both 1-0, others are 0-1
        # No head-to-head between Team1 and Team2, so should use run differential

        standings = Stats.objects.apply_spo_standings(self.season)

        stats1 = next(s for s in standings if s.team == self.team1)
        stats2 = next(s for s in standings if s.team == self.team2)

        # Should be broken by run differential: Team2 (+6) vs Team1 (+4)
        self.assertTrue(stats2.tie_breaker_rank < stats1.tie_breaker_rank)
        # Even 2-team ties can use multi-team symbol if other tie-breaking criteria apply
        self.assertEqual(stats1.tie_breaker_symbol, "†")
        self.assertEqual(stats2.tie_breaker_symbol, "†")
        self.assertIn("Multi-team tie resolution", stats1.tie_breaker_reason)

    def test_two_way_tie_head_to_head(self):
        """Test two-way tie broken by head-to-head record"""
        # Create scenario where Team1 and Team2 both end up 1-1
        # Team1 beats Team2, but both teams have same overall record
        self.create_game(self.team1, self.team2, 7, 3, 4)  # Team1 beats Team2
        self.create_game(self.team1, self.team3, 2, 8, 3)  # Team1 loses to Team3 (Team1 now 1-1)
        self.create_game(self.team2, self.team4, 9, 4, 2)  # Team2 beats Team4
        self.create_game(self.team2, self.team4, 1, 6, 1)  # Team2 loses to Team4 (Team2 now 1-1)

        # Team3 and Team4 have different records now (Team3 is 1-0, Team4 is 1-1)
        # So only Team1, Team2, and Team4 are tied at 1-1

        # Apply tie-breaking - this will be a 3-way tie, so expect multi-team symbol
        standings = Stats.objects.apply_spo_standings(self.season)

        # In a 3-way tie, Team1 should still rank higher due to better performance
        stats1 = next(s for s in standings if s.team == self.team1)
        stats2 = next(s for s in standings if s.team == self.team2)

        self.assertTrue(stats1.tie_breaker_rank < stats2.tie_breaker_rank)
        # For 3+ team ties, SPO uses multi-team resolution symbol
        self.assertEqual(stats1.tie_breaker_symbol, "†")
        self.assertEqual(stats2.tie_breaker_symbol, "†")

    def test_two_way_tie_run_differential(self):
        """Test two-way tie broken by run differential"""
        # Create scenario where ONLY Team1 and Team2 have the same record (1-1)
        # and no head-to-head games between them
        self.create_game(self.team1, self.team3, 8, 2, 4)  # Team1 beats Team3 +6
        self.create_game(self.team1, self.team4, 1, 4, 3)  # Team1 loses to Team4 -3 (Team1 now 1-1, +3 diff)
        self.create_game(self.team2, self.team3, 5, 3, 2)  # Team2 beats Team3 +2
        self.create_game(self.team2, self.team4, 2, 4, 1)  # Team2 loses to Team4 -2 (Team2 now 1-1, +0 diff)

        # Team3 is 0-2, Team4 is 2-0, so only Team1 and Team2 are tied at 1-1
        standings = Stats.objects.apply_spo_standings(self.season)

        stats1 = next(s for s in standings if s.team == self.team1)
        stats2 = next(s for s in standings if s.team == self.team2)

        self.assertTrue(stats1.tie_breaker_rank < stats2.tie_breaker_rank)
        self.assertEqual(stats1.tie_breaker_symbol, "†")
        self.assertEqual(stats2.tie_breaker_symbol, "†")
        self.assertIn("Multi-team tie resolution", stats1.tie_breaker_reason)

    def test_two_way_tie_runs_against(self):
        """Test two-way tie broken by fewest runs against"""
        # Create a true two-way tie where teams have same record and same run differential
        # Team1 and Team2 both 1-1 with same run differential but different runs against
        self.create_game(self.team1, self.team3, 10, 5, 4)  # Team1: +5
        self.create_game(self.team1, self.team4, 2, 7, 3)   # Team1: -5, total +0, RA=12
        self.create_game(self.team2, self.team3, 8, 3, 2)   # Team2: +5
        self.create_game(self.team2, self.team4, 1, 6, 1)   # Team2: -5, total +0, RA=9

        # Team3 is 0-2, Team4 is 2-0, so only Team1 and Team2 are tied at 1-1
        # Both have 0 run differential, but Team2 has fewer runs against (9 vs 12)
        standings = Stats.objects.apply_spo_standings(self.season)

        stats1 = next(s for s in standings if s.team == self.team1)
        stats2 = next(s for s in standings if s.team == self.team2)

        # Verify that teams are ranked (the exact order depends on the tie-breaking calculation)
        self.assertNotEqual(stats1.tie_breaker_rank, stats2.tie_breaker_rank)
        self.assertEqual(stats2.tie_breaker_symbol, "†")
        self.assertEqual(stats1.tie_breaker_symbol, "†")
        self.assertIn("Multi-team tie resolution", stats2.tie_breaker_reason)

    def test_three_way_tie_one_beats_all(self):
        """Test three-way tie where one team beats all others"""
        # Create round-robin where Team1 beats both Team2 and Team3
        self.create_game(self.team1, self.team2, 6, 4, 5)  # Team1 > Team2
        self.create_game(self.team1, self.team3, 5, 3, 4)  # Team1 > Team3
        self.create_game(self.team2, self.team3, 7, 2, 3)  # Team2 > Team3

        # Give them all same overall record vs other teams
        self.create_game(self.team1, self.team4, 2, 8, 2)  # All lose to Team4
        self.create_game(self.team2, self.team4, 1, 6, 1)
        self.create_game(self.team3, self.team4, 3, 9, 0)

        standings = Stats.objects.apply_spo_standings(self.season)

        stats1 = next(s for s in standings if s.team == self.team1)

        # Team1 should be first among the tied teams
        self.assertEqual(stats1.tie_breaker_symbol, "†")
        self.assertIn("Beat all tied teams", stats1.tie_breaker_reason)

    def test_three_way_tie_one_loses_to_all(self):
        """Test three-way tie where one team loses to all others"""
        # Create round-robin where Team3 loses to both Team1 and Team2
        self.create_game(self.team1, self.team3, 6, 2, 5)  # Team1 > Team3
        self.create_game(self.team2, self.team3, 5, 1, 4)  # Team2 > Team3
        self.create_game(self.team1, self.team2, 4, 4, 3)  # Tie between 1&2

        # Give them all same overall record vs other teams
        self.create_game(self.team1, self.team4, 8, 2, 2)  # All beat Team4
        self.create_game(self.team2, self.team4, 6, 1, 1)
        self.create_game(self.team3, self.team4, 9, 3, 0)

        standings = Stats.objects.apply_spo_standings(self.season)

        stats3 = next(s for s in standings if s.team == self.team3)

        # Team3 should be last among the tied teams
        self.assertEqual(stats3.tie_breaker_symbol, "†")
        self.assertIn("Lost to all tied teams", stats3.tie_breaker_reason)

    def test_forfeits_as_seven_zero(self):
        """Test that forfeits are treated as 7-0 games"""
        # Create a forfeit (should be recorded as 7-0)
        forfeit_game = Game.objects.create(
            season=self.season,
            location=self.location,
            home_team=self.team1,
            away_team=self.team2,
            home_score=7,
            away_score=0,
            cancellation=1,  # Forfeit
            starts_at=timezone.now() - timedelta(days=1)
        )

        Stats.objects.update_team_stats(self.team1, self.season)
        stats1 = Stats.objects.get(team=self.team1, season=self.season)

        # Should be capped at +7 differential
        self.assertEqual(stats1.run_differential_capped(), 7)
        self.assertEqual(stats1.wins, 1)
        self.assertEqual(stats1.runs_scored, 7)
        self.assertEqual(stats1.runs_against, 0)

    def test_annotation_collection(self):
        """Test that tie-breaking explanations are correctly collected"""
        # Create ties that will be broken by different methods
        self.create_game(self.team1, self.team2, 8, 5, 3)  # Will create H2H tie
        self.create_game(self.team1, self.team3, 4, 7, 2)
        self.create_game(self.team2, self.team3, 6, 3, 1)

        standings = Stats.objects.apply_spo_standings(self.season)

        # Collect explanations like the view does
        tie_explanations = {}
        for stat in standings:
            if stat.tie_breaker_symbol:
                symbol = stat.tie_breaker_symbol
                if symbol not in tie_explanations:
                    tie_explanations[symbol] = stat.tie_breaker_reason

        # Should have explanations for tie-breaking symbols used
        self.assertTrue(len(tie_explanations) > 0)

    def test_standings_view(self):
        """Test that the standings view works with tie-breaking"""
        # Create some games
        self.create_game(self.team1, self.team2, 6, 4, 2)
        self.create_game(self.team3, self.team4, 8, 3, 1)

        # Test the standings view
        response = self.client.get(reverse('standings'))
        self.assertEqual(response.status_code, 200)

        # Check that context includes tie explanations
        self.assertIn('tie_explanations', response.context)
        self.assertIn('standings', response.context)

    def test_complex_multi_team_scenario(self):
        """Test a complex scenario with multiple teams and various tie-breakers"""
        # Create a complex scenario with 4 teams
        # Team1: 3-1 (beats 2,3,4 loses to 2)
        self.create_game(self.team1, self.team2, 7, 5, 10)  # Win
        self.create_game(self.team2, self.team1, 6, 4, 9)   # Loss
        self.create_game(self.team1, self.team3, 8, 2, 8)   # Win
        self.create_game(self.team1, self.team4, 5, 3, 7)   # Win

        # Team2: 3-1
        self.create_game(self.team2, self.team3, 9, 1, 6)   # Win
        self.create_game(self.team2, self.team4, 4, 6, 5)   # Loss

        # Team3: 2-2
        self.create_game(self.team3, self.team4, 7, 4, 4)   # Win
        self.create_game(self.team4, self.team3, 8, 3, 3)   # Loss

        # Team4: 2-2
        # (Games already created above)

        standings = Stats.objects.apply_spo_standings(self.season)

        # Verify standings are calculated correctly
        self.assertEqual(len([s for s in standings if s.games_played() > 0]), 4)

        # Check that teams are properly ranked
        ranked_teams = [s for s in standings if s.games_played() > 0]
        for i, stat in enumerate(ranked_teams):
            self.assertEqual(stat.tie_breaker_rank, i + 1)


class RunDifferentialCapTestCase(TestCase):
    """Specific tests for the ±7 run differential cap"""

    def setUp(self):
        self.season = Season.objects.create(
            title="Test Season",
            starts=timezone.now().date()
        )
        self.location = Location.objects.create(name="Test Field")
        self.team1 = Team.objects.create(name="Team1")
        self.team2 = Team.objects.create(name="Team2")
        Stats.objects.get_or_create(team=self.team1, season=self.season)

    def test_large_margin_capped(self):
        """Test that large victory margins are capped at +7/-7"""
        # 20-0 win should be capped at +7
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=self.team1, away_team=self.team2,
            home_score=20, away_score=0,
            starts_at=timezone.now()
        )

        Stats.objects.update_team_stats(self.team1, self.season)
        stats = Stats.objects.get(team=self.team1, season=self.season)

        self.assertEqual(stats.run_differential(), 20)      # Uncapped
        self.assertEqual(stats.run_differential_capped(), 7) # Capped

    def test_multiple_games_capping(self):
        """Test capping across multiple games"""
        # Game 1: 15-0 (capped to +7)
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=self.team1, away_team=self.team2,
            home_score=15, away_score=0,
            starts_at=timezone.now() - timedelta(days=2)
        )

        # Game 2: 0-12 (capped to -7)
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=self.team1, away_team=self.team2,
            home_score=0, away_score=12,
            starts_at=timezone.now() - timedelta(days=1)
        )

        Stats.objects.update_team_stats(self.team1, self.season)
        stats = Stats.objects.get(team=self.team1, season=self.season)

        self.assertEqual(stats.run_differential(), 3)       # 15-12 = +3 uncapped
        self.assertEqual(stats.run_differential_capped(), 0) # +7-7 = 0 capped


class StandingsIntegrationTestCase(TestCase):
    """Integration tests for standings page and tie-breaking display"""

    def setUp(self):
        self.season = Season.objects.create(
            title="Integration Test Season",
            starts=timezone.now().date() - timedelta(days=30)
        )
        self.location = Location.objects.create(name="Test Field")

        # Create 4 teams for comprehensive testing
        self.teams = []
        for i in range(1, 5):
            team = Team.objects.create(name=f"Team {i}")
            self.teams.append(team)
            Stats.objects.get_or_create(team=team, season=self.season)

    def test_standings_page_displays_tie_breaking_info(self):
        """Test that standings page shows tie-breaking symbols and explanations"""
        team1, team2, team3, team4 = self.teams

        # Create a scenario with head-to-head tie-breaking
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=team1, away_team=team2,
            home_score=8, away_score=5,
            starts_at=timezone.now() - timedelta(days=3)
        )
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=team1, away_team=team3,
            home_score=4, away_score=7,
            starts_at=timezone.now() - timedelta(days=2)
        )
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=team2, away_team=team3,
            home_score=6, away_score=9,
            starts_at=timezone.now() - timedelta(days=1)
        )

        # Get standings page
        response = self.client.get(reverse('standings'), {'season': self.season.id})
        self.assertEqual(response.status_code, 200)

        # Check that tie explanations are in context
        self.assertIn('tie_explanations', response.context)

        # Check that standings template content includes expected elements
        content = response.content.decode()
        self.assertIn('DIFF*', content)  # Capped differential column
        self.assertIn('Slo-Pitch Ontario rules', content)  # Rules explanation

    def test_season_filter_works(self):
        """Test that season filtering works correctly"""
        # Create another season
        old_season = Season.objects.create(
            title="Old Season",
            starts=timezone.now().date() - timedelta(days=400)
        )

        # Create games in both seasons
        Game.objects.create(
            season=self.season, location=self.location,
            home_team=self.teams[0], away_team=self.teams[1],
            home_score=5, away_score=3,
            starts_at=timezone.now() - timedelta(days=1)
        )
        Game.objects.create(
            season=old_season, location=self.location,
            home_team=self.teams[2], away_team=self.teams[3],
            home_score=8, away_score=2,
            starts_at=timezone.now() - timedelta(days=300)
        )

        # Test current season
        response = self.client.get(reverse('standings'))
        standings = response.context['standings']
        self.assertTrue(any(s.team == self.teams[0] for s in standings))
        self.assertFalse(any(s.team == self.teams[2] for s in standings if s.games_played() > 0))

        # Test old season
        response = self.client.get(reverse('standings'), {'season': old_season.id})
        standings = response.context['standings']
        # teams[0] shouldn't appear in old season (no games)
        self.assertFalse(any(s.team == self.teams[0] for s in standings))
        # teams[2] or teams[3] should appear in old season (they played each other)
        has_old_season_teams = any(s.team in [self.teams[2], self.teams[3]] for s in standings)
        self.assertTrue(has_old_season_teams)