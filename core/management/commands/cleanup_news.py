import re
from django.core.management.base import BaseCommand
from news.models import News


class Command(BaseCommand):
    help = 'Clean up line break characters in news content'

    def handle(self, *args, **options):
        self.stdout.write('Cleaning up news content...')

        news_articles = News.objects.all()
        updated_count = 0

        for news in news_articles:
            original_body = news.body
            if original_body:
                # Remove \r\n, \r, \n, and \t characters
                cleaned_body = original_body.replace('\\r\\n', '').replace('\\r', '').replace('\\n', '').replace('\\t', '')
                # Also handle actual carriage returns, line feeds, and tabs
                cleaned_body = cleaned_body.replace('\r\n', '').replace('\r', '').replace('\n', '').replace('\t', '')

                if cleaned_body != original_body:
                    news.body = cleaned_body
                    news.save()
                    updated_count += 1
                    self.stdout.write(f'  Cleaned article: {news.subject}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned {updated_count} news articles')
        )