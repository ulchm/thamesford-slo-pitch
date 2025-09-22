#!/usr/bin/env python
import os
import sys
import django
import time

# Add the project directory to the Python path
sys.path.append('/home/mike/Code/thamesfordslopitch')

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'slopitch.settings')
django.setup()

from core.services import StatsCalculator
from core.models import Season

if __name__ == '__main__':
    # Test with multiple seasons
    seasons = Season.objects.all()[:3]  # Test with first 3 seasons
    calculator = StatsCalculator()

    for season in seasons:
        start_time = time.time()
        stats = calculator.calculate_all_team_stats(season)
        end_time = time.time()

        print(f'\n=== {season.title} ===')
        print(f'Calculated stats for {len(stats)} teams in {(end_time - start_time)*1000:.1f}ms')
        
        if stats:
            print(f'Top 3 teams:')
            for i, team_stats in enumerate(stats[:3]):
                print(f'  {i+1}. {team_stats["team"].name}: {team_stats["wins"]}-{team_stats["losses"]}-{team_stats["ties"]} ({team_stats["points"]} pts, {team_stats["percentage"]:.3f})')
        else:
            print('  No teams with games played')
    
    # Test a season with lots of games
    print(f'\n=== Performance Test with Busy Season ===')
    busy_season = Season.objects.filter(stats__isnull=False).first()
    if busy_season:
        start_time = time.time()
        stats = calculator.calculate_all_team_stats(busy_season)
        end_time = time.time()
        print(f'Calculated stats for {len(stats)} teams in {(end_time - start_time)*1000:.1f}ms')
    else:
        print('No seasons with stats found')