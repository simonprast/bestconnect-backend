import graphene

# import user.schema
import sharepoint.schema
import oauth.schema


class Query(
    # user.schema.Query,
    sharepoint.schema.Query,
    oauth.schema.Query,
    graphene.ObjectType
):
    pass


# class Mutation(
#     user.schema.Mutation,
#     graphene.ObjectType
# ):
#     pass


schema = graphene.Schema(query=Query)
