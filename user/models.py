import phonenumbers
import secrets

from datetime import timedelta

from django.conf import settings
from django.core import exceptions
from django.core.validators import validate_email
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

from uuid import uuid4

from .system_messages import system_messages


class UserManager(BaseUserManager):
    def create_user(
        self,
        username=None,
        email=None,
        password=None,
        utype=1,
        default_superuser=False,
        **kwargs
    ):
        if not username:
            username = uuid4()

        if email and EmailAddress.objects.filter(email_address=email).exists():
            verified_exists = False
            for email_object in EmailAddress.objects.filter(email_address=email):
                if email_object.user.check_password(password):
                    raise exceptions.ValidationError('User already registered. Please log in.')

                if email_object.verified:
                    verified_exists = True

            if verified_exists:
                raise exceptions.ValidationError('This email address already exists on another account.')

        user = self.model(
            username=username,
            utype=utype,
            default_superuser=default_superuser
        )

        first_name = kwargs.get('first_name', None)
        user.first_name = first_name

        last_name = kwargs.get('last_name', None)
        user.last_name = last_name

        user.set_password(password)
        user.save(using=self._db)

        if email:
            # The email address added when creating the account is always the primary address.
            user.add_email_address(email, primary=True)

        return user

    def create_superuser(
        self,
        username,
        email=None,
        password=None,
        default_superuser=False
    ):
        user = self.create_user(
            username=username,
            email=email,
            password=password,
            utype=9,
            default_superuser=default_superuser
        )

        return user

    # Return a list containing all user's with a given email address.
    def filter_email(self, email_address):
        if EmailAddress.objects.filter(email_address=email_address).exists():
            users = []

            for email_object in EmailAddress.objects.filter(email_address=email_address):
                users.append(email_object.user)

            return users

        return None


class User(AbstractBaseUser):
    # Essential fields
    username = models.CharField(max_length=40, unique=True)
    utype = models.IntegerField(verbose_name='User Type', default=0)
    is_admin = models.BooleanField(default=False)
    default_superuser = models.BooleanField(default=False)

    # In order to be able to block user accounts and show them a specific message
    is_active = models.BooleanField(default=True)
    ban_reason = models.IntegerField(default=0, null=True, blank=True)

    # Meta fields
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    last_logout_all = models.DateTimeField(null=True, blank=True)

    # Contact fields
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)

    # Personal address fields
    street_1 = models.CharField(max_length=255, null=True, blank=True)
    street_2 = models.CharField(max_length=255, null=True, blank=True)
    zip_code = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)

    # Anti-Spam
    last_phone_request = models.DateTimeField(null=True, blank=True)
    last_phone_code_request = models.DateTimeField(null=True, blank=True)
    last_email_request = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'

    # Add a new mail address and associate it with the user account.
    def add_email_address(self, email_address, primary=False):
        """Associates a new mail address with a user account.
        Per default, a new mail address isn't a users new primary mail address.
        The primary attribute can also be set to True."""

        email_object = EmailAddress.objects.add_email_address(
            user=self,
            email_address=email_address,
            primary=primary
        )

        email_object.save()

        return email_object

    # Remove a mail address from the user account.
    def remove_email_address(self, pk):
        try:
            email_object = EmailAddress.objects.get(pk=pk, user=self)
            email_object.delete()
            return True
        except EmailAddress.DoesNotExist:
            return False

    @property
    def primary_email(self):
        if self.emailaddress_set.filter(primary=True).exists():
            return self.emailaddress_set.get(primary=True)
        else:
            return None

    # Add a new phone number and associate it with the user account.
    def add_phone_number(self, phone_number, primary=False):
        """Associates a new phone number with a user account.
        Per default, a new phone number isn't a users new primary phone number.
        The primary attribute can also be set to True."""

        phone_object = PhoneNumber.objects.create(
            user=self,
            phone_number=phone_number,
            primary=primary
        )

        phone_object.save()

        return phone_object

    # Remove a phone number from the user account.
    def remove_phone_number(self, pk):
        try:
            phone_object = PhoneNumber.objects.get(pk=pk, user=self)
            phone_object.delete()
            return True
        except PhoneNumber.DoesNotExist:
            return False

    @property
    def primary_phone(self):
        if self.phonenumber_set.filter(primary=True).exists():
            return self.phonenumber_set.get(primary=True)
        else:
            return None

    def deactivate_account(self, reason):
        self.is_active = False
        self.ban_reason = reason
        self.save()

    def add_system_message(self, code, variables=None, message=None):
        if code:
            message = system_messages[code]

            if variables:
                message.format(variables)

        message = SystemMessage.objects.create(
            user=self,
            message=message
        )

        return message

    def __str__(self):
        return str(self.username)

    def save(self, *args, **kwargs):
        # If the utype attribute is greater than or equal to 7, the is_admin attribute is automatically set to True.
        if self.utype < 7:
            self.is_admin = False
        else:
            self.is_admin = True

        # Remove the ban_reason for active accounts.
        if self.is_active:
            self.ban_reason = 0

        super(User, self).save(*args, **kwargs)

    # Needed for Django functionality
    def has_perm(self, perm, obj=None):
        'Does the user have a specific permission?'
        # Simplest possible answer: Yes, always
        return True

    # Needed for Django functionality
    def has_module_perms(self, app_label):
        'Does the user have permissions to view the app `app_label`?'
        # Simplest possible answer: Yes, always
        return True

    # Needed for Django functionality
    @property
    def is_staff(self):
        'Is the user a member of staff?'
        # Staff has utype above 7.
        return self.utype >= 7 or self.is_admin


class SystemMessage(models.Model):
    """
    System messages sent to users.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Message in the format {locale: message}
    message = models.JSONField(null=True, blank=True)
    code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    @property
    def custom(self):
        return True if self.code == 0 else False


class PhoneNumber(models.Model):
    # User reference
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )

    # Phone number fields
    phone_number = models.CharField(max_length=64, null=True, blank=True)
    comment = models.CharField(max_length=256, null=True, blank=True)
    verified = models.BooleanField(default=False, null=True, blank=True)
    primary = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return self.phone_number

    def set_primary(self):
        if not self.verified:
            return False

        if PhoneNumber.objects.filter(user=self.user, primary=True).exists():
            old_phone = PhoneNumber.objects.get(user=self.user, primary=True)
            old_phone.primary = False
            old_phone.save()

        self.primary = True
        self.save()
        return True

    def verify(self):
        self.verified = True

        # Check if the user has a primary phone number.
        if self.user.primary_phone is None:
            self.primary = True

        # Check if this phone number is on any other account.
        # Delete this phone number from all other accounts which have not verified this number.
        if PhoneNumber.objects.filter(phone_number=self.phone_number).exclude(user=self.user).exists():
            for phone_object in PhoneNumber.objects.filter(phone_number=self.phone_number).exclude(user=self.user):
                phone_object.delete()

        self.save()

    # Verify a phone number
    @staticmethod
    def validate_phone_number(phone_number):
        # Try to parse the phone number string, if this is not possible it will return False
        try:
            n = phonenumbers.parse(phone_number, None)

            if phonenumbers.phonenumberutil.region_code_for_number(n) not in settings.ALLOWED_PHONE_REGIONS:
                return None, {
                    'message': 'This phone number is not within allowed regions. (' +
                               str(settings.ALLOWED_PHONE_REGIONS) + ')',
                    'code': 201
                }
        except phonenumbers.phonenumberutil.NumberParseException:
            return None, {
                'message': 'The string supplied did not seem to be a phone number.',
                'code': 101
            }

        if not phonenumbers.is_valid_number(n):
            return None, {
                'message': 'The phone number was successfully parsed but is not valid.',
                'code': 202
            }

        # e.g. +436641234567, as a string
        return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164), None


class EmailManager(models.Manager):
    def add_email_address(
        self,
        user,
        email_address,
        primary=False,
        comment=None
    ):
        """Add a new email address to a user account.
        This function takes the user and a string containing a valid email address.
        Per default, new email addresses aren't primary nor verified."""

        # Skip email validation for superusers.
        if not user.utype == 9:
            # Validate the given email address.
            try:
                validate_email(email_address)
            except exceptions.ValidationError:
                raise exceptions.ValidationError('Email address is not valid.')

            # Everything beyond the @ of an email address is case-insensitive according to RFC specs.
            # In practice, no well-known email provider uses case-sensitive username parts.
            # Therefore, lowercase the email string.
            email_address = email_address.lower()

        # Unique check
        if EmailAddress.objects.filter(email_address=email_address, verified=True).exists():
            raise exceptions.ValidationError('This email address already exists on another account.')

        # Before making a email primary, check for the current primary email address.
        if primary:
            if EmailAddress.objects.filter(user=user, primary=True):
                email_object = EmailAddress.objects.get(user=user, primary=True)
                email_object.primary = False
                email_object.save()

        email_object = EmailAddress(
            user=user,
            email_address=email_address,
            primary=primary,
            comment=comment
        )

        email_object.save()

        return email_object

    def remove(
        self,
        email_object
    ):
        'Deletes given email object after checking for any interferences.'

        # Prevent the deletion of primary email addresses.
        if email_object.primary:
            raise ValueError('Cannot delete a primary email address.')

        email_object.delete()

        return True

    def set_primary(
        self,
        email_object
    ):
        'Make an email object the primary mail address after checking for the current primary address.'

        # Before making a email primary, check for the current primary email address.
        if EmailAddress.objects.filter(user=email_object.user, primary=True).exists():
            old_primary = EmailAddress.objects.get(user=email_object.user, primary=True)
            old_primary.primary = False
            old_primary.save()

        email_object.primary = True
        email_object.save()

    def get_primary_addresses(self):
        return EmailAddress.objects.filter(primary=True)


class EmailAddress(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )

    email_address = models.CharField(max_length=320, null=True, blank=True)
    comment = models.CharField(max_length=256, null=True, blank=True)
    verified = models.BooleanField(default=False, null=True, blank=True)
    primary = models.BooleanField(default=True, null=True, blank=True)

    objects = EmailManager()

    def __str__(self):
        return self.email_address

    def set_primary(self):
        if not self.verified:
            return False

        if EmailAddress.objects.filter(user=self.user, primary=True).exists():
            old_primary = EmailAddress.objects.get(user=self.user, primary=True)
            old_primary.primary = False
            old_primary.save()

        self.primary = True
        self.save()
        return True

    def verify(self):
        'Set the verified status of an email object to True.'
        # Handled at verification.views.handle_verify

        self.verified = True
        self.save()

        # Delete all email addresses on another account.
        other_email_objects = EmailAddress.objects.filter(email_address=self.email_address, verified=False)

        # Deactivate every user account which had only the recently verified email active.
        for other_email_object in other_email_objects:
            if other_email_object.user.primary_email.email_address == self.email_address:
                other_email_object.user.deactivate_account(2)

        other_email_object.user.add_system_message(1, variables=other_email_object.email_address)
        other_email_objects.delete()

        if not self.user.primary_email.verified:
            self.set_primary()


def generate_token():
    token = secrets.randbelow(999999)
    token = str(token).zfill(6)
    return token


class EmailToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    email_object = models.ForeignKey(
        EmailAddress, on_delete=models.CASCADE
    )
    email_address = models.CharField(
        max_length=320, null=True, blank=True
    )
    token = models.CharField(
        max_length=6, default=generate_token
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        self.email_address = self.email_object.email_address
        super(EmailToken, self).save(*args, **kwargs)

    def is_valid(self):
        return True if (timezone.now() - self.created_at).seconds < 600 else False


class EmailTokenSpamBlock(models.Model):
    email_address = models.CharField(max_length=320, null=True, blank=True)
    last_email_code_request = models.DateTimeField(null=True, blank=True)

    @classmethod
    def request_allowed(cls, email_address, until_timedelta=timedelta(seconds=5)):
        if not EmailTokenSpamBlock.objects.filter(email_address=email_address).exists():
            cls.block(email_address, until_timedelta)
            return True
        else:
            obj = EmailTokenSpamBlock.objects.get(email_address=email_address)
            blocked_until = obj.last_email_code_request

            if timezone.now() > blocked_until:
                obj.delete()
                cls.block(email_address, until_timedelta)
                return True

            return False

    @staticmethod
    def block(email_address, until_timedelta):
        blocked_until = timezone.now() + until_timedelta

        EmailTokenSpamBlock.objects.create(
            email_address=email_address,
            last_email_code_request=blocked_until
        )

    @staticmethod
    def time_remaining(email_address):
        obj = EmailTokenSpamBlock.objects.get(email_address=email_address)
        difference = (obj.last_email_code_request - timezone.now()).total_seconds()
        return difference
