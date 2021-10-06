from django.test import TestCase

from user.models import User


class TestUserCreation(TestCase):
    def test_user_creation(self):
        User.objects.create_user(
            username='test1',
            email='simoF@pra.st',
            password='test123',
            utype=1
        )

        User.objects.create_user(
            username='test2',
            email='me+valid@mydomain.example.net',
            password='test123',
            utype=1
        )

        User.objects.create_user(
            username='TestWithoutEmail',
            email=None,
            password='test123',
            utype=9
        )
