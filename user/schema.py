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

from .ban_codes import ban_codes

from .models import EmailAddress, PhoneNumber, User

from .twilio_verify import send_code, verify_code

from .views import handle_verify, initialize_verification_process


def get_email_object(user, email_address):
    if EmailAddress.objects.filter(user=user, email_address=email_address).exists():
        return EmailAddress.objects.get(user=user, email_address=email_address)
    else:
        raise exceptions.ObjectDoesNotExist


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
        exclude = 'password', 'email', 'utype', 'is_admin'

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


class RequestVerifyEmail(graphene.Mutation):
    class Arguments:
        email_address = graphene.String()

    ok = graphene.Boolean()
    email_object = graphene.Field(EmailAddressType)

    @staticmethod
    @login_required
    def mutate(root, info, email_address):
        email_object = get_email_object(info.context.user, email_address)

        if email_object.verified:
            raise exceptions.ValidationError('This email address is already verified.')

        initialize_verification_process(info.context.user, email_object)

        ok = True

        return RequestVerifyEmail(ok=ok, email_object=email_object)


class VerifyEmail(graphene.Mutation):
    class Arguments:
        email_address = graphene.String()
        token = graphene.String()

    ok = graphene.Boolean()
    email_object = graphene.Field(EmailAddressType)

    @staticmethod
    def mutate(root, info, email_address, token):
        email_object = handle_verify(email_address, token)

        if email_object:
            ok = True
        else:
            ok = False

        return VerifyEmail(ok=ok, email_object=email_object)


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

                return CheckPhoneNumber(ok=False, error=error)

        return AddPhoneNumber(ok=True, phone_object=phone_object)


# Check phone number verification code
class CheckPhoneNumber(graphene.Mutation):
    """
    Using this mutation, the given phone number can be verified using the code received by SMS.

    This mutation can return following errors:
    - Code 1: Anti-spam protection (request blocked)
    - Code 2: Phone number did not pass the parser
    - Code 3: The verification code format is invalid
    - Code 4: Verified number already on own account
    - Code 5: Verified number already on another account
    - Code 6: The verification code is invalid
    - Code 7: An unidenitfied error occurred
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
        phone_number = PhoneNumber.validate_phone_number(phone_number)
        if not phone_number:
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


class Mutation(graphene.ObjectType):
    register_user = RegisterUser.Field()
    request_verify_email = RequestVerifyEmail.Field()
    verify_email = VerifyEmail.Field()
    addPhoneNumber = AddPhoneNumber.Field()
    checkPhoneNumber = CheckPhoneNumber.Field()
    login = ObtainJSONWebToken.Field()
    logout = Revoke.Field()
    verify_token = Verify.Field()
    refresh_token = Refresh.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
