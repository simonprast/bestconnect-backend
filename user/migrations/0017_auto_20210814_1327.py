# Generated by Django 3.1.2 on 2021-08-14 11:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0016_auto_20210801_1035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='bank',
        ),
        migrations.RemoveField(
            model_name='user',
            name='bank_number',
        ),
        migrations.RemoveField(
            model_name='user',
            name='bic',
        ),
        migrations.RemoveField(
            model_name='user',
            name='iban',
        ),
        migrations.RemoveField(
            model_name='user',
            name='tax_number',
        ),
    ]
