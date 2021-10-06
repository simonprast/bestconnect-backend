from django.conf import settings
from django.db import models
from django.template.loader import get_template

from user.models import User


class MailModel(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    to_email = models.CharField(max_length=320, null=True, blank=True)
    from_email = models.CharField(max_length=320, null=True, blank=True)
    template = models.CharField(max_length=255, null=True, blank=True)
    context = models.TextField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.to_email

    def save(self, *args, **kwargs):
        if self.from_email is None:
            self.from_email = settings.DEFAULT_FROM_EMAIL

        template = get_template(self.template)
        self.message = template.render(self.context)

        super(MailModel, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Mail message'
