# Generated by Django 3.1.2 on 2021-06-04 10:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0004_mailmodel_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailmodel',
            name='from_email',
            field=models.CharField(blank=True, max_length=320, null=True),
        ),
        migrations.AlterField(
            model_name='mailmodel',
            name='to_email',
            field=models.CharField(blank=True, max_length=320, null=True),
        ),
    ]
