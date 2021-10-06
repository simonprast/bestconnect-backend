import graphene


class ErrorType(graphene.ObjectType):
    message = graphene.String()
    code = graphene.Int()
