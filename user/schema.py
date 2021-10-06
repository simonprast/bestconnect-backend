import graphene
from graphene_django import DjangoObjectType

from .models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        # exclude = 'password', 'utype', 'is_admin'


class Query(graphene.ObjectType):
    users = graphene.List(UserType)

    def resolve_users(self, info, **kwargs):
        return User.objects.all()
