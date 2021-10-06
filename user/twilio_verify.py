from django.conf import settings

from twilio.rest import Client


def send_code(number, channel):
    # Create twilio client
    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)

    # Define the verification channel (Receive SMS or receive call)
    channel = channel.lower()
    if not channel:
        channel = 'sms'
    elif channel not in ['sms', 'call']:
        channel = 'sms'

    try:
        # Send an SMS message to the specified number.
        verification = client.verify \
            .services(settings.TWILIO_SERVICE_ID) \
            .verifications \
            .create(to=number, channel=channel)
    except Exception as e:
        # See Twilio error codes:
        # https://www.twilio.com/docs/api/errors
        return False, e.args[3]

    # This can be used for debugging purposes:
    # from pprint import pprint
    # pprint(verification.__dict__)

    return verification.status, None


def verify_code(number, code):
    # Create twilio client
    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        # Check a given verification code for a phone number.
        verification_check = client.verify \
            .services(settings.TWILIO_SERVICE_ID) \
            .verification_checks \
            .create(to=number, code=code)
    except Exception as e:
        # See Twilio error codes:
        # https://www.twilio.com/docs/api/errors
        return 'failed', e.args[3]

    return verification_check.status, None
