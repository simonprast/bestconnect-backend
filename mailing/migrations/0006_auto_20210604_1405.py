# Generated by Django 3.1.2 on 2021-06-04 12:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0005_auto_20210604_1202'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailmodel',
            name='message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='mailmodel',
            name='subject',
            field=models.TextField(blank=True, null=True),
        ),
    ]