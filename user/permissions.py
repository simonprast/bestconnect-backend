from graphql_jwt.decorators import user_passes_test


# Check if the user is named 'Simon'.
def user_is_simon_f(user):
    return user.first_name == 'Simon'


# This is a demo permission check.
# Check if the user is named 'Simon' using the GraphQL JWT implementation.
user_is_simon = user_passes_test(lambda u: u.first_name == 'Simon')


# Instead of the lambda function, every other function returning a boolean can be used.
# user_is_simon = user_passes_test(user_is_simon_f)
