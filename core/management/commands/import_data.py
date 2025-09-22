import re
import sqlite3
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Team, Player, Location, Season, Game, Stats
from gallery.models import Category, Photo
from news.models import News


class Command(BaseCommand):
    help = 'Import data from PostgreSQL dump file'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Path to the PostgreSQL dump file')

    def handle(self, *args, **options):
        sql_file = options['sql_file']
        
        self.stdout.write('Reading SQL dump file...')
        
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
            return

        # Extract COPY data sections
        lines = content.split('\n')
        data = {}
        current_table = None
        current_data = []
        
        for line in lines:
            # Check for COPY command
            copy_match = re.match(r'COPY (\w+) \([^)]+\) FROM stdin;', line)
            if copy_match:
                # Save previous table data if exists
                if current_table and current_data:
                    data[current_table] = current_data
                
                current_table = copy_match.group(1)
                current_data = []
                continue
            
            # Check for end of data marker
            if line == '\\.':
                if current_table and current_data:
                    data[current_table] = current_data
                current_table = None
                current_data = []
                continue
            
            # If we're in a COPY section, collect the data
            if current_table is not None and line.strip():
                # Split by tabs and handle NULL values
                row = [None if col == '\\N' else col for col in line.split('\t')]
                current_data.append(row)
            
        self.stdout.write(f'Found data for {len(data)} tables')
        
        # Import data in correct order (respecting foreign keys)
        try:
            self.import_users(data.get('auth_user', []))
            self.import_locations(data.get('core_location', []))
            self.import_seasons(data.get('core_season', []))
            self.import_teams(data.get('core_team', []))
            self.import_players(data.get('core_player', []))
            self.import_games(data.get('core_game', []))
            self.import_categories(data.get('core_category', []))
            self.import_photos(data.get('core_photo', []))
            self.import_news(data.get('core_news', []))
            
            self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during import: {e}'))

    def import_users(self, rows):
        self.stdout.write('Importing users...')
        for row in rows:
            try:
                user_id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined = row
                
                # Convert string booleans
                is_staff = is_staff == 't'
                is_active = is_active == 't'
                is_superuser = is_superuser == 't'
                
                # Parse dates
                date_joined = datetime.fromisoformat(date_joined.replace('Z', '+00:00')) if date_joined else timezone.now()
                last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00')) if last_login else None
                
                user, created = User.objects.get_or_create(
                    id=int(user_id),
                    defaults={
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'password': password,
                        'is_staff': is_staff,
                        'is_active': is_active,
                        'is_superuser': is_superuser,
                        'last_login': last_login,
                        'date_joined': date_joined,
                    }
                )
                if created:
                    self.stdout.write(f'  Created user: {username}')
            except Exception as e:
                self.stdout.write(f'  Error importing user {row}: {e}')

    def import_locations(self, rows):
        self.stdout.write('Importing locations...')
        for row in rows:
            try:
                location_id, name = row
                location, created = Location.objects.get_or_create(
                    id=int(location_id),
                    defaults={'name': name}
                )
                if created:
                    self.stdout.write(f'  Created location: {name}')
            except Exception as e:
                self.stdout.write(f'  Error importing location {row}: {e}')

    def import_seasons(self, rows):
        self.stdout.write('Importing seasons...')
        for row in rows:
            try:
                season_id, starts, title = row
                starts_date = datetime.fromisoformat(starts).date() if starts else timezone.now().date()
                
                season, created = Season.objects.get_or_create(
                    id=int(season_id),
                    defaults={
                        'starts': starts_date,
                        'title': title
                    }
                )
                if created:
                    self.stdout.write(f'  Created season: {title}')
            except Exception as e:
                self.stdout.write(f'  Error importing season {row}: {e}')

    def import_teams(self, rows):
        self.stdout.write('Importing teams...')
        for row in rows:
            try:
                team_id, name, biography = row
                team, created = Team.objects.get_or_create(
                    id=int(team_id),
                    defaults={
                        'name': name,
                        'biography': biography
                    }
                )
                if created:
                    self.stdout.write(f'  Created team: {name}')
            except Exception as e:
                self.stdout.write(f'  Error importing team {row}: {e}')

    def import_players(self, rows):
        self.stdout.write('Importing players...')
        for row in rows:
            try:
                player_id, user_id, team_id, phone_number, hide_contact, number, is_captain = row
                
                user = User.objects.get(id=int(user_id))
                team = Team.objects.get(id=int(team_id))
                
                hide_contact = hide_contact == 't' if hide_contact else True
                is_captain = is_captain == 't' if is_captain else False
                number = int(number) if number else None
                
                player, created = Player.objects.get_or_create(
                    id=int(player_id),
                    defaults={
                        'user': user,
                        'team': team,
                        'phone_number': phone_number,
                        'hide_contact': hide_contact,
                        'number': number,
                        'is_captain': is_captain
                    }
                )
                if created:
                    self.stdout.write(f'  Created player: {user.first_name} {user.last_name}')
            except Exception as e:
                self.stdout.write(f'  Error importing player {row}: {e}')

    def import_games(self, rows):
        self.stdout.write('Importing games...')
        for row in rows:
            try:
                game_id, season_id, location_id, home_team_id, away_team_id, starts_at, home_score, away_score, cancellation = row
                
                season = Season.objects.get(id=int(season_id))
                location = Location.objects.get(id=int(location_id))
                home_team = Team.objects.get(id=int(home_team_id))
                away_team = Team.objects.get(id=int(away_team_id))
                
                starts_at = datetime.fromisoformat(starts_at.replace('Z', '+00:00')) if starts_at else timezone.now()
                home_score = int(home_score) if home_score else None
                away_score = int(away_score) if away_score else None
                cancellation = int(cancellation) if cancellation else None
                
                game, created = Game.objects.get_or_create(
                    id=int(game_id),
                    defaults={
                        'season': season,
                        'location': location,
                        'home_team': home_team,
                        'away_team': away_team,
                        'starts_at': starts_at,
                        'home_score': home_score,
                        'away_score': away_score,
                        'cancellation': cancellation
                    }
                )
                if created:
                    self.stdout.write(f'  Created game: {away_team} @ {home_team}')
            except Exception as e:
                self.stdout.write(f'  Error importing game {row}: {e}')

    def import_categories(self, rows):
        self.stdout.write('Importing categories...')
        for row in rows:
            try:
                category_id, name, slug = row
                category, created = Category.objects.get_or_create(
                    id=int(category_id),
                    defaults={
                        'name': name,
                        'slug': slug
                    }
                )
                if created:
                    self.stdout.write(f'  Created category: {name}')
            except Exception as e:
                self.stdout.write(f'  Error importing category {row}: {e}')

    def import_photos(self, rows):
        self.stdout.write('Importing photos...')
        for row in rows:
            try:
                photo_id, title, description, image, uploaded_at, category_id = row
                
                category = Category.objects.get(id=int(category_id))
                uploaded_at = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00')) if uploaded_at else timezone.now()
                
                photo, created = Photo.objects.get_or_create(
                    id=int(photo_id),
                    defaults={
                        'title': title,
                        'description': description,
                        'image': image,  # Note: This will need manual file migration
                        'uploaded_at': uploaded_at,
                        'category': category
                    }
                )
                if created:
                    self.stdout.write(f'  Created photo: {title}')
            except Exception as e:
                self.stdout.write(f'  Error importing photo {row}: {e}')

    def import_news(self, rows):
        self.stdout.write('Importing news...')
        for row in rows:
            try:
                news_id, posted_on, subject, body = row
                
                posted_on = datetime.fromisoformat(posted_on.replace('Z', '+00:00')) if posted_on else timezone.now()
                
                news, created = News.objects.get_or_create(
                    id=int(news_id),
                    defaults={
                        'posted_on': posted_on,
                        'subject': subject,
                        'body': body
                    }
                )
                if created:
                    self.stdout.write(f'  Created news: {subject}')
            except Exception as e:
                self.stdout.write(f'  Error importing news {row}: {e}')