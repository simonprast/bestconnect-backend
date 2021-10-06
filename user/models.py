from django.core import exceptions
from django.core.validators import validate_email
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(
        self,
        username,
        email=None,
        password=None,
        utype=1,
        default_superuser=False
    ):
        if not username:
            raise exceptions.ValidationError('Users must have an username.')

        if email and EmailAddress.objects.filter(email_address=email).exists():
            raise exceptions.ValidationError('This email address already exists on an account.')

        user = self.model(
            username=username,
            utype=utype,
            default_superuser=default_superuser
        )

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


class User(AbstractBaseUser):
    # Essential fields
    username = models.CharField(max_length=40, unique=True)
    email = models.EmailField(verbose_name='Email Address', null=True, blank=True, max_length=320)
    utype = models.IntegerField(verbose_name='User Type', default=0)
    is_admin = models.BooleanField(default=False)
    default_superuser = models.BooleanField(default=False)

    # Meta fields
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    # Contact Fields
    company_name = models.CharField(max_length=64, null=True, blank=True)
    first_name = models.CharField(max_length=64, null=True, blank=True)
    last_name = models.CharField(max_length=64, null=True, blank=True)
    bank = models.CharField(max_length=64, null=True, blank=True)
    iban = models.CharField(max_length=64, null=True, blank=True)
    bank_number = models.CharField(max_length=64, null=True, blank=True)
    bic = models.CharField(max_length=64, null=True, blank=True)
    tax_number = models.CharField(max_length=64, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'

    # Add a new mail address and associate it with the user account
    def add_email_address(self, email_address, primary=False):
        """Associates a new mail address with a user account.
        Per default, a new mail address isn't a users new primary mail address.
        The primary attribute can also be set to True."""

        email_object = EmailAddress.objects.add_email_address(
            user=self,
            email_address=str(email_address),
            primary=primary
        )

        email_object.save()

        return True

    @property
    def get_primary_email(self):
        if self.emailaddress_set.filter(primary=True).exists():
            return self.emailaddress_set.get(primary=True)
        else:
            return None

    @property
    def get_primary_phone(self):
        return self.phonenumber_set.get(primary=True).phone_number or None

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # If the utype attribute is greater than or equal to 7, the is_admin attribute is automatically set to True.
        if self.utype < 7:
            self.is_admin = False
        else:
            self.is_admin = True

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
    def is_active(self):
        return True

    # Needed for Django functionality
    @property
    def is_staff(self):
        'Is the user a member of staff?'
        # Simplest possible answer: All admins are staff
        return self.is_admin


class Address(models.Model):
    # User reference
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )

    # Address fields
    street_1 = models.CharField(max_length=64, null=True, blank=True)
    street_2 = models.CharField(max_length=64, null=True, blank=True)
    zip_code = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True)

    primary = models.BooleanField(default=True, null=True, blank=True)


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
        if EmailAddress.objects.filter(email_address=email_address).exists():
            raise ValueError('This email address already exists on an account.')

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

    def verify(
        self,
        email_object
    ):
        'Set the verified status of an email object to True.'

        # TODO: Email handling before verification
        # Allow adding a unverified email to any account. Whenever an email address is
        # verified on another account, inform the user that its unverified email address
        # has been removed from his account.

        email_object.verified = True
        email_object.save()

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

    email_address = models.CharField(max_length=64, null=True, blank=True)
    comment = models.CharField(max_length=256, null=True, blank=True)
    verified = models.BooleanField(default=False, null=True, blank=True)
    primary = models.BooleanField(default=True, null=True, blank=True)

    objects = EmailManager()

    def __str__(self):
        return self.email_address
