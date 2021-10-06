from django.http import JsonResponse
from django.test import TestCase
from django.views import View

from .views import send_mail


class MailModelTest(TestCase):
    def test_send_mail(self):
        send_mail('multipart-default.tpl', 'simon@pra.st')


class MailTestView(View):
    def get(self, request):
        mail_data = send_mail('multipart-default.tpl', 'simon@pra.st')
        return JsonResponse(mail_data, json_dumps_params={'indent': 2})
