from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def last_updated(self):
        """Return the upload date of the most recent photo in this category."""
        try:
            photo = self.photos.latest('uploaded_at')
            return photo.uploaded_at
        except Photo.DoesNotExist:
            return None


class Photo(models.Model):
    title = models.CharField(max_length=128)
    description = models.TextField()
    image = models.ImageField(upload_to="photos/")
    uploaded_at = models.DateTimeField(default=timezone.now)
    category = models.ForeignKey(Category, related_name="photos", on_delete=models.CASCADE)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title
