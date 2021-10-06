import graphene

from graphene_django.types import DjangoObjectType

import user.schema


class Query(
        user.schema.Query,
        graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
