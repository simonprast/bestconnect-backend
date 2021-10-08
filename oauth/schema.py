import graphene
import requests

from django.conf import settings

from pprint import pprint


class BearerTokenInfo(graphene.ObjectType):
    expires_in = graphene.Int()
    ext_expires_in = graphene.Int()
    access_token = graphene.String()
    refresh_token = graphene.String()


class Query(graphene.ObjectType):
    obtain_token = graphene.Field(BearerTokenInfo, code=graphene.String())
    refresh_token = graphene.Field(BearerTokenInfo, refresh_token=graphene.String())

    def resolve_obtain_token(self, info, code, **kwargs):
        payload = {
            'grant_type': 'authorization_code',
            'client_id': settings.MS_CLIENT_ID,
            'client_secret': settings.MS_CLIENT_SECRET,
            'scope': 'https://kanbon.sharepoint.com/.default offline_access',
            'code': code,
            'redirect_uri': settings.MS_REDIRECT_URI
        }

        pprint(payload)

        req = requests.post(
            'https://login.microsoftonline.com/74f8e6c7-a9d7-48db-9ad1-811e938553e1/oauth2/v2.0/token',
            data=payload
        )

        pprint(req.json())

        obj = BearerTokenInfo(
            expires_in=req.json()['expires_in'],
            ext_expires_in=req.json()['ext_expires_in'],
            access_token=req.json()['access_token'],
            refresh_token=req.json()['refresh_token']
        )

        return obj

    def resolve_refresh_token(self, info, refresh_token, **kwargs):
        payload = {
            'grant_type': 'refresh_token',
            'client_id': settings.MS_CLIENT_ID,
            'client_secret': settings.MS_CLIENT_SECRET,
            'scope': 'https://kanbon.sharepoint.com/.default offline_access',
            'refresh_token': refresh_token,
            'redirect_uri': settings.MS_REDIRECT_URI
        }

        req = requests.post(
            'https://login.microsoftonline.com/74f8e6c7-a9d7-48db-9ad1-811e938553e1/oauth2/v2.0/token',
            data=payload
        )

        pprint(req.json())

        obj = BearerTokenInfo(
            expires_in=req.json()['expires_in'],
            ext_expires_in=req.json()['ext_expires_in'],
            access_token=req.json()['access_token'],
            refresh_token=req.json()['refresh_token']
        )

        return obj
