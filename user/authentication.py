from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import EmailAddress, PhoneNumber

UserModel = get_user_model()


class AuthenticationBackend(ModelBackend):
    """This inherits from the default authentication backend."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return

        # Check if there is a user with the given username.
        if UserModel.objects.filter(username=username).exists():
            user = UserModel.objects.get(username=username)
            if user.is_admin and user.check_password(password):
                return user

        # Check if there is any user available with the email address or the phone number associated with them.
        email_addresses = EmailAddress.objects.filter(email_address=username)
        phone_numbers = PhoneNumber.objects.filter(phone_number=username)

        if email_addresses.count() == 0 and phone_numbers.count() == 0:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user.
            UserModel.set_password(UserModel, raw_password=password)
            return

        # At this point, we know that there is at least one user available with given email address or phone number.
        # Check the given password for all available users.
        if email_addresses.count() >= 1:
            for email_object in email_addresses:
                if email_object.user.check_password(password):
                    return email_object.user

        # It the emails didn't hit, it must be a phone number which hit.
        if phone_numbers.count() >= 1:
            for phone_object in phone_numbers:
                if phone_object.user.check_password(password):
                    return phone_object.user
