from mail_templated import EmailMessage

from user.models import EmailAddress

from .models import MailModel


# sendMail sends an email and saves it into the database.
def send_mail(template, to_email, from_email=None, context={}):
    if EmailAddress.objects.filter(email_address=to_email, verified=True).exists() and 'user' not in context:
        email_object = EmailAddress.objects.get(email_address=to_email, verified=True)
        user = email_object.user

        context.update({'user': user})
    elif 'user' in context:
        user = context['user']
    else:
        user = None

    message = EmailMessage(
        template,
        context,
        from_email,
        [to_email]
    )

    message.send()

    MailModel.objects.create(
        user=user,
        to_email=to_email,
        from_email=from_email,
        template=template,
        context=context
    )

    return {
        'user': {
            'id': user.id if user else None,
            'username': user.username if user else None,
            'email': str(user.primary_email) if user else None
        },
        'to_email': to_email,
        'from_email': from_email
    }
