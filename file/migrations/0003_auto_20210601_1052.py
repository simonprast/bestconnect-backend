# Generated by Django 3.1.2 on 2021-06-01 08:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0002_auto_20210518_1415'),
    ]

    operations = [
        migrations.RenameField(
            model_name='document',
            old_name='created_by',
            new_name='owner',
        ),
    ]
