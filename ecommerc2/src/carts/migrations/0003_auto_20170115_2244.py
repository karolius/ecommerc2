# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-01-15 21:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carts', '0002_auto_20170115_2226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, max_digits=30),
        ),
    ]