# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agentex', '0008_remove_datapoint_coordsource'),
    ]

    operations = [
        migrations.AddField(
            model_name='datapoint',
            name='coordsource',
            field=models.ForeignKey(blank=True, to='agentex.CatSource', null=True),
        ),
    ]
