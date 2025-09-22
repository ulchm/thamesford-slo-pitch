# Thamesford Slo-Pitch League

A Django-based website for managing the Thamesford Slo-Pitch League. This application provides comprehensive league management tools including team roster management, game scheduling, standings calculation with official Slo-Pitch Ontario (SPO) tie-breaking rules, photo galleries, and news updates.

## Features

### Core League Management
- **Team Management**: Team profiles with logos, rosters, and player contact information
- **Game Scheduling**: Complete game scheduling system with locations and times
- **Standings**: Real-time standings calculation with SPO-compliant tie-breaking rules
- **Statistics**: Comprehensive team and player statistics tracking
- **Performance Optimization**: Database indexes and query optimization for fast loading

### Content Management
- **Photo Gallery**: Organized photo galleries with categories for league events
- **News System**: News articles with rich text editing and home page display options
- **Admin Interface**: Full Django admin interface for easy content management

### SPO Compliance
- Implements official Slo-Pitch Ontario tie-breaking rules:
  - Head-to-head record
  - Run differential (capped at ±7 per game)
  - Fewest runs against
  - Most runs scored
  - Manual resolution for remaining ties

## Technology Stack

- **Backend**: Django 5.2.6
- **Database**: SQLite3 (easily configurable for PostgreSQL/MySQL)
- **Frontend**: Bootstrap 5 with custom CSS
- **Rich Text**: TinyMCE integration
- **Python**: 3.12+

## Project Structure

```
├── core/           # Main league functionality (teams, games, standings)
├── gallery/        # Photo gallery system
├── news/           # News and announcements
├── slopitch/       # Django project settings
├── static/         # CSS, images, and static files
├── templates/      # HTML templates
├── media/          # User-uploaded files (photos, team logos)
└── manage.py       # Django management script
```

## Installation

### Prerequisites
- Python 3.12+
- pip

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd thamesfordslopitch
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install django pillow django-tinymce
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Website: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Configuration

### Database
The project uses SQLite3 by default. To use PostgreSQL or MySQL, update the `DATABASES` setting in `slopitch/settings.py`.

### Media Files
Uploaded files (photos, team logos) are stored in the `media/` directory. In production, configure proper media file serving.

### Static Files
Static files are served from the `static/` directory. Run `python manage.py collectstatic` for production deployment.

## Usage

### Managing Teams
1. Access the admin interface at `/admin/`
2. Add teams under "Core" → "Teams"
3. Add players and assign them to teams
4. Upload team logos through the team admin interface

### Scheduling Games
1. Create seasons under "Core" → "Seasons"
2. Add locations under "Core" → "Locations"
3. Schedule games under "Core" → "Games"
4. Enter scores when games are completed

### Managing Content
- **Photos**: Use "Gallery" → "Categories" and "Photos" to organize league photos
- **News**: Use "News" → "News" to create announcements and articles

### Viewing Statistics
- Team standings are automatically calculated and displayed at `/standings/`
- Individual team statistics are available at `/teams/<team_id>/`
- Historical statistics are maintained across seasons

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Performance Testing
A performance test script is included:
```bash
python test_stats_performance.py
```

## Data Migration

The project includes a management command for importing data from PostgreSQL dumps:

```bash
python manage.py import_data path/to/dump.sql
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

For questions or issues, please open an issue on GitHub or contact the league administrators.