# Based on graphql_jwt.backends.JSONWebTokenBackend, extending GraphQL
# JWT's default backend by the User.last_logut_all implementation.

from graphql_jwt.exceptions import JSONWebTokenExpired
from graphql_jwt.shortcuts import get_user_by_token
from graphql_jwt.utils import get_credentials, get_payload, get_user_by_natural_key


class JSONWebTokenBackend:

    def authenticate(self, request=None, **kwargs):
        if request is None or getattr(request, '_jwt_token_auth', False):
            return None

        token = get_credentials(request, **kwargs)

        if token is not None:
            user = get_user_by_token(token, request)

            # Get the token's payload.
            t = get_payload(token)
            # t contains the token's creation date (origIat).

            # A JWT can also contain following, most of it is unused right now:
            # Registered Claim Names
            # 'iss' (Issuer) Claim
            # 'sub' (Subject) Claim
            # 'aud' (Audience) Claim
            # 'exp' (Expiration Time) Claim
            # 'iat' (Issued At) Claim
            # 'jti' (JWT ID) Claim

            # If the token was initialized before the last_logout_all timestamp, the token is handled as expired.
            # Skip the validation if the user did never set the last_logout_all field.
            if user.last_logout_all:
                if user.last_logout_all.timestamp() >= t.get('origIat'):
                    raise JSONWebTokenExpired()

            return get_user_by_token(token, request)

        return None

    def get_user(self, user_id):
        return get_user_by_natural_key(user_id)
