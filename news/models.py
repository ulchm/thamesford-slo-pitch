from django.db import models
from django.utils import timezone
from tinymce.models import HTMLField


class News(models.Model):
    posted_on = models.DateTimeField(default=timezone.now)
    subject = models.CharField(max_length=128)
    body = HTMLField()
    display_on_home = models.BooleanField(default=False, help_text="Display this article on the home page")

    class Meta:
        verbose_name_plural = "news"
        ordering = ['-posted_on']

    def __str__(self):
        return self.subject
