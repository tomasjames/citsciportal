'''
Citizen Science Portal: App containing Agent Exoplant and Show Me Stars for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from django.contrib import admin
from showmestars.models import Event

class EventAd(admin.ModelAdmin):
    list_display = ['name','start','end','site']


admin.site.register(Event,EventAd)
