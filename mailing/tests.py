from django.test import TestCase
from .views import sendMail


class MailModelTest(TestCase):
    def test_sendMail(self):
        sendMail('multipart-default.tpl', None, 'simon@pra.st')
