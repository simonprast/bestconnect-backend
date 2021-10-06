import json

# from django.test import TestCase

from graphene_django.utils.testing import GraphQLTestCase

from pprint import pprint

from .models import EmailToken, User


# class TestUserCreation(TestCase):
#     def test_user_creation(self):
#         User.objects.create_user(
#             username='test1',
#             email='simoF@pra.st',
#             password='test123',
#             utype=1
#         )

#         User.objects.create_user(
#             username='test2',
#             email='me+valid@mydomain.example.net',
#             password='test123',
#             utype=1
#         )

#         User.objects.create_user(
#             username='TestWithoutEmail',
#             email=None,
#             password='test123',
#             utype=9
#         )


class RegisterTestCase(GraphQLTestCase):
    GRAPHQL_URL = '/graphql'
    REGISTER_MAIL = 'test@simonprast.com'

    def test_registration(self):
        pheader('Register User Account Through GraphQL')

        mutation_create_user = self.query(
            '''
            mutation createUser {{
                registerUser(
                    input: {{
                        email: "{email}",
                        companyName: "InspireMedia GmbH",
                        firstName: "Simon",
                        lastName: "Prast",
                        password: "tes2t"
                    }}
                ) {{
                    ok
                    user {{
                        id
                        username
                    }}
                }}
            }}
            '''.format(email=self.REGISTER_MAIL)
        )

        content = json.loads(mutation_create_user.content)
        pmessage('The mutation response')
        pprint(content)

        self.assertResponseNoErrors(mutation_create_user)

        new_user = User.objects.get(pk=content['data']['registerUser']['user']['id'])
        user_email_token = EmailToken.objects.get(user=new_user)

        pmessage('The email verification token created')
        pprint(vars(user_email_token))

        pmessage('The email object before verifciation')
        pprint(vars(new_user.primary_email))

        response_verify_mail = self.query(
            '''
            mutation verifyEmail {{
                verifyEmail(emailAddress: "{email}", token: "{token}") {{
                    ok
                    emailObject {{
                        emailAddress
                        verified
                        primary
                    }}
                }}
            }}
            '''.format(email=self.REGISTER_MAIL, token=user_email_token.token)
        )

        content_verify_mail = json.loads(response_verify_mail.content)
        pmessage('The email verification mutation response')
        pprint(content_verify_mail)

        pmessage('The email object after verifciation')
        pprint(vars(new_user.primary_email))


def pheader(msg):
    print('\n##############################################################')
    print(msg)
    print('##############################################################')


def pmessage(msg):
    print('\n\n###', msg, '###\n')
