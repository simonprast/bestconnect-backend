from colorama import Fore, Style

from django.conf import settings

from .models import EmailAddress, User


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

                if not str(user.primary_email) == settings.ADMIN_MAIL:
                    print(f'{Fore.GREEN}Changing existing default superuser\'s email:')
                    print(f'From {user.primary_email} to {settings.ADMIN_MAIL}{Style.RESET_ALL}')

                    # The current email address must be cached as a string, as Django
                    # creates only a copy of the current state of the email object.
                    # (When fetching the email object immediately, the object's 'primary'
                    # attribute will be True after adding the new email address.)
                    old_email_address = user.primary_email

                    user.add_email_address(settings.ADMIN_MAIL, primary=True)

                    # Automatically verifiy a superuser's email address.
                    EmailAddress.objects.get(email_address=user.primary_email).verify()

                    if old_email_address is not None:
                        # Get the object related to the old email address and delete it after checks succeeded.
                        old_email_object = EmailAddress.objects.get(email_address=old_email_address)
                        EmailAddress.objects.remove(old_email_object)

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
                print(f'E-Mail: {user.primary_email}{Style.RESET_ALL}\n')
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

    if EmailAddress.objects.filter(email_address=settings.ADMIN_MAIL):
        email = EmailAddress.objects.get(email_address=settings.ADMIN_MAIL)
        if not email.user.default_superuser:
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
