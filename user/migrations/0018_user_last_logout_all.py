# Generated by Django 3.1.2 on 2021-08-14 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0017_auto_20210814_1327'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_logout_all',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]