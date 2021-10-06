import graphene

from django.apps import apps
from django.utils import timezone

from graphql_jwt.decorators import login_required
from graphql_jwt.settings import jwt_settings

from api.helpers import ErrorType


def get_refresh_token_model():
    return apps.get_model(jwt_settings.JWT_REFRESH_TOKEN_MODEL)


def revoke_all_refresh(info):
    """
    Invalidates all refresh tokens of a user.
    """

    tokens = get_refresh_token_model().objects.filter(user=info.context.user, revoked=None)

    for token in tokens:
        if not token.is_expired():
            token.revoke(info.context)


class RevokeAll(graphene.Mutation):
    ok = graphene.Boolean()
    error = graphene.Field(ErrorType)

    @staticmethod
    @login_required
    def mutate(root, info):
        revoke_all_refresh(info)
        info.context.user.last_logout_all = timezone.now()
        info.context.user.save()
        return RevokeAll(ok=True)
