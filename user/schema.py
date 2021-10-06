import graphene

from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.core.validators import validate_email
from django.utils import timezone

from graphene_django import DjangoObjectType

from graphql_jwt import ObtainJSONWebToken, Refresh, Revoke, Verify
from graphql_jwt.decorators import login_required, staff_member_required

from api.helpers import ErrorType

from .auth_backends.revoke_refresh_token import RevokeAll

from .ban_codes import ban_codes

from .models import EmailAddress, EmailToken, EmailTokenSpamBlock, PhoneNumber, User

from .twilio_verify import send_code, verify_code

from .views import initialize_verification_process

from .system_messages import system_messages


def get_email_object(user, email_address):
    if EmailAddress.objects.filter(user=user, email_address=email_address).exists():
        return EmailAddress.objects.get(user=user, email_address=email_address)
    else:
        return None


class EmailAddressType(DjangoObjectType):
    class Meta:
        model = EmailAddress
        exclude = 'id', 'comment', 'user'


class PhoneNumberType(DjangoObjectType):
    class Meta:
        model = PhoneNumber
        exclude = 'id', 'comment', 'user'


class BanCodeType(graphene.ObjectType):
    code = graphene.Int()
    info = graphene.String()


class UserType(DjangoObjectType):
    # email_addresses = graphene.List(EmailAddressType)

    class Meta:
        model = User
        # fields = ['id', 'username', 'email', 'emailaddress_set']
        exclude = [
            'id',
            'password',
            'username',
            'utype',
            'is_admin',
            'default_superuser'
        ]

    # def resolve_email_addresses(self, info):
    #     return EmailAddress.objects.filter(user=self)


class Query(graphene.ObjectType):
    users = graphene.List(UserType)
    user = graphene.Field(UserType, id=graphene.Int(required=True))
    me = graphene.Field(UserType)
    ban_codes = graphene.List(BanCodeType, code=graphene.Int())

    @staff_member_required
    def resolve_users(self, info, **kwargs):
        return User.objects.all()

    @staff_member_required
    def resolve_user(self, info, id, **kwargs):
        if not User.objects.filter(pk=id).exists():
            return None
        return User.objects.get(pk=id)

    @login_required
    def resolve_me(self, info):
        return info.context.user

    def resolve_ban_codes(self, info, **kwargs):
        code = kwargs.get('code', None)

        ban_message_list = []

        if code:
            ban_message = BanCodeType(code, ban_codes[code])
            ban_message_list.append(ban_message)
        else:
            for code, message in ban_codes.items():
                ban_message = BanCodeType(code, message)
                ban_message_list.append(ban_message)

        return ban_message_list


# Create Input Object Types
class UserInput(graphene.InputObjectType):
    id = graphene.ID()
    email = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    password = graphene.String()


class AddressInput(graphene.InputObjectType):
    street_1 = graphene.String()
    street_2 = graphene.String()
    zip_code = graphene.String()
    city = graphene.String()
    country = graphene.String()


class DetailedUserInput(graphene.InputObjectType):
    id = graphene.ID()
    first_name = graphene.String()
    last_name = graphene.String()
    password = graphene.String()
    old_password = graphene.String()
    address = graphene.Field(AddressInput)


class RegisterUser(graphene.Mutation):
    """
    Create a user from a UserInput object.

    This mutation can return following errors:
    - Code 1: A user with this email already exists. This can be overridden by provding the forceRegister parameter.
    - Code 2: A user with exactly this email and password combination already exists. Please login.
    - Code 3: A input variable is missing (email, firstName, lastName or password).
    - Code 4: Given email address is invalid.
    - Code 5: Given password does not meet requirements.
    """

    class Arguments:
        input = UserInput(required=True)
        force_register = graphene.Boolean()

    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    error = graphene.Field(ErrorType)

    @staticmethod
    def mutate(root, info, force_register=False, input=None):
        if not info.context.user.is_anonymous:
            error = ErrorType(
                code=6,
                message='You are already logged in.'
            )

            return RegisterUser(ok=False, error=error)

        if not input.email or not input.first_name or not input.last_name or not input.password:
            return RegisterUser(
                ok=False,
                error=ErrorType(
                    code=3,
                    message='Please provide all necessary input values.'
                )
            )

        # Validate the given email address.
        try:
            validate_email(input.email)
        except exceptions.ValidationError:
            return RegisterUser(
                ok=False,
                error=ErrorType(
                    code=4,
                    message='Given email address is invalid.'
                )
            )

        # Validate the password requirements.
        try:
            validate_password(input.password)
        except exceptions.ValidationError as e:
            return RegisterUser(
                ok=False,
                error=ErrorType(
                    code=5,
                    message='Password does not meet the requirements: ' + str(e)
                )
            )

        # Check if a user exists with this email address.
        if User.objects.filter_email(email_address=input.email):
            if not force_register:
                error = ErrorType(
                    code=1,
                    message='A user with this email already exists. ' +
                            'Provide forceRegister: true if you want to create a new account.'
                )

                return RegisterUser(ok=False, error=error)

            # Check if a user with exactly this email and password combination exists.
            for user in User.objects.filter_email(email_address=input.email):
                if user.check_password(input.password):
                    error = ErrorType(
                        code=2,
                        message='A user with this email and password combination already exists. ' +
                                'Please log into your existing account.'
                    )

                    return RegisterUser(ok=False, error=error)

            # At this point, no user with this email + password combination
            # exists and a new account is wished to be created.

        user = User.objects.create_user(
            email=input.email,
            first_name=input.first_name,
            last_name=input.last_name,
            password=input.password
        )

        # Prepare the email verification process.
        initialize_verification_process(user, user.primary_email)

        return RegisterUser(ok=True, user=user)


# A mutation for changing user data.
class UpdateUser(graphene.Mutation):
    """
    Update a user from a DetailedUserInput object.

    This mutation can return following errors:
    - Code 1: There was no current password provided while trying to change it.
    - Code 2: The current password did not match the one in the database.
    """

    class Arguments:
        input = DetailedUserInput(required=True)

    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, input):
        user = info.context.user

        if input.first_name:
            user.first_name = input.first_name

        if input.last_name:
            user.last_name = input.last_name

        if input.password:
            if not input.old_password:
                # Create an error
                error = ErrorType(
                    code=1,
                    message='Please provide your old password.'
                )

                return UpdateUser(ok=False, error=error)

            if not user.check_password(input.old_password):
                # Return an error showing the old password was wrong.
                error = ErrorType(
                    code=2,
                    message='The old password is incorrect.'
                )

                return UpdateUser(ok=False, error=error)

            # TODO: Password validation
            user.set_password(input.password)
            # TODO: Double-check, send email to user?

        if input.address:
            if input.address.street_1:
                user.street_1 = input.address.street_1

            if input.address.street_2:
                user.street_2 = input.address.street_2

            if input.address.zip_code:
                user.zip_code = input.address.zip_code

            if input.address.city:
                user.city = input.address.city

            if input.address.country:
                user.country = input.address.country

        user.save()

        return UpdateUser(ok=True, user=info.context.user)


class RequestVerifyEmail(graphene.Mutation):
    """
    One can either add a new email address to a user account using this mutation, or request the verification of an
    existing one. If both an email address and the objectId is provided, the system will try to use the objectId.

    This mutation can return following errors:
    - Code 1: Anti-spam protection (request blocked)
    - Code 2: Couldn't find an available email object for verification
    (obj does not exist, not on user or already verified)
    - Code 3: Neither an object id, nor an email address was provided
    - Code 4: The given email address is already verified on this account
    - Code 5: Email address format is invalid
    - Code 6: Email address is already verified on another account
    """
    class Arguments:
        email_address = graphene.String()
        object_id = graphene.Int()

    ok = graphene.Boolean()
    email_object = graphene.Field(EmailAddressType)
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, email_address=None, object_id=None):
        # If an object ID is given, try to get the email object with this ID.
        if object_id:
            if EmailAddress.objects.filter(pk=object_id, user=info.context.user, verified=False).exists():
                email_object = EmailAddress.objects.get(pk=object_id, user=info.context.user, verified=False)
            else:
                error = ErrorType(
                    message='There is no email object with this ID available for this action.',
                    code=2
                )

                return RequestVerifyEmail(ok=False, error=error)
        else:
            # If no object_id is given, the email_address must be used.
            if not email_address:
                error = ErrorType(
                    message='Please provide an email address or an email object ID.',
                    code=3
                )

                return RequestVerifyEmail(ok=False, error=error)

            # This hits if the user has a given email address alraedy associated with his account.
            email_object = get_email_object(info.context.user, email_address)

            if email_object and email_object.verified:
                error = ErrorType(
                    message='This email address is already verified on your account.',
                    code=4
                )

                return RequestVerifyEmail(ok=False, error=error)

        # Check for anti-spam protection
        if info.context.user.last_email_request and info.context.user.last_email_request > timezone.now():
            # Calculate second-difference between now and last_email_request.
            difference = (info.context.user.last_email_request - timezone.now()).total_seconds()

            error = ErrorType(
                message='Your request is currently blocked (anti-spam). Seconds remaining: ' + str(difference),
                code=1
            )

            return RequestVerifyEmail(ok=False, error=error)

        # If the email address is new (no object_id), validate the email
        # and check if the email already exists on another account.
        if not email_object:
            try:
                validate_email(email_address)
            except exceptions.ValidationError:
                error = ErrorType(
                    message='Given email address is invalid.',
                    code=5
                )

                return RequestVerifyEmail(ok=False, error=error)

            # At this point, we already know that the email address does not exist on his own account.
            # Therefore there is no need to filter for other accounts.
            if EmailAddress.objects.filter(email_address=email_address, verified=True).exists():
                # Set the anti-spam time to now +20 seconds
                info.context.user.last_email_request = timezone.now() + timedelta(seconds=20)
                info.context.user.save()

                error = ErrorType(
                    message='This email address is already verified on another account.',
                    code=6
                )

                return RequestVerifyEmail(ok=False, error=error)

            # At this point, the email address isn't verified on any account and can be added to the user.
            email_object = info.context.user.add_email_address(email_address)

        initialize_verification_process(info.context.user, email_object)

        # Set the anti-spam to now +10 minutes.
        info.context.user.last_email_request = timezone.now() + timedelta(minutes=5)

        return RequestVerifyEmail(ok=True, email_object=email_object)


class VerifyEmail(graphene.Mutation):
    """
    This mutation is respoonsible for verifying an existing email address using a verification code.
    No login is required for this mutation, as users must also be able to verify their email address
    by using the link received by mail on the mobile phone.
    """
    class Arguments:
        email_address = graphene.String()
        token = graphene.String()

    ok = graphene.Boolean()
    email_object = graphene.Field(EmailAddressType)
    error = graphene.Field(ErrorType)

    @staticmethod
    def mutate(root, info, email_address, token):
        # It is to be checked...
        # - if anti-spam hits
        # - if the email address is already verified
        # - if there is a EmailToken object with the given email address and token
        # - if the token is valid or expired
        # - to remove the email from all other accounts after sucessfully verifying it
        # - to ban other users if they have no other email address left

        # Validate the email address format.
        try:
            validate_email(email_address)
        except exceptions.ValidationError:
            error = ErrorType(
                message='Given email address format is invalid.',
                code=3
            )

            return VerifyEmail(ok=False, error=error)

        # Validate if the verificatino code has 6 digits and is numeric.
        if not token.isdigit() or len(token) != 6:
            error = ErrorType(
                message='The verification code format is invalid (has to be numeric and 6 digits long).',
                code=4
            )

            return VerifyEmail(ok=False, error=error)

        # Check for anti-spam protection.
        if not EmailTokenSpamBlock.request_allowed(email_address):
            time_remaining = EmailTokenSpamBlock.time_remaining(email_address)

            error = ErrorType(
                message='Your request is currently blocked (anti-spam). Seconds remaining: ' + str(time_remaining),
                code=1
            )

            return VerifyEmail(ok=False, error=error)

        # Check if there is a EmailToken object with the given email address and token.
        if not EmailToken.objects.filter(token=token, email_address=email_address).exists():
            error = ErrorType(
                message='No verification process found for this email + token combination.',
                code=5
            )

            return VerifyEmail(ok=False, error=error)

        token_object = EmailToken.objects.get(token=token, email_address=email_address)

        # Set the anti-spam protection of verification request to now +10 seconds.
        token_object.user.last_email_request = timezone.now() + timedelta(seconds=10)
        token_object.user.save()

        token_object.email_object.verify()

        return VerifyEmail(ok=True, email_object=token_object.email_object)


# Use AddPhoneNumber to associate a new phone number with a user.
class AddPhoneNumber(graphene.Mutation):
    """
    Using this mutation, the given phone number can be associated with the user, given the number is not verified on
    another account already. Afterwards, the number must be verified using a code received by SMS or call, as provided
    using the channel parameter.

    This mutation can return following errors:
    - Code 1: Anti-spam protection (request blocked)
    - Code 2: Phone number did not pass the parser but succeeded all checks (backup check)
    - Code 3: Phone number already verified and on own account (anti-spam blocked)
    - Code 4: Phone number already verified and on own account (outside of anti-spam)
    - Code 5: Phone number already on account but not yet verified (anti-spam blocked)
    - Code 6: Phone number already verified on another account
    - Code 101: The string supplied did not seem to be a phone number (phonenumbers parse error)
    - Code 201: This phone number is not within the allowed prefix regions
    - Code 202: The phone number was successfully parsed but is not valid (backup check)
    - Code 60203: Max send attempts reached
    - Code xxxxx: An unidentified Twilio error occured

    3-digit error codes occur at PhoneNumber.validate_phone_number().

    5-digit error codes are Twilio errors.
    """
    class Arguments:
        phone_number = graphene.String(required=True)
        channel = graphene.String(default_value='sms')

    ok = graphene.Boolean()
    phone_object = graphene.Field(PhoneNumberType)
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, phone_number, channel):
        # Validate phone number
        phone_number, err = PhoneNumber.validate_phone_number(phone_number)
        if not phone_number:
            if err:
                error = ErrorType(
                    message=err['message'],
                    code=err['code']
                )

                return AddPhoneNumber(ok=False, error=error)

            error = ErrorType(
                message='No valid phone number could be processed.',
                code=2
            )

            return AddPhoneNumber(ok=False, error=error)

        # When is the next request allowed?
        # Check if user.last_phone_request time is in the future.
        # last_phone_request stores the time at which the next request is allowed.
        if info.context.user.last_phone_request and info.context.user.last_phone_request > timezone.now():
            # Calculate second-difference between now and last_phone_request.
            difference = (info.context.user.last_phone_request - timezone.now()).total_seconds()

            # Check if the phone number already exists on the User.
            if PhoneNumber.objects.filter(user=info.context.user, phone_number=phone_number).exists():
                phone_object = PhoneNumber.objects.get(user=info.context.user, phone_number=phone_number)

                if phone_object.verified:
                    error = ErrorType(
                        message='This phone number is already verified on your account.',
                        code=3
                    )

                    return AddPhoneNumber(ok=False, error=error)
                else:
                    error = ErrorType(
                        message='This phone number is already associated with your account. ' +
                                'You can use the verification code you already received, ' +
                                'or wait for anti-spam to run out. Seconds ramaining: ' + str(difference),
                        code=5
                    )

                    return AddPhoneNumber(ok=False, error=error)

            error = ErrorType(
                message='Your request is currently blocked (anti-spam). Seconds remaining: ' + str(difference),
                code=1
            )

            return AddPhoneNumber(ok=False, error=error)

        # Anti-spam does not hit at this point.
        # Check if verified phone number already exists on another account than the requesting user.
        if PhoneNumber.objects.filter(verified=True, phone_number=phone_number).exists():
            # Get this phone number object.
            phone_object = PhoneNumber.objects.get(verified=True, phone_number=phone_number)

            # Check if the requesting user is the owner of this phone number.
            if phone_object.user != info.context.user:
                error = ErrorType(
                    message='This phone number is already verified on another account.',
                    code=6
                )
            else:
                error = ErrorType(
                    message='This phone number is already associated with your account.',
                    code=4
                )

            # Set the anti-spam threshold to now +20 seconds.
            info.context.user.last_phone_request = timezone.now() + timedelta(seconds=20)
            info.context.user.save()

            return AddPhoneNumber(ok=False, error=error)

        # The phone number is not already on any account and verified at this point.

        # Check if the phone number is already on the user's account.
        if PhoneNumber.objects.filter(user=info.context.user, phone_number=phone_number).exists():
            phone_object = PhoneNumber.objects.get(user=info.context.user, phone_number=phone_number)
        else:
            # Add new phone number object to user.
            phone_object = info.context.user.add_phone_number(phone_number)

        # Set the anti-spam threshold to now +2 minutes.
        info.context.user.last_phone_request = timezone.now() + timedelta(minutes=2)
        info.context.user.save()

        # Send a verification code to the user.
        status, err = send_code(phone_number, channel)

        if not status:
            if err == 60203:
                error = ErrorType(
                    message='A Twilio error occured. Max send attempts reached.',
                    code=err
                )

                return AddPhoneNumber(ok=False, error=error)

        return AddPhoneNumber(ok=True, phone_object=phone_object)


# Check phone number verification code.
class CheckPhoneNumber(graphene.Mutation):
    """
    Using this mutation, the given phone number can be verified using the code received by SMS.
    Please note that anti-spam threshold is set to 5 seconds after unsuccesful verification.

    This mutation can return following errors:
    - Code 1: Anti-spam protection (request blocked)
    - Code 2: Phone number did not pass the parser
    - Code 3: The verification code format is invalid
    - Code 4: Verified number already on own account
    - Code 5: Verified number already on another account
    - Code 6: The verification code is invalid
    - Code 7: An unidenitfied error occurred
    - Code 8: Checking phone number not on account
    - Code 20404: No verification process found for this phone number (expired, not started, wrong number)
    - Code 60202: Max check attempts reached
    - Code xxxxx: An unidentified Twilio error occured

    5-digit error codes are Twilio errors.
    """
    class Arguments:
        phone_number = graphene.String(required=True)
        code = graphene.String(required=True)

    ok = graphene.Boolean()
    phone_object = graphene.Field(PhoneNumberType)
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, phone_number, code):
        # Validate phone number
        phone_number, err = PhoneNumber.validate_phone_number(phone_number)

        if not phone_number:
            if err:
                error = ErrorType(
                    message=err['message'],
                    code=err['code']
                )

                return CheckPhoneNumber(ok=False, error=error)

            error = ErrorType(
                message='No valid phone number could be processed.',
                code=2
            )

            return CheckPhoneNumber(ok=False, error=error)

        # Validate if the verificatino code has 6 digits and is numeric.
        if not code.isdigit() or len(code) != 6:
            error = ErrorType(
                message='The verification code format is invalid (has to be numeric and 6 digits long).',
                code=3
            )

            return CheckPhoneNumber(ok=False, error=error)

        # Check if the last_phone_code_request time is in the future.
        # last_phone_code_request stores the time at which the next request is allowed.
        if info.context.user.last_phone_code_request and info.context.user.last_phone_code_request > timezone.now():
            # Calculate second-difference between now and last_phone_code_request.
            difference = (info.context.user.last_phone_code_request - timezone.now()).total_seconds()

            error = ErrorType(
                message='Your request is currently blocked (anti-spam). Seconds remaining: ' + str(difference),
                code=1
            )

            return CheckPhoneNumber(ok=False, error=error)

        # Check if the phone number is already verified on own account.
        if PhoneNumber.objects.filter(user=info.context.user, phone_number=phone_number, verified=True).exists():
            error = ErrorType(
                message='This phone number is already verified on your account.',
                code=4
            )

            return CheckPhoneNumber(ok=False, error=error)

        # Check if the phone number is associated to the user.
        # This should never happen during normal usage but could be done by manipulating Frontend requests.
        if not PhoneNumber.objects.filter(user=info.context.user, phone_number=phone_number).exists():
            error = ErrorType(
                message='This phone number is not associated with the requesting account.',
                code=8
            )

            return CheckPhoneNumber(ok=False, error=error)

        # Check if the phone number is already verified on another account.
        # This is just a backup check. Normally, all unverified phone numbers
        # will be deleted if one user verifies their phone number.
        if PhoneNumber.objects.filter(verified=True, phone_number=phone_number).exists():
            error = ErrorType(
                message='This phone number is already verified on another account.',
                code=5
            )

            return CheckPhoneNumber(ok=False, error=error)

        # Set the anti-spam threshold to now +5 seconds.
        info.context.user.last_phone_code_request = timezone.now() + timedelta(seconds=5)
        info.context.user.save()

        status, err = verify_code(phone_number, code)

        if status == 'approved':
            # Get this phone number object.
            phone_object = PhoneNumber.objects.get(user=info.context.user, phone_number=phone_number)

            # Set the verified flag to True.
            phone_object.verify()

            # If a number is successfully verified, the user can immediately add a new number.
            # Set the anti-spam threshold to now +5 seconds.
            info.context.user.last_phone_request = timezone.now() + timedelta(seconds=5)
            info.context.user.save()

            return CheckPhoneNumber(ok=True, phone_object=phone_object)

        elif status == 'pending':
            error = ErrorType(
                message='The verification code is invalid.',
                code=6
            )

            return CheckPhoneNumber(ok=False, error=error)

        elif status == 'failed':
            if err == 20404:
                error = ErrorType(
                    message='A Twilio error occured. The verification process was not found for this number. The ' +
                            'code is maybe expired, or the process was never started, or you already used the code.',
                    code=err
                )

                return CheckPhoneNumber(ok=False, error=error)

            if err == 60202:
                error = ErrorType(
                    message='A Twilio error occured. Max check attempts reached.',
                    code=err
                )

                return CheckPhoneNumber(ok=False, error=error)

            error = ErrorType(
                message='An unidenitfied Twilio error occurred. Plese contact support using the error code.',
                code=err
            )

            return CheckPhoneNumber(ok=False, error=error)

        # At this point, something with the verification has gone wrong.
        error = ErrorType(
            message='An unidentified error occurred while verifying your phone number.',
            code=7
        )

        return CheckPhoneNumber(ok=False, error=error)


# Remove email address with given primary key.
class RemoveEmailAddress(graphene.Mutation):
    """
    Remove an email address from the user's account.

    This mutation can return following errors:
    - Code 1: No email address found on account
    - Code 2: Primary addresses cannot be removed
    - Code 3: Unkown error occured - this should never happen
    """

    class Arguments:
        object_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, object_id):
        # Check if given object exists on the user's account.
        if not EmailAddress.objects.filter(user=info.context.user, pk=object_id).exists():
            error = ErrorType(
                message='The email object does not exist on your account.',
                code=1
            )

            return RemoveEmailAddress(ok=False, error=error)

        # Check if given object id is a primary address.
        if EmailAddress.objects.get(pk=object_id).primary:
            error = ErrorType(
                message='You cannot remove the primary email address.',
                code=2
            )

            return RemoveEmailAddress(ok=False, error=error)

        success = info.context.user.remove_email_address(object_id)

        error = None

        if not success:
            error = ErrorType(
                message='An error occurred while removing the email address.',
                code=3
            )

        return RemoveEmailAddress(ok=success, error=error)


# Remove phone number with given primary key.
class RemovePhoneNumber(graphene.Mutation):
    """
    Remove a phone number from the user's account.

    This mutation can return following errors:
    - Code 1: No phone number found on account
    - Code 2: Primary phone numbers cannot be removed
    - Code 3: Unkown error occured - this should never happen
    """

    class Arguments:
        object_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, object_id):
        # Check if given object exists on the user's account.
        if not PhoneNumber.objects.filter(user=info.context.user, pk=object_id).exists():
            error = ErrorType(
                message='The phone object does not exist on your account.',
                code=1
            )

            return RemovePhoneNumber(ok=False, error=error)

        # Check if given object id is a primary phone number.
        if PhoneNumber.objects.get(pk=object_id).primary:
            error = ErrorType(
                message='You cannot remove the primary phone number.',
                code=2
            )

            return RemovePhoneNumber(ok=False, error=error)

        success = info.context.user.remove_phone_number(object_id)

        error = None

        if not success:
            error = ErrorType(
                message='An error occurred while removing the phone number.',
                code=3
            )

        return RemovePhoneNumber(ok=success, error=error)


# A mutation for making a specific email address primary.
class SetPrimaryEmailAddress(graphene.Mutation):
    """
    Set a specific email address as primary.

    This mutation can return following errors:
    - Code 1: No email address found on account
    - Code 2: Object already primary
    - Code 3: Object must be verified in order to become primary
    """

    class Arguments:
        object_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    email_object = graphene.Field(EmailAddressType)
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, object_id):
        # Check if given object exists on the user's account.
        if not EmailAddress.objects.filter(user=info.context.user, pk=object_id).exists():
            error = ErrorType(
                message='The email object does not exist on your account.',
                code=1
            )

            return SetPrimaryEmailAddress(ok=False, error=error)

        email_object = EmailAddress.objects.get(pk=object_id)

        if email_object.primary:
            error = ErrorType(
                message='The email address is already set as primary.',
                code=2
            )

            return SetPrimaryEmailAddress(ok=False, error=error)

        # Only verified emails can be set as primary email addresses.
        if not email_object.verified:
            error = ErrorType(
                message='The email address is not verified.',
                code=3
            )

            return SetPrimaryEmailAddress(ok=False, error=error)

        email_object.set_primary()

        return SetPrimaryEmailAddress(ok=True, email_object=email_object)


# A mutation for making a specific phone number primary.
class SetPrimaryPhoneNumber(graphene.Mutation):
    """
    Set a specific phone number as primary.

    This mutation can return following errors:
    - Code 1: No phone number found on account
    - Code 2: Object already primary
    - Code 3: Object must be verified in order to become primary
    """

    class Arguments:
        object_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    phone_object = graphene.Field(PhoneNumberType)
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info, object_id):
        # Check if given object exists on the user's account.
        if not PhoneNumber.objects.filter(user=info.context.user, pk=object_id).exists():
            error = ErrorType(
                message='The phone object does not exist on your account.',
                code=1
            )

            return SetPrimaryPhoneNumber(ok=False, error=error)

        phone_object = PhoneNumber.objects.get(pk=object_id)

        if phone_object.primary:
            error = ErrorType(
                message='The phone number is already set as primary.',
                code=2
            )

            return SetPrimaryPhoneNumber(ok=False, error=error)

        # Only verified phone numbers can be set as primary phone numbers.
        if not phone_object.verified:
            error = ErrorType(
                message='The phone number is not verified.',
                code=3
            )

            return SetPrimaryPhoneNumber(ok=False, error=error)

        phone_object.set_primary()

        return SetPrimaryPhoneNumber(ok=True, phone_object=phone_object)


class Mutation(graphene.ObjectType):
    register_user = RegisterUser.Field()
    update_user = UpdateUser.Field()
    request_verify_email = RequestVerifyEmail.Field()
    verify_email = VerifyEmail.Field()
    add_phone_number = AddPhoneNumber.Field()
    check_phone_number = CheckPhoneNumber.Field()
    remove_email_address = RemoveEmailAddress.Field()
    remove_phone_number = RemovePhoneNumber.Field()
    set_primary_email_address = SetPrimaryEmailAddress.Field()
    set_primary_phone_number = SetPrimaryPhoneNumber.Field()
    login = ObtainJSONWebToken.Field()
    logout = Revoke.Field()
    logout_all = RevokeAll.Field()
    verify_token = Verify.Field()
    refresh_token = Refresh.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
