from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username',)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords don\'t match')
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserAdmin(BaseUserAdmin):
    # The custom form handling for creating a user
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        'id',
        'username',
        'email',
        'is_admin',
        'default_superuser'
    )

    list_filter = (
        'is_admin',
        'default_superuser'
    )

    fieldsets = (
        (
            None, {
                'fields': (
                    'username',
                    'email'
                )
            }
        ),
        (
            'Permissions', {
                'fields': (
                    'utype',
                    'is_admin',
                    'default_superuser'
                )
            }
        ),
    )

    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            None, {
                'fields': (
                    'username',
                    'email',
                    'utype',
                    'password1',
                    'password2'
                )
            }
        ),
    )

    search_fields = (
        'id',
        'username',
        'email'
    )
    ordering = (
        'id',
    )
    filter_horizontal = ()


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)
