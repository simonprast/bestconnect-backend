# Generated by Django 3.1.2 on 2021-03-26 08:15

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0003_auto_20210325_1259'),
    ]

    operations = [
        migrations.AddField(
            model_name='mailmodel',
            name='date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
