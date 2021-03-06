# Generated by Django 3.1.2 on 2021-08-25 12:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0021_auto_20210819_1713'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.JSONField(blank=True, null=True)),
                ('code', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read', models.BooleanField(default=False)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
