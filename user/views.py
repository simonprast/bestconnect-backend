from django.core import exceptions

from urllib.parse import quote_plus

from mailing.views import send_mail

from .models import EmailAddress, EmailToken


def get_token_object(token):
    if EmailToken.objects.filter(token=token).exists():
        return EmailToken.objects.get(token=token)
    else:
        raise exceptions.ObjectDoesNotExist


def get_email_object(user, email_address):
    if EmailAddress.objects.filter(user=user, email_address=email_address).exists():
        return EmailAddress.objects.get(user=user, email_address=email_address)
    else:
        raise exceptions.ObjectDoesNotExist


def initialize_verification_process(user, email_object):
    token_object = EmailToken(email_address=email_object, user=user)
    token_object.save()

    context = {
        'user': token_object.user,
        'email': quote_plus(str(token_object.user.primary_email)),
        'token_1': token_object.token[0:3],
        'token_2': token_object.token[3:6]
    }

    mail_data = send_mail('registration-german.tpl', email_object.email_address, context=context)

    return mail_data


def handle_verify(email_address, token):
    token_object = get_token_object(token)
    user = token_object.user
    email_object = get_email_object(user, email_address)

    if token_object.email_address == email_object:
        EmailAddress.objects.verify(email_object)
        token_object.delete()
        return email_object
    else:
        return None
