#
# Created on Mon Nov 02 2020
#
# Copyright (c) 2020 - Simon Prast
#


from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer


def obtain_auth_token(username, password):
    serializer_auth = AuthTokenSerializer(
        data={'username': username, 'password': password})
    if serializer_auth.is_valid():
        user = serializer_auth.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return token, created, user
    return None, None, None


def remove_token(user):
    Token.objects.filter(user=user).delete()


def refresh_token(user):
    remove_token(user)
    token = Token.objects.create(user=user)
    return token
