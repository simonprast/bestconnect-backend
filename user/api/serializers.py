#
# Created on Mon Nov 02 2020
#
# Copyright (c) 2020 - Simon Prast
#


from rest_framework import serializers

from user.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password', 'is_admin']


class RegisterUserSerializer(serializers.ModelSerializer):
    # password = serializers.CharField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def save(self):
        User.objects.create_user(
            username=self.validated_data.get('username'),
            email=self.validated_data.get('email'),
            password=self.validated_data.get('password')
        )
