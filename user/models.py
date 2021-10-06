from colorama import Fore, Style

from django.conf import settings
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
        # Skip email validation for superusers.
        if not utype == 9:
            # Validate the given email address.
            try:
                validate_email(email)
            except exceptions.ValidationError:
                raise exceptions.ValidationError('Email address is not valid.')

            # Everything beyond the @ of an email address is case-insensitive according to RFC specs.
            # In practice, no well-known email provider uses case-sensitive username parts.
            # Therefore, lowercase the email string.
            email = email.lower()

        if not username:
            raise exceptions.ValidationError('Users must have an username.')

        user = self.model(
            username=username,
            email=email,
            utype=utype,
        )

        user.set_password(password)
        user.save(using=self._db)
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
    username = models.CharField(max_length=40, unique=True)
    email = models.EmailField(verbose_name='Email Address', null=True, blank=True, max_length=320)
    utype = models.IntegerField(verbose_name='User Type', default=0)
    is_admin = models.BooleanField(default=False)
    default_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # If the utype attribute is greater than or equal to 7, the is_admin attribute is automatically set to True.
        if self.utype < 7:
            self.is_admin = False
        else:
            self.is_admin = True

        # A user can never be saved using the same email address as another user.
        # The email field is optional for administrative users though,
        # therefore the unique attribute cannot be used here.
        if self.email is not None:
            if User.objects.filter(email=self.email).exclude(id=self.id).exists():
                print(User.objects.filter(email=self.email).exclude(username=self.username))
                raise exceptions.ValidationError('User with this E-Mail already exits.')

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


def create_admin_user():
    # This is called within the root URLs file at francy.urls, because, at this point, all modules / the user module is
    # already loaded. This function ensures that a default administrative user account exists.
    # Username, email and password are set according to environment variables ADMIN_USER, ADMIN_MAIL and ADMIN_PASSWORD.

    # If a default superuser account already exists, use it.
    if User.objects.filter(default_superuser=True).exists():
        user = User.objects.get(default_superuser=True)

        # If the superuser object should be persistent, the existing object is used and updated.
        # Else, the existing superuser object and its children are deleted.
        if settings.ADMIN_PERSISTENT:
            # Check wether another account with this username or email address already exists.
            username_unique_fail, email_unique_fail = unique_fail()

            if not username_unique_fail and not email_unique_fail:
                update = False
                if not user.username == settings.ADMIN_USER:
                    print(f'{Fore.GREEN}Changing existing default superuser\'s name:')
                    print(f'From {user.username} to {settings.ADMIN_USER}{Style.RESET_ALL}')

                    user.username = settings.ADMIN_USER
                    update = True

                if not user.email == settings.ADMIN_MAIL:
                    print(f'{Fore.GREEN}Changing existing default superuser\'s email:')
                    print(f'From {user.email} to {settings.ADMIN_MAIL}{Style.RESET_ALL}')

                    user.email = settings.ADMIN_MAIL
                    update = True

                if not user.check_password(settings.ADMIN_PASSWORD):
                    print(f'{Fore.GREEN}Updating existing default superuser\'s password.{Style.RESET_ALL}')

                    user.set_password(settings.ADMIN_PASSWORD)
                    update = True

                if update:
                    user.save()
                    # Line break
                    print('')

                print(f'{Fore.BLUE}Default superuser account:')
                print(f'Username: {user.username}')
                print(f'E-Mail: {user.email}{Style.RESET_ALL}\n')
            else:
                print(f'{Fore.BLUE}Keeping default superuser account attributes:')
                print(f'Username: {user.username}')
                print(f'E-Mail: {user.email}{Style.RESET_ALL}\n')
        else:
            User.objects.filter(default_superuser=True).delete()
    else:
        # Check wether another account with this username or email address already exists.
        username_unique_fail, email_unique_fail = unique_fail()

        if not username_unique_fail and not email_unique_fail:
            User.objects.create_superuser(
                username=settings.ADMIN_USER,
                email=settings.ADMIN_MAIL,
                password=settings.ADMIN_PASSWORD,
                default_superuser=True
            )

            print(f'{Fore.GREEN}Created default superuser account:')
            print(f'Username: {settings.ADMIN_USER}')
            print(f'E-Mail: {settings.ADMIN_MAIL}{Style.RESET_ALL}\n')


def unique_fail():
    # Check wether another account with this username or email address already exists.
    username_unique_fail = False
    email_unique_fail = False

    if User.objects.filter(username=settings.ADMIN_USER, default_superuser=False).exists():
        username_unique_fail = True

    if User.objects.filter(email=settings.ADMIN_MAIL, default_superuser=False).exists():
        email_unique_fail = True

    # ... and show an error message accordingly.
    if username_unique_fail or email_unique_fail:
        # ... A formatted string literal or f-string is a string literal that is prefixed with 'f' or 'F'.
        # These strings may contain replacement fields, which are expressions delimited by curly braces {}.
        # While other string literals always have a constant value, formatted strings are really expressions
        # evaluated at run time.
        print(f'{Fore.RED}Could not update default superuser account:', end='')

        if username_unique_fail:
            print('\nUsername already exists on non-superuser account.', end='')

        if email_unique_fail:
            print('\nE-Mail already exists on non-superuser account.', end='')

        print(f'{Style.RESET_ALL}\n')

    return username_unique_fail, email_unique_fail
