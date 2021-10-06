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
    # If a token already exists, delete it.
    if EmailToken.objects.filter(email_object=email_object).exists():
        EmailToken.objects.get(email_object=email_object).delete()

    # Create a new token. The EmailToken.token is a random number.
    token_object = EmailToken(email_object=email_object, user=user)

    # Check if there is already any other token object with the same email address and token.
    while (EmailToken.objects.filter(email_address=email_object.email_address, token=token_object.token)
           .exclude(email_object=email_object).exists()):
        token_object = None
        token_object = EmailToken(email_object=email_object, user=user)

    token_object.save()

    context = {
        'user': token_object.user,
        'email': quote_plus(str(token_object.email_object.email_address)),
        'token_1': token_object.token[0:3],
        'token_2': token_object.token[3:6]
    }

    send_mail('registration-german.tpl', email_object.email_address, context=context)
