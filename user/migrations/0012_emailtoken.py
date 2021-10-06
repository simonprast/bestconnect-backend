# Generated by Django 3.1.2 on 2021-06-10 09:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0011_auto_20210604_1202'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('email_address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.emailaddress')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]