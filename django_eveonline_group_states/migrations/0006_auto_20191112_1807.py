# Generated by Django 2.2.4 on 2019-11-12 18:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_group_states', '0005_auto_20191105_1757'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evegroupstate',
            name='priority',
            field=models.IntegerField(default=0, unique=True),
        ),
    ]
