from django.conf import settings
from mail_templated import EmailMessage
from user.models import User

from .models import MailModel


# sendMail sends an email and saves it into the database.
def sendMail(template, from_email, to_email):
    if User.objects.filter(email=to_email).exists():
        user = User.objects.get(email=to_email)
    else:
        user = None

    if user is not None:
        context = {'user': user}
    else:
        context = {}

    message = EmailMessage(
        template,
        context,
        from_email,
        [to_email]
    )

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    MailModel.objects.create(
        user=user,
        to_email=to_email,
        from_email=from_email,
        subject=message.subject,
        message=message.body,
    )

    message.send()
