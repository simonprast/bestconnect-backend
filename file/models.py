from django.db import models
from django.template.defaultfilters import slugify

from user.models import User

from .storage import create_file_path, UserDataFileStorage


class Document(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=create_file_path, storage=UserDataFileStorage(), max_length=255)
    owner = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id and self.title:
            self.slug = slugify(self.title)

        return super(Document, self).save(*args, **kwargs)


# TODO: Remove files when the corresponding object is deleted
