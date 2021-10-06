#
# Created on Mon Nov 02 2020
#
# Copyright (c) 2020 - Simon Prast
#


from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from rest_framework import exceptions, generics, mixins, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import obtain_auth_token, refresh_token, remove_token

from ..models import User
from .serializers import UserSerializer, RegisterUserSerializer


class UserList(mixins.ListModelMixin,
               generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            user = User.objects.get(pk=pk)
            return user
        except User.DoesNotExist:
            raise exceptions.NotFound

    def get(self, request, *args, **kwargs):
        # A staff user is allowed to see all users
        if request.user.is_staff:
            return self.list(request, *args, **kwargs)
        # AnonymousUsers are denied.
        # If the User is not anonymous, only show the requesting user himself.
        elif not request.user.is_anonymous:
            user = self.get_object(request.user.id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        else:
            exceptions.PermissionDenied


class UserCreateOrLogin(generics.GenericAPIView):
    serializer_class = RegisterUserSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            # Deny any request thats not from an AnonymousUser
            return Response({'detail': 'You cannot create an account while authenticated.'}, status=status.HTTP_403_FORBIDDENe)
        else:
            serializer = RegisterUserSerializer(data=request.data)

            if settings.ALLOW_REGISTER:
                if serializer.is_valid():
                    # Creates the user using create_user()
                    serializer.save()

            # Authenticate the newly created user
            # OR authenticate the existing user with given username and password combination.
            token, created, user = obtain_auth_token(
                request.data.__getitem__('username'),
                request.data.__getitem__('password')
            )

            # If a user with given username does already exist but the username password
            # combination is wrong, 'token', 'created' and 'user' will be set to 'None'.
            # In this case, this error response is thrown.
            if not token:
                errors = {
                    'username': [
                        'user with this username already exists',
                        'username and password combination wrong'
                    ]
                }
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

            # Either the user object was created or the user just logged in
            auth_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

            # Attach a 'created' confirmation to the return dictionary if the object was just created
            return_dict = {'username': user.username, 'token': token.key} if not created else {
                'username': user.username, 'token': token.key, 'created': 'True'}

            return Response(return_dict, status=auth_status)


class UserDetail(mixins.RetrieveModelMixin,
                 mixins.UpdateModelMixin,
                 mixins.DestroyModelMixin,
                 generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_requested_object(self, pk):
        try:
            user = User.objects.get(pk=pk)
            return user
        except User.DoesNotExist:
            raise exceptions.NotFound

    def get(self, request, pk, *args, **kwargs):
        # Get the requested user
        requested_user = self.check_requested_object(pk=pk)
        # Only allow staff users and own requests
        if request.user.is_staff or requested_user == request.user:
            return self.retrieve(request, *args, **kwargs)
        else:
            raise exceptions.PermissionDenied

    def put(self, request, pk, *args, **kwargs):
        # Get the requested user
        requested_user = self.check_requested_object(pk=pk)
        # Only allow staff users and own requests
        if request.user.is_staff or requested_user == request.user:
            # This copies the request.data dictionary,
            # as request.data is read-only.
            altered_request_data = request.data.copy()

            # last_login cannot be altered.
            if altered_request_data.__contains__('last_login'):
                altered_request_data.pop('last_login')

            # utype can only be altered by administrative accounts.
            if altered_request_data.__contains__('utype') and not request.user.is_staff:
                altered_request_data.pop('utype')

            # Update the object using the serializer.
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=altered_request_data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            # Copy the read-only serializer.data dictionary.
            serializer_data = serializer.data

            # Set a new password if it was sent through the request body
            password = request.data.get('password', False)
            if password:
                requested_user.set_password(password)
                requested_user.save()

                # If the user who requests the password change is the user itself,
                # the user is given a new token. If the password is changed by an admin,
                # the valid login token is deleted.
                if requested_user == request.user:
                    token = refresh_token(requested_user)
                    serializer_data.update({'token': str(token)})
                else:
                    remove_token(requested_user)

            return Response(serializer_data)
        else:
            raise exceptions.PermissionDenied
