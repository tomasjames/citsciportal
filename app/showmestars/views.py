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
from agentex.models import Target, Event, Datapoint, DataSource, Badge, Achievement, DataCollection,Decision,CatSource, Observer, AverageSet
from agentex.views import photometry, calibrator_data, admin_averagecals
from django.contrib import admin
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
import json

class DatapointAd(admin.ModelAdmin):
    list_display = ['taken','data','pointtype','user','xpos','ypos','value','coorder','get_source']
    list_filter = ['pointtype']
    def get_source(self,obj):
        return '%s' % obj.coorder.source
    get_source.allow_tags = True
    get_source.short_description = 'Cat Source'
    
class DCAdmin(admin.ModelAdmin):
    list_display = ['planet','person','calid','display','complete']
    list_filter = ['display','complete','planet','person']

class DecAdmin(admin.ModelAdmin):
    list_display = ['value','person','planet','taken','source']
    list_filter = ['planet','value']
class CatAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['final']
    list_display = ['name','data','get_planet','final']
    def get_planet(self,obj):
        return '%s' % obj.data.event.title
    get_planet.allow_tags = True
    get_planet.short_description = 'Planet'
      
class DSAdmin(admin.ModelAdmin):
    list_filter = ['event','target']
    list_display = ['timestamp','event','target']
    
class EventAdmin(admin.ModelAdmin):
    list_display = ['title','name','start','midpoint','end','numobs','xpos','ypos','enabled']    
class TargetAdmin(admin.ModelAdmin):
    list_display = ['name','ra','dec','period','rstar','mass','ap','inclination']
    
class SetAdmin(admin.ModelAdmin):
    list_display = ['planet','star','settype']
    
def allcalibrators_check(request,planetid):
    # Uses and SQL statement to try to speed up the query for averaging data points
    e = Event.objects.filter(id=planetid)[0]
    normcals,dates,ids,cats = admin_averagecals(e.name,0)
    c = json.dumps(cats)
    # return normcals,stamps,[int(i) for i in ids],cats
    title = 'Check calibrators for %s' % e.title
    return render_to_response('admin/agentex/allcalibrators.html',{'calibrators':normcals,
                                                                    'title':title,
                                                                    'planetid':planetid,
                                                                    'dates':dates,
                                                                    'calids':[int(i) for i in ids],
                                                                    'cats':c},context_instance=RequestContext(request))
    
def calibrator_check(request,planetid,calid):
    planet = Event.objects.get(id=planetid)
    dcs = DataCollection.objects.filter(source__id=calid)
    if request.POST:
        people = request.POST.getlist('user')
        dcs.update(display=False)  
        include = request.POST.get('include','none')
        cs = CatSource.objects.filter(id=calid)
        if include == 'false':
            cs.update(final=False)
        elif include == 'true':
            cs.update(final=True)
        elif include == 'none':
            dcup = dcs.filter(person__username__in=people)
            dcup.update(display=True)
    data,times,people = calibrator_data(calid,planet.name)
    include = dcs.filter(person__username__in=people).values_list('display',flat=True)
    resp = {'data'       : data,
            'timestamps' : times,
            'people'     : people,
            'include'    : list(include),
            }
    return HttpResponse(json.dumps(resp,indent=2),mimetype='application/javascript')
    
admin.site.register(Target, TargetAdmin)
admin.site.register(Event,EventAdmin)
admin.site.register(Datapoint, DatapointAd)
admin.site.register(DataSource,DSAdmin)
admin.site.register(Badge)
admin.site.register(Decision,DecAdmin)
admin.site.register(Achievement)
admin.site.register(Observer)
admin.site.register(CatSource,CatAdmin)
admin.site.register(DataCollection,DCAdmin)
admin.site.register(AverageSet,SetAdmin)
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
decision_images = {
    'D':{'name':'Dip','image':'choice_dip.png'},
    'N':{'name':'No Dip','image':'choice_nodip.png'},
    'O':{'name':'Odd','image':'choice_odd.png'},
    'B':{'name':'Blip','image':'choice_blip.png'},
    'P':{'name':'Periodic','image':'choice_periodic.png'},
    'S':{'name':'Noise','image':'choice_noise.png'},
    'R':{'name':'Other','image':'choice_other.png'},
}

planet_level = {
    'corot2b' : 'beginner',
    'ogletr132b' : 'advanced',
}'''
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
from agentex.models import Event, AverageSet, Decision, Datapoint, DataSource, Target
import agentex as ax

####
#import matplotlib.pyplot as plt
####

from django.contrib.auth.models import User
from django.db.models import Count, Avg
from datetime import datetime
from calendar import timegm
from numpy import array,nan_to_num, vstack, apply_along_axis, mean, var, sqrt,average, r_, linspace

from django.conf import settings

class Dataset(object):
    def __init__(self , planetid=None,userid=None):
        try:
            self.planet = Event.objects.get(name=planetid)
        except:
            self.planet = None
        try:
            self.user = User.objects.get(username=userid)
        except:
            self.user = None
        try:
            self.target = Target.objects.get(name=self.planet.title[:-1])
        except:
            self.target = None
    def calibrators(self):
        sc = AverageSet.objects.filter(planet=self.planet, settype='S')[0].data
        bg = AverageSet.objects.filter(planet=self.planet, settype='B')[0].data
        return cals,sc,bg,time,ids,cats
    def final(self):
        normvals = AverageSet.objects.filter(planet=self.planet,settype='F')[0].data
        std = AverageSet.objects.filter(planet=self.planet,settype='E')[0].data
        sources = DataSource.objects.filter(event=self.planet).order_by('timestamp')
        #myvals = ax.views.myaverages(self.planet,self.user)
        n = 0
        data = []
        if len(normvals) == self.planet.numobs :
            for i,s in enumerate(sources):
                line = {
                        'id'        : "%i" % s.id,
                        'date'      : s.timestamp.isoformat(" "),
                        'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                        'data'      : {
                                        'mean' : normvals[i],
                                        'std'  : std[i],
                                        'mine' : 'null',#myvals[i],
                            },
                        }
                data.append(line)
        else:
            data = None
        return data
    def my_data(self):
        if self.user:
            data = []
            sources = DataSource.objects.filter(event=self.planet).values_list('id','timestamp').order_by('timestamp')
            points  = Datapoint.objects.filter(data__event=self.planet,user=self.user)
            sc = dict(points.filter(pointtype='S').values_list('data__id','value'))
            bg = dict(points.filter(pointtype='B').values_list('data__id','value'))
            cals = points.filter(pointtype='C').values_list('data__id','value').order_by('coorder')
            for d in sources:
                cal = [c[1] for c in cals if int(c[0]) == d[0]]
                line = {
                        'id'        : "%i" % d[0],
                        'date'      : d[1].isoformat(" "),
                        'datestamp' : timegm(d[1].timetuple())+1e-6*d[1].microsecond,
                        'data'      : { 'source' : None,
                                        'background' :  None,
                                        'calibrator' :  cal,
                                    },
                        }
                try:
                    line['data']['source'] = [sc[d[0]]]
                except:
                    line['data']['source'] = 'null'
                try:
                    line['data']['background'] = [bg[d[0]]]
                except:
                    line['data']['background'] = 'null' 
                data.append(line)
            return data,points
        else:
            self.error = "No user specified"
            return False
        # Produce final lightcurve from the average data sets
        # calibs = []
        # mypoints = []
        # calslist = []
        # ti = 0.
        # # assume data which has AverageSet forms part of a complete set
        # # People and their sources who have Dips in the select planet
        # decs = Decision.objects.values_list('person','source').filter(value='D', current=True, planet=self.planet, source__datacollection__display=True).annotate(Count('source'))
        # peoplelst,sourcelst,tmp = zip(*decs)
        # people = set(peoplelst)
        # sources = set(sourcelst)
        # #catsources = Decision.objects.values_list('source',flat=True).filter(value='D', current=True, planet=self.planet)
        # if decs.count() > 0:
        #     vals = Datapoint.objects.filter(data__event=self.planet,user__in=people)
        #     sourceave = vals.filter(pointtype='S').values_list('data').annotate(mean=Avg('value')).order_by('data__timestamp')
        #     bgave = vals.filter(pointtype='B').values_list('data').annotate(mean=Avg('value')).order_by('data__timestamp')
        #     sc_ave = zip(*sourceave)
        #     bg_ave = zip(*bgave)
        #     sc = array(sc_ave[1])
        #     bg = array(bg_ave[1])
        #     sets = AverageSet.objects.filter(planet=self.planet,star__in=sources)
        #     for s in sets:
        #         calslist.append(s.data)
        #     numsuper = sets.count()
        #     if settings.LOCAL_DEVELOPMENT: print "Number of supercals for %s : %s" % (self.planet.title,numsuper)
        #     # sc_set = AverageSet.objects.filter(planet=self.planet, settype='S')[0]
        #     # bg_set = AverageSet.objects.filter(planet=self.planet, settype='B')[0]
        #     # sc = array(sc_set.data)
        #     # bg = array(bg_set.data)
        #     calstack = vstack(calslist)
        #     cc = (sc-bg)/(calstack-bg)
        #     n = 0
        #     sourcelist = list(sources)
        #     calibs.append(cc.tolist())
        #     norm_a = lambda a: mean(r_[a[:3],a[-3:]])
        #     cala = vstack(calibs)
        #     norms = apply_along_axis(norm_a, 1, cala)
        #     dim = len(cala)
        #     norm1 = cala/norms.reshape(dim,1)
        #     for c in norm1:
        #         filename = 'media/transit/%s-%s.png' % (self.planet.name,sourcelist[n])
        #         plt.plot(linspace(0,len(sc),len(sc)),c, lw=2)
        #         plt.savefig(filename)
        #         plt.close()
        #         n+=1
        #     norm_alt = mean(norm1,axis=0)
        #     variance = var(norm1,axis=0)
        #     std = sqrt(variance)
        #     fz = list(norm_alt)
        #     mycals = myaverages(self.planet,self.user)
        #     nodata = True
        #     return numsuper,fz,mycals,list(std),nodata
        # else:
        #     print "No average sets"
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
from django import forms
from types import *
from django.forms import TextInput,Textarea
from django.contrib.auth.models import User

class DataEntryForm(forms.Form):
    sourceradius = forms.CharField(label='Aperture Radius (source)')
    sourcexpos = forms.CharField(label='Source x position')
    sourceypos = forms.CharField(label='Source y position')
    sourcecounts = forms.CharField(label='Source counts')
#    cal1radius = forms.CharField(label='Aperture Radius (calibrator)')
#    cal1xpos = forms.CharField(label='Calibrator x postion')
#    cal1ypos = forms.CharField(label='Calibrator y postion')
#    cal1counts = forms.CharField(label='Calibrator counts')
    bgradius = forms.CharField(label='Aperture Radius (background)')
    bgxpos = forms.CharField(label='Background x position')
    bgypos = forms.CharField(label='Background y position')
    bgcounts = forms.CharField(label='Background counts')
    
class RegisterForm(forms.Form):
    username = forms.CharField(label=u'Choose a username')
    password = forms.CharField(label= u'Password',widget=forms.PasswordInput(render_value=False))
    firstname = forms.CharField(label=u'What should we call you? (e.g. as a greeting)')
    lastname = forms.CharField(label=u'Full Name')
    emailaddress = forms.EmailField(label= u'Contact email address',widget=TextInput(attrs={'size':'60'}))
    
    def clean_username(self):
      username = self.cleaned_data['username']
      try:
          user = User.objects.get(username=username)
      except User.DoesNotExist:
          return username
      raise forms.ValidationError(u'%s already exists' % username )

            
class RegistrationEditForm(forms.Form):
    password = forms.CharField(label= u'Password',widget=forms.PasswordInput(render_value=False),required=False)
    firstname = forms.CharField(label=u'What should we call you? (e.g. as a greeting)')
    lastname = forms.CharField(label=u'Full Name')
    emailaddress = forms.EmailField(label= u'Contact email address',widget=TextInput(attrs={'size':'60'}))
    
class CommentForm(forms.Form):
    emailaddress = forms.EmailField(label= u'Contact email address',widget=TextInput(attrs={'size':'60'}),required=True)
    comment = forms.CharField(label='Comment',max_length=160, help_text='160 characters max.',widget=Textarea(attrs={'rows':4, 'cols':60}),required=True)'''
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
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from calendar import timegm
from json import dumps,loads
TYPECHOICE = (
('S','Source'),
('C','Calibration'),
('B','Background'),
('R','Reduced'),
('F','Final'),
('E','Error bar')
)
ENTRYCHOICE = (
('W','Web'),
('M','Manual'),
('N','No javascript'),
)

DECISIONS = (
('D','Dip'),
('N','No Dip'),
('O','Odd'),
('B','Blip'),
('P','Periodic'),
('S','Noise'),
('R','Other'),
)
decisions = {
    'dip':'D',
    'nodip':'N',
    'odd':'O',
    'blip':'B',
    'periodic':'P',
    'other':'R',
}

class Target(models.Model):
    name = models.CharField(blank=True, max_length=100) # Wordy name. should be the name of the host star
    ra = models.CharField('right ascension',blank=True, max_length=100)
    dec = models.CharField('declination',blank=True, max_length=100)
    constellation = models.CharField(blank=True, max_length=100)
    magv = models.CharField('apparent magnitude V',blank=True, max_length=100)
    inclination = models.FloatField('inclination of planet orbit',blank=True,null=True)
    period = models.FloatField('period of planet orbit (days)',blank=True,null=True)
    rstar = models.FloatField('radius of host star',blank=True,null=True)
    ap = models.FloatField('semi-major axis',blank=True,null=True)
    mass = models.FloatField('mass of host star',blank=True,null=True)
    description = models.TextField()
    finderchart =  models.FileField('Finder chart',upload_to="finderchart", help_text='Image with a clearly marked up target position',blank=True)
    finderchart_tb =  models.FileField('Finder chart thumbnail',upload_to="finderchart/thumb", help_text='Image with a clearly marked up target position',blank=True)
    class Meta:
        verbose_name = u'transiting exoplanet target'
        db_table = u'dataexplorer_target'
    def __unicode__(self):
        return self.name
    
class Event(models.Model):
    name = models.CharField(blank=False, max_length=20, help_text='code, no spaces and no hyphens') # code to be used in URLs i.e. NO spaces
    title = models.CharField(blank=False, max_length=100) # Longer title which can be more wordy
    start = models.DateTimeField(null=True, blank=True, default=datetime.now)
    end = models.DateTimeField(null=True, blank=True, default=datetime.now)
    midpoint = models.DateTimeField(null=True, blank=True)
    numobs = models.IntegerField(blank=True, null=True,default=0)
    finder = models.IntegerField('id of finder chart source',blank=True)
    xpos = models.IntegerField('x pos on finder chart',blank=False,default=0)
    ypos = models.IntegerField('y pos on finder chart',blank=False,default=0)
    enabled = models.BooleanField(default=True,help_text='show this event on main site')
    illustration = models.FileField('illustration',upload_to="illustration", help_text='illustration for this event',blank=True)
    radius = models.IntegerField('aperture radius', blank=False, default=10)
    class Meta:
        verbose_name = u'transit event'
        db_table = u'dataexplorer_event'
    def __unicode__(self):
        return self.name
        
class DataSource(models.Model):
    fits = models.URLField(blank=True)
    image = models.URLField(blank=True, null=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    telescopeid = models.CharField(blank=True, max_length=100)
    event = models.ForeignKey(Event)
    target = models.ForeignKey(Target)
    max_x = models.IntegerField('max pixels (x)',blank=False)
    max_y = models.IntegerField('max pixels (y)',blank=False)
    class Meta:
        verbose_name = u'data source image'
        db_table = u'dataexplorer_datasource'
    def __unicode__(self):
        return self.timestamp.isoformat()
    def unixstamp(self):
        return timegm(self.timestamp.timetuple())+1e-6*self.timestamp.microsecond
    def isostamp(self):
        return self.timestamp.isoformat()
    
class CatSource(models.Model):
    name = models.CharField('object name',blank=False,max_length=50)
    data = models.ForeignKey(DataSource)
    xpos = models.IntegerField('x position on finder image', blank=True)
    ypos = models.IntegerField('y position on finder image', blank=True)
    catalogue = models.CharField('catalogue name',blank=False,max_length=20)
    final = models.BooleanField('include in final curve',default=True)
    class Meta:
        verbose_name = "catalogue source"
        db_table = u'dataexplorer_catsource'
    def __unicode__(self):
        return self.name
    
class DataCollection(models.Model):
    person = models.ForeignKey(User)
    planet = models.ForeignKey(Event)
    display = models.BooleanField(default=False)
    complete = models.BooleanField(default=False)
    calid = models.IntegerField('calibrator order',blank=False,null=False)
    source = models.ForeignKey(CatSource,blank=True, null=True)
    class Meta:
        verbose_name = u'data collection'
        db_table = u'dataexplorer_datacollection'
    def __unicode__(self):
        val = "%s" % self.planet.title
        return val
    
class Datapoint(models.Model):
    data = models.ForeignKey(DataSource)
    taken = models.DateTimeField(blank=True, default=datetime.now)
    value = models.FloatField(blank=True,null=True)  
    user = models.ForeignKey(User)
    pointtype = models.CharField(blank=False,max_length=1,choices=TYPECHOICE)
    coorder = models.ForeignKey(DataCollection,blank=True, null=True, help_text='point order')
    xpos = models.IntegerField('x position', blank=True)
    ypos = models.IntegerField('y position', blank=True)
    radius = models.IntegerField('aperture radius', blank=True)
    entrymode = models.CharField(blank=False,max_length=1,choices=ENTRYCHOICE,default='W')
    offset = models.FloatField('distance from source',blank=True)
    class Meta:
        verbose_name = u'data point'
        db_table = u'dataexplorer_datapoint'
    class Admin:
        list_display = ('event',)
        search_fields = ('user',)
    def __unicode__(self):
        return self.taken.isoformat()
            
class Decision(models.Model):
    source = models.ForeignKey(CatSource)
    value = models.CharField('decision',blank=False,max_length=1,choices=DECISIONS)
    person = models.ForeignKey(User)
    planet = models.ForeignKey(Event)
    taken = models.DateTimeField(default=datetime.now,blank=False)
    current = models.BooleanField(default=False)
    class Meta:
        verbose_name = u'lightcurve decision'
        db_table = u'dataexplorer_decision'
    def __unicode__(self):
        return self.source.name
        
class AverageSet(models.Model):
    planet = models.ForeignKey(Event)
    star = models.ForeignKey(CatSource,blank=True,null=True)
    values = models.TextField(null=True,blank=True)
    settype = models.CharField(blank=False,max_length=1,choices=TYPECHOICE)
    class Meta:
        verbose_name = u'combined lightcurve set'
    @property 
    def data(self):
        return [float(x) for x in self.values.split(';')]
    def __unicode__(self):
        return u"%s" % (self.planet.title)
        
class Badge(models.Model):
    name = models.CharField(blank=False, max_length=20, help_text='code, no spaces')
    description = models.CharField(blank=False, max_length=200, help_text='brief, publicly readable')
    image = models.FileField(upload_to="badge",blank=False)
    class Meta:
        verbose_name = u'badge'
        db_table = u'dataexplorer_badge'
    def __unicode__(self):
        return self.name

class Achievement(models.Model):
    person = models.ForeignKey(User)
    awarded = models.DateTimeField(blank=True, default=datetime.now)
    badge = models.ForeignKey(Badge)
    planet = models.ForeignKey(Event,blank=True, null=True,help_text='planet')
    class Meta:
        verbose_name = u'achievement unlocked'
        verbose_name_plural = u'achievements unlocked'
        db_table = u'dataexplorer_achievement'
    def __unicode__(self):
        if self.planet:
            t = "%s - %s - %s" % (self.badge.name,self.person.username,self.planet.title)
        else:
            t = "%s - %s" % (self.badge.name,self.person.username)
        return t
        
class Observer(models.Model):
    user = models.OneToOneField(User, unique=True,)
    tag = models.CharField(max_length=75, blank=False,default="LCO")
    organization = models.CharField(max_length=150, blank=True)
    dataexploreview = models.BooleanField("use web interface for dataexplorer", default=True)
    class Meta:
        db_table = u'observer'
        verbose_name = "observer"
    def __unicode__(self):
        return self.user.username


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
from django.conf.urls import include, url
from django.contrib.auth.views import login, logout
from .views import *

urlpatterns = [
    url(r'^$',index, name='index'),
    url(r'^account/login/$', login, {'template_name' :'login.html'}, name='login'),
    url(r'^account/logout/$', logout,{'template_name' :'logout.html'}, name='logout'),
    url(r'^account/register/$', register, name='register'),
    url(r'^account/$', editaccount, name='editaccount'),
    url(r'^profile/$',profile, name='profile'),
    url(r'^planets/$',target, name='target'),
    url(r'^fitsanalyse',fitsanalyse, name='fitsanalyse'),
    url(r'^test',tester, name='tester'),
    url(r'^briefing/read/$',read_manual_check, name='read_manual_check'),
    url(r'^briefing/$',briefing, name='briefing'),
    url(r'^comment/$',addcomment, name='addcomment'),
    url(r'^(?P<code>\w+)/view/$',addvalue, name='addvalue'),
    url(r'^(?P<code>\w+)/graph/update/$',updatedataset, name='updatedataset'),
    url(r'^(?P<code>\w+)/lightcurve/advanced/$',graphview, {'mode' : 'advanced','calid':None}, name='advanced-graph'),
    url(r'^(?P<code>\w+)/lightcurve/me/$',graphview, {'mode' : 'simple','calid':None}, name='my-graph'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/update/$',classifyupdate, name='classifyupdate'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/$',graphview, {'mode' : 'ave','calid':None}, name='average-graph'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/(?P<calid>\w+)/$',graphview, {'mode' : 'ave'}, name='calibrator-graph'),
    url(r'^(?P<code>\w+)/lightcurve/$',graphsuper,name='super-graph'),
    url(r'^(?P<code>\w+)/$',infoview, name='infoview'),
    url(r'^(?P<code>\w+)/data.(?P<format>\w+)',measurementsummary, name='measurementsummary'),
]'''
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
import json
from django.utils.encoding import smart_unicode
from django.core.serializers import serialize
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, ADDITION
from django.db.models import Count,Avg,Min,Max,Variance, Q, Sum
from django.contrib import messages
from django.db import connection
import urllib2
from xml.dom.minidom import parse
from math import sin,acos,fabs,sqrt
from numpy import *
from astropy.io import fits 
from datetime import datetime,timedelta
from calendar import timegm
from time import mktime
from math import floor,pi,pow
from itertools import chain
from numpy import array,nan_to_num

from django.contrib.auth.models import User
from agentex.models import Target, Event, Datapoint, DataSource, DataCollection,CatSource, Decision, Achievement, Badge, Observer, AverageSet
from agentex.models import decisions
from agentex.forms import DataEntryForm, RegisterForm, CommentForm,RegistrationEditForm
import agentex.dataset as ds

from django.conf import settings
from agentex.agentex_settings import planet_level

guestuser = 2

def home(request):
    ''' Render the Front page of citizen science portal '''
    return render_to_response('index.html',context_instance=RequestContext(request))

def index(request):  
    return render_to_response('agentex/index.html', context_instance=RequestContext(request))

def briefing(request):
    return render_to_response('agentex/briefing.html', context_instance=RequestContext(request))

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        # Check if User has already registered with same username or email address
        if form.is_valid():
            user = User.objects.create_user(form.cleaned_data['username'],form.cleaned_data['emailaddress'],form.cleaned_data['password'])
            user.first_name=form.cleaned_data['firstname']
            user.last_name=form.cleaned_data['lastname']
            user.save()
            o = Observer(user=user)
            o.save()
            messages.success(request,"Your account has been created")
            new_user = authenticate(username=form.cleaned_data['username'],
                                    password=form.cleaned_data['password'])
            login(request, new_user)         
            next = request.GET.get('next','')
            if next:
                print next
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect(reverse('portal'))
        else:
            return render_to_response("register.html",{'form': form},context_instance=RequestContext(request))
    else:
        return render_to_response("register.html",{'form': RegisterForm()},context_instance=RequestContext(request))
        
@login_required
def editaccount(request):
    p = personcheck(request)
    if request.method == 'POST':
        form = RegistrationEditForm(request.POST)
        # Check if User has already registered with same username or email address
        user = p.user
        if form.is_valid():
            f = form.cleaned_data
            print f
            user.first_name=f['firstname']
            user.last_name=f['lastname']
            user.email=f['emailaddress']
            password =f['password']
            if password:
                user.set_password(password)
            user.save()
            messages.success(request,"Your account has been updated")
        # data = {'firstname' : p.user.first_name,'lastname' : p.user.last_name,'emailaddress':p.user.email,'password':p.user.password,'username':p.user.username}
        return render_to_response("register.html",{'form': form,'edit':True},context_instance=RequestContext(request))
    else:
        form = RegistrationEditForm({'firstname' : p.user.first_name,'lastname' : p.user.last_name,'emailaddress':p.user.email,'password':p.user.password})
        return render_to_response("register.html",{'form': form,'edit':True},context_instance=RequestContext(request))    

@login_required
def profile(request):
    a = Achievement.objects.filter(person=request.user).order_by('badge')
    nomeas = Datapoint.objects.filter(user=request.user).values('taken').annotate(Count('taken')).count()
    noplanet = DataCollection.objects.filter(person=request.user).values('planet').annotate(Count('person')).count()
    completed = DataCollection.objects.values('planet').filter(person=request.user).annotate(Count('complete')).count()
    #ndecs = Decision.objects.filter(person=request.user,planet=d[0].event,current=True).count()
    badgelist = Badge.objects.exclude(id__in=[b.badge.id for b in a]).order_by('name')
    return render_to_response("agentex/profile.html",{'unlocked':a,'badges':badgelist,'planets':noplanet,'measurements':nomeas,'completed':completed},context_instance=RequestContext(request))

#@login_required
def target(request):  
    data = []
    events = Event.objects.filter(enabled=True)
    for e in events:
        if (request.user.is_authenticated()):
            person = request.user
            completed = Datapoint.objects.filter(user=person, data__event__name=e,pointtype='S').count()
        else:
            person = guestuser
            completed = 0
        points =Datapoint.objects.filter(user=person,pointtype='S')
        try:
            level = planet_level[e.name]
        except:
            level = None
        line = {'event':e,'points':points,'completed':completed,'level':level}
        data.append(line)
    return render_to_response('agentex/target.html', {'data':data},context_instance=RequestContext(request))

@login_required
def addvalue(request,code):
    form = DataEntryForm()
    if (request.user.is_authenticated()):
        if request.user.username == 'admin':
            superuser = True
            sudo = request.GET.get('sudo','')
            if sudo:
                person = User.objects.get(id=sudo)
            else:
                person = request.user
        else:
            person = request.user
            superuser = False
    o = Observer.objects.filter(user=person)
    progress = checkprogress(person,code)
    if (progress['done'] >= progress['total']):
        dcolls = DataCollection.objects.filter(person=person,planet__name=code)
        dcolls.update(complete=True)
    ###### Has the user selected to use the web interface
    ###### Default for anonymous is always web interface
    if (person != guestuser):
        try:
            webin = o[0].dataexploreview
        except:
            webin = True
    else:
        webin = True
    least_coords = leastmeasured(code)
    if (request.POST):
    ####### Form data has been submitted
        x = []
        y = []
        nocals = request.POST.get('calibrators','1')
        setting = request.POST.get('entrytype','')
        # Only update the user's preference if they change it
        if (setting == 'manual' and o[0].dataexploreview == True):
            o.update(dataexploreview=False)
            messages.success(request, "Setting changed to use manual view")
            entrymode = 'M'
        elif (setting == 'dataexplorer' and o[0].dataexploreview == False):
            o.update(dataexploreview=True)
            messages.success(request, "Setting changed to use web view")
            entrymode = 'W'
        else:
            entrymode = 'N'
        id = request.POST.get('dataid','')
        form = DataEntryForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            ind = {'source':'S','bg':'B'}
            reduced = 0
            update = request.POST.get('update','')
            counts = list()
            for i in ind:
                value = float(cd[i+'counts'])
                x.append(cd[i+'xpos'])
                y.append(cd[i+'ypos'])
                counts.append(value)
            for vari in range(1,int(nocals)+1):
                cali = str(vari)
                value = request.POST.get('cal'+cali+'counts','')
                x.append(request.POST.get('cal'+cali+'xpos',''))
                y.append(request.POST.get('cal'+cali+'ypos',' '))
                counts.append(float(value))
            pointsum = {'bg' :  '%.2f' % counts[0], 'sc' : '%.2f' % counts[1], 'cal' : counts[2:]}
            if (len(x) < 3 or len(y) < 3):
                messages.warning(request,'Please submit calibration, blank sky and source apertures.')
                url = reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name])
                return HttpResponseRedirect(url)
            x = map(float,x)
            y = map(float,y)
            coords = zip(x,y)
            dataid = request.POST.get('dataid','')
            resp = savemeasurement(person,pointsum,coords,dataid,entrymode)
            messages.add_message(request, resp['code'], resp['msg'])
            if webin == False:
                url = "%s?%s" % (reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name]),"input=manual")
            else:
                url = reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name])
             #messages.success(request, "Measurement successfully added")
            return HttpResponseRedirect(url)
        else:
            return render_to_response('agentex/dataentry.html', {'data':DataSource.objects.get(id=id),'form':form,'data_url':settings.DATA_URL}, context_instance=RequestContext(request))
    else:
        nextcal = request.GET.get('next',False)
        ############ This condition is active when a user edits the frame
        # Find the data sources for the given code
        source = DataSource.objects.filter(event__name=code)
        length = source.count()
        # Pull out data user has viewed and exclude them from the list of possible candidates
        ds = Datapoint.objects.values_list('data',flat=True).filter(data__event__name=code,user=person,pointtype='S')
        input = request.GET.get('input',False)
        id = request.GET.get('dataid',False)
        # If an ID is specified return the frame, as long as the person has made measurements of it
        if id:
            dnext = False
            #### If anonymous user tell them they cannot edit points
            if person == guestuser:
                messages.warning(request,'You cannot edit points unless you are logged in')
                try:
                    url = reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name])
                    return HttpResponseRedirect(url)
                except:
                    raise Http404
            mycalibs = []
            ##### The page is being displayed with data for editing
            points = Datapoint.objects.filter(data__id=id,user=person)
            if nextcal=='cal':
                print "*******"
                dp = Datapoint.objects.filter(pointtype='S',user=person,data__id=id)
                dd = dp[0].data.timestamp
                ds = Datapoint.objects.filter(pointtype='S',user=person,data__timestamp__gt=dd).order_by('data__timestamp')
                if ds.count() > 0:
                    dnext = ds[0].data
            d = DataSource.objects.filter(id=id)[0]
            otherpoints = Datapoint.objects.filter(~Q(user=person),pointtype='C',data=d)
            cals = Datapoint.objects.values_list('xpos','ypos','radius').filter(data=d,pointtype='C').order_by('coorder__calid')
            calibs = []
            if cals:
                for c in cals:
                    calibs.append({'x' : int(c[0]) , 'y' : int(c[1]), 'r' : int(c[2])})
            source = points.filter(pointtype='S')[:1]
            bg = points.filter(pointtype='B')[:1]
            #### If there are no results, the person is hacking the query string. Return a fresh frame
            if (source.count() == 0 or bg.count() == 0):
                url = reverse('agentex.views.addvalue',args= [code])
                return HttpResponseRedirect(url)
            cal = points.filter(pointtype='C').order_by('coorder__calid')
            for c in cal:
                line = {'x' :c.xpos,'y' : c.ypos}
                mycalibs.append(line)
            ### If more cals have been placed on other frames add these to this frame
            max_cal = Datapoint.objects.filter(pointtype='C',user=person).aggregate(max=Max('coorder__calid'))['max']
            if max_cal+1 > cal.count():
                for order in range(cal.count(),max_cal+1):
                    dp = Datapoint.objects.filter(pointtype='C',user=person,coorder__calid=order,data__event__name=code)
                    if dp.count() > 0:
                        line = {'x': dp[0].xpos, 'y':dp[0].ypos}
                        # Add to the mycalibs array
                        mycalibs.append(line)
            coords = { 'source': {'x' :source[0].xpos,'y' : source[0].ypos},
                     'cal'  : mycalibs,
                     'bg'  : {'x' :bg[0].xpos,'y' : bg[0].ypos},
                     'radius' : source[0].radius,
                     'id'  : id,
                     'numcals' : len(mycalibs),
                     }
            messages.info(request, "Updating measurement")
            return render_to_response('agentex/dataentry.html',{'data':d,
                                                                    'next':dnext,
                                                                    'points':coords,
                                                                    'update':True,
                                                                    'webinput':webin,
                                                                    'progress':progress,
                                                                    'form':form,
                                                                    'calibrators':calibs,
                                                                    'least_data':least_coords,
                                                                    'data_url':settings.DATA_URL},
                                    context_instance=RequestContext(request))                             
        else:
            ######## User is being given a new frame not editing data  
            complete = 0
            if  (progress['done'] >= progress['total'] and person != guestuser):
                ####### No new data can be provided because the user has come to the end
                complete = 1
                numplanets = DataCollection.objects.values('planet').filter(person=person,complete=True).annotate(Count('complete')).count()
                e = Event.objects.filter(name=code)[0]
                resp = achievementscheck(person,e,0,0,0,0,numplanets)

                msg = '<br />'
                for item in resp:
                    if messages.SUCCESS == item['code'] :
                        msg += "<img src=\""+STATIC_URL+item['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />"
                        messages.success(request,msg)
                
                return HttpResponseRedirect(reverse('my-graph',args=[code]))

                return render_to_response('agentex/dataentry.html',
                                        {'event': e,
                                        'complete':complete,
                                        'progress':progress,
                                        'points':Datapoint.objects.filter(user=person,pointtype='S',data__event=e).order_by('data__timestamp'),
                                        'data_url':settings.DATA_URL,
                                        'numplanets':numplanets,},
                                        context_instance=RequestContext(request))            
            else:
                planet = Event.objects.get(name=code)
                mylist = Datapoint.objects.filter(user=person,pointtype='S',data__event=planet).values_list('data',flat=True)
                print mylist
                ### if person does not have a DataCollection it is their first measurement
                if (DataCollection.objects.filter(planet=planet,person=person).count() == 0):
                    d = DataSource.objects.filter(event=planet,id=planet.finder)[0]
                    did = d.id
                    try:
                        dold = d.id
                        first = True   
                    except:
                        messages.error(request,"Finderchart cannot be found")
                        raise Http404    
                elif  person == guestuser:
                    d = DataSource.objects.filter(event=planet).annotate(count=Count('datapoint')).order_by('-count')[0]
                    did = d.id
                    dold = d.id
                    first = True
                else:
                    try:
                        source_rank = DataSource.objects.filter(event=planet ).annotate(count=Count('datapoint') ).values_list('id','count').order_by('-count')  
                        available = [x for x in source_rank if x[0] not in list(mylist)]
                        dold = Datapoint.objects.values_list('data__id',flat=True).filter(user=person,data__event=planet,pointtype='C').annotate(max =Max('coorder__calid')).order_by('-max','-taken')[0]
                    # Find position in set of DataSources
                        d = available[0]
                        did = d[0]
                        first = False
                    except Exception,e:
                        print e
                        messages.error(request,"User has a data collection but no points!")
                        raise Http404
                cals = Datapoint.objects.values_list('xpos','ypos').filter(data=dold,pointtype='C',user=person).order_by('coorder__calid')
                calibs = []
                if cals:
                    for c in cals:
                        calibs.append({'x' : int(c[0]) , 'y' : int(c[1])})
                otherpoints = Datapoint.objects.filter(~Q(user=person),pointtype='C',data__id=did)
                othercals = []
                if otherpoints:
                    for c in otherpoints:
                        othercals.append({'x' : int(c.xpos) , 'y' : int(c.ypos),'r':int(c.radius)})
                prev = Datapoint.objects.filter(user=person,data=dold).order_by('coorder__calid')
                if first == False:
                    coords = { 'source': {'x' :prev.filter(pointtype='S')[0].xpos,'y' : prev.filter(pointtype='S')[0].ypos},
                             'bg'  : {'x' :prev.filter(pointtype='B')[0].xpos,'y' : prev.filter(pointtype='B')[0].ypos},
                             'cal'  : calibs ,
                             'id'  : dold,
                             'radius' : planet.radius
                             }
                else:
                    coords = False
                if person == guestuser:
                    progress = {'percent'   : "0",
                                'done'      : 0,
                                'total'     : n_sources,}
                return render_to_response('agentex/dataentry.html',
                                        {'data':DataSource.objects.get(id=did),
                                        'complete':complete,
                                        'update':False,
                                        'webinput':webin,
                                        'progress':progress,
                                        'form':form,
                                        'calibrators':othercals,
                                        'points':coords,
                                        'least_data':least_coords,
                                        'data_url':settings.DATA_URL},
                                        context_instance=RequestContext(request))        


def savemeasurement(person,pointsum,coords,dataid,entrymode):
    # Only update the user's preference if they change it
    o = Observer.objects.filter(user=person)
    try:
        if (entrymode == 'manual' and o[0].dataexploreview == True):
            o.update(dataexploreview=False)
            messages.success(request, "Setting changed to use manual view")
        elif (entrymode == 'dataexplorer' and o[0].dataexploreview == False):
            o.update(dataexploreview=True)
            messages.success(request, "Setting changed to use web view")
    except:
        print "Having problems with"
    mode = {'dataexplorer':'W','manual':'M'}
    pointtype = {'sc':'S','bg':'B'}
    d = DataSource.objects.filter(id=int(dataid))
    s_x = float(coords[1][0])
    s_y = float(coords[1][1])
    if d[0].id == d[0].event.finder:
        xvar = abs(s_x - d[0].event.xpos)
        yvar = abs(s_y - d[0].event.ypos)
        if (xvar > 3 or yvar > 3):
          # Remove previous values for this point
          return {'msg': 'Target marker not correctly aligned', 'code': messages.ERROR}
    xmean = 0
    ymean = 0 
    # Remove previous values for this point
    oldpoints = Datapoint.objects.filter(data=d[0],user=person)
    oldpoints.delete()
    numpoints = Datapoint.objects.filter(data__event=d[0].event,user=person).count()
    datestamp = datetime.now()
    reduced = 0
    calave = 0.
    error = ''
    ### Add a datacollection for the current user
    r = d[0].event.radius
    for k,value in pointtype.iteritems():
        # Background and source
        data = Datapoint(user=person,
                            pointtype = value,
                            data=d[0], 
                            radius=r,
                            entrymode=mode[entrymode],)
        if k == 'sc':
            coord = coords[1]
            data.offset = 0
        elif k == 'bg':
            coord = coords[0]
            data.offset = int(sqrt((s_x - float(coord[0]))**2 + (s_y - float(coord[1]))**2))
        data.value= float(pointsum[k])
        data.xpos = int(float(coord[0]))
        data.ypos = int(float(coord[1]))
        data.taken=datestamp
        try:
            data.save()
        except:
            return {'msg': 'Error saving data point', 'code': messages.ERROR}
    # Slice coord data so we only have calibration stars
    coord = coords[2:]
    basiccoord = array(coord[:3])
    nocals = len(coord)
    sc_cal = float(pointsum['sc']) - float(pointsum['bg'])
    # Find out if means have been calculated already, if not do it for the source
    # This step can only happen if we are not at the finder frame 
    if numpoints != 0 and d[0].event.finder != d[0].id:
        xmean, ymean = measure_offset(d,person,basiccoord)
        # check the source is within this tolerance too
        sc_xpos = d[0].event.xpos
        sc_ypos = d[0].event.ypos
        xvar = abs(abs(sc_xpos-s_x)-abs(xmean))
        yvar = abs(abs(sc_ypos-s_y)-abs(ymean))
        if (xvar > 5 or yvar > 5):
            # Remove previous values for this point
            oldpoints = Datapoint.objects.filter(data__id=int(dataid),user=person)
            oldpoints.delete()
            return {'msg': 'Target marker not correctly aligned', 'code': messages.ERROR}
    for i,value in enumerate(pointsum['cal']):
        xpos = int(float(coord[i][0]))
        ypos = int(float(coord[i][1]))
        newcoord = coord
        nocolls = DataCollection.objects.filter(planet=d[0].event,person=person,calid=i).count()
        if (nocolls == 0 and person != guestuser):
            ## Find closest catalogue sources
            if i > 2:
                # Add more datacollections if i is > 2 i.e. after basic 3 have been entered
                cats = CatSource.objects.filter(xpos__lt=xpos-xmean+5,ypos__lt=ypos-ymean+5,xpos__gt=xpos-xmean-5,ypos__gt=ypos-ymean-5,data__event=d[0].event)
            else:
                cats = CatSource.objects.filter(xpos__lt=xpos+5,ypos__lt=ypos+5,xpos__gt=xpos-5,ypos__gt=ypos-5,data__event=d[0].event)
            if cats:
                dcoll = DataCollection(person=person,planet=d[0].event,complete=False,calid=i,source=cats[0])
            else:
                dcoll = DataCollection(person=person,planet=d[0].event,complete=False,calid=i)
            dcoll.display = True
            dcoll.save()
        else:
            dcoll = DataCollection.objects.filter(person=person,planet=d[0].event,calid=i)[0]
        data = Datapoint(user=person,
                            pointtype = 'C',
                            data=d[0], 
                            radius=r,
                            entrymode=mode[entrymode])
        data.value= float(value)
        data.xpos = xpos
        data.ypos = ypos
        data.offset = int(sqrt((s_x - float(coord[i][0]))**2 + (s_y - float(coord[i][1]))**2))
        data.taken=datestamp
        data.coorder = dcoll
        try:
            data.save()
        except:
            return {'msg': 'Error saving', 'code': messages.ERROR}
        calave = calave +sc_cal/(value - float(pointsum['bg']))/float(nocals)
    else:
        #resp = achievementcheck(person,d[0].event,nocals,'calibrator')
        #nomeas = Datapoint.objects.filter(data__event__name=d[0].event,user=person).values('taken').annotate(Count('taken')).count()
        nomeas = Datapoint.objects.filter(user=person).values('taken').annotate(Count('taken')).count()
        noplanet = DataCollection.objects.filter(person=person).values('planet').annotate(Count('person')).count()
        ndecs = Decision.objects.filter(person=person,current=True).count() # filter: ,planet=d[0].event
        unlock = False
        nunlock = 0
        resp = achievementscheck(person,d[0].event,nomeas,noplanet,nocals,ndecs,0)
        msg = '<br />'
        for item in resp:
            if messages.SUCCESS == item['code'] :
                msg += "<img src=\""+STATIC_URL+item['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />"
                unlock = True
                nunlock += 1

        if unlock :
            if nunlock > 1 : return {'msg': 'Achievements unlocked'+msg, 'code': messages.SUCCESS}
            else : return {'msg': 'Achievement unlocked'+msg, 'code': messages.SUCCESS}
        return {'msg': 'Measurements saved', 'code': messages.SUCCESS}

def measure_offset(d,person,basiccoord):
    # Find the likely offset of this new calibrator compared to the basic ones and find any sources within 5 pixel radius search
    finderid = d[0].event.finder
    finderdp = Datapoint.objects.values_list('xpos','ypos').filter(user=person,data__id=finderid,pointtype='C',coorder__calid__lt=3).order_by('coorder__calid')
    finder = basiccoord - array(finderdp)
    t = transpose(finder)
    xmean = mean(t[0])
    ymean = mean(t[1])
    return xmean,ymean



def read_manual_check(request):
	if (request.POST.get('read_manual','')=='true' and request.user.is_authenticated()):
		o = personcheck(request)
		resp = achievementunlock(o.user,None,'manual')
		if messages.SUCCESS == resp['code'] :
			messages.add_message(request, messages.SUCCESS, "Achievement unlocked<br /><img src=\""+STATIC_URL+resp['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />")
		
	return HttpResponseRedirect(reverse('agentex.views.target'))
		


# measurements, planets, calibrators descisions
def achievementscheck(person,planet,nmeas,nplan,ncals,ndcsn,ncomp):
    resp = []
    if person.id!=guestuser:
        if nmeas == 1 : resp.append(achievementunlock(person,planet,'measurement_1'))
        if nmeas == 5 : resp.append(achievementunlock(person,planet,'measurement_5'))
        if nmeas == 10 : resp.append(achievementunlock(person,planet,'measurement_10'))
        if nmeas == 25 : resp.append(achievementunlock(person,planet,'measurement_25'))
        if nmeas == 50 : resp.append(achievementunlock(person,planet,'measurement_50'))
        if nmeas == 100 : resp.append(achievementunlock(person,planet,'measurement_100'))
        if nmeas == 250 : resp.append(achievementunlock(person,planet,'measurement_250'))
        if nmeas == 500 : resp.append(achievementunlock(person,planet,'measurement_500'))
        if nmeas == 1000 : resp.append(achievementunlock(person,planet,'measurement_1000'))
        if nmeas == 1500 : resp.append(achievementunlock(person,planet,'measurement_1500'))
        if nmeas == 2000 : resp.append(achievementunlock(person,planet,'measurement_2000'))
        if ncals >= 3 : resp.append(achievementunlock(person,planet,'calibrator_3'))
        if ncals >= 5 : resp.append(achievementunlock(person,planet,'calibrator_5'))
        if ncals >= 10 : resp.append(achievementunlock(person,planet,'calibrator_10'))
        if ncals >= 15 : resp.append(achievementunlock(person,planet,'calibrator_15'))
        if ncals >= 25 : resp.append(achievementunlock(person,planet,'calibrator_25'))
        if nplan == 1 : resp.append(achievementunlock(person,planet,'planet_1'))
        if nplan == 2 : resp.append(achievementunlock(person,planet,'planet_2'))
        if nplan == 3 : resp.append(achievementunlock(person,planet,'planet_3'))
        if nplan == 4 : resp.append(achievementunlock(person,planet,'planet_4'))
        if nplan == 5 : resp.append(achievementunlock(person,planet,'planet_5'))
        if nplan == 6 : resp.append(achievementunlock(person,planet,'planet_6'))
        if nplan == 7 : resp.append(achievementunlock(person,planet,'planet_7'))
        if nplan == 8 : resp.append(achievementunlock(person,planet,'planet_8'))
        if nplan == 9 : resp.append(achievementunlock(person,planet,'planet_9'))
        if ndcsn >= 3 : resp.append(achievementunlock(person,planet,'lightcurve_1star'))
        if ndcsn >= 10 : resp.append(achievementunlock(person,planet,'lightcurve_2star'))
        if ncomp == 1 : resp.append(achievementunlock(person,planet,'completed_1'))
        if ncomp == 2 : resp.append(achievementunlock(person,planet,'completed_2'))
        if ncomp == 3 : resp.append(achievementunlock(person,planet,'completed_3'))
        if ncomp == 4 : resp.append(achievementunlock(person,planet,'completed_4'))
        if ncomp == 5 : resp.append(achievementunlock(person,planet,'completed_5'))
        if ncomp == 6 : resp.append(achievementunlock(person,planet,'completed_6'))
        if ncomp == 7 : resp.append(achievementunlock(person,planet,'completed_7'))
        if ncomp == 8 : resp.append(achievementunlock(person,planet,'completed_8'))
        if ncomp == 9 : resp.append(achievementunlock(person,planet,'completed_9'))
    
    return resp


def achievementunlock(person,planet,typea):
    # Check what badges user has to see if they deserve more
    # The planet will simply be to record where they got this achievement
    achs = Achievement.objects.filter(person=person) #,planet=planet
    badge =  Badge.objects.filter(name=typea)
    if badge.count() == 0:
        return {'msg' : 'Wrong badge code', 'code': messages.ERROR}
    if achs.filter(badge=badge).count() == 0:
        newa = Achievement(badge=badge[0],planet=planet,person=person)	# ,planet=planet
        try:
            newa.save()
            LogEntry.objects.log_action(
                user_id         = person.id, 
                content_type_id = ContentType.objects.get_for_model(newa).pk,
                object_id       = newa.pk,
                object_repr     = smart_unicode(newa), 
                action_flag     = ADDITION,
                change_message  = 'Achievement automatically unlocked'
            )
            return {'msg': 'Achievement unlocked', 'image':"%s" % badge[0].image, 'code': messages.SUCCESS }
        except:
            return {'msg' : 'Achievement save error', 'image':"%s" % badge[0].image, 'code': messages.ERROR }
    else:
        return {'msg' : 'Already has this badge', 'image': '', 'code': messages.WARNING }

def classifyupdate(request,code):
    if (request.POST):
        resp = addvalidset(request,code)
        if resp:
            msg = {'update':False}
        else:
            msg = {'update': True}
    else:
        msg = {'update':False}
    #messages.warning(request,msg)
    return HttpResponse(json.dumps(msg),mimetype='application/javascript')

def updatedataset(request,code):
    formdata = request.POST
    option = request.GET.get('mode','')
    if (formdata and option == 'display'):
        resp = updatedisplay(request,code)
        url = reverse('my-graph',args= [code])
        if resp:
            messages.warning(request,'Your preferences have not been saved.')
        else:
            messages.success(request,'Your display setting has been saved.')
    elif (formdata and option == 'valid'):
        resp = addvalidset(request,code)
        if resp:
            messages.warning(request,'None of your lightcurves have been saved.')
        else:
            messages.success(request,'Your selected classification has been saved.')
        url = reverse('average-graph',args= [code])
    else:
        messages.warning(request,'Nothing to save')
    return HttpResponseRedirect(url)

def updatedisplay(request,code):
    # Wipe all the validations for user and event
    o = personcheck(request)
    dc = DataCollection.objects.filter(person=o.user,planet=Event.objects.get(name=code),complete=True)
    dc.update(display = False)
    empty = True
    formdata = request.POST
    for i,val in formdata.items():
        if i[4:] == val:
            # Add validations back one by one
            col = dc.filter(calid=val)
            col.update(display= True)
            empty = False
    return empty

def addvalidset(request,code):
    o = personcheck(request)
    calid = request.POST.get('calid','')
    choice1 = request.POST.get('choice1','')
    choice2 = request.POST.get('choice2','')
    point = DataCollection.objects.filter(person=o.user,calid=calid,planet__name=code)
    planet = Event.objects.filter(name=code)[0]
    if choice1 and point and calid:
        value = decisions[choice1]
        source = point[0].source
        old = Decision.objects.filter(person=o.user,planet=planet,source=source)
        old.delete()
        decision1 = Decision(source=source,
                        value=value,
                        person=o.user,
                        planet=planet)
        
        if choice2:
            value2 = decisions[choice2]
            decision2 = Decision(source=source,
                            value=value2,
                            person=o.user,
                            planet=planet,
                            current=True)
            decision2.save()
        else:
            decision1.current = True
        decision1.save()
        return False
    else:
        return True
        
@login_required
def my_data(o,code):
    data = []
    sources = DataSource.objects.filter(event__name=code).order_by('timestamp')
    points  = Datapoint.objects.filter(data__event__name=code,user=o.user)
    for s in sources:
        ps = points.filter(data=s)
        myp = ps.filter(pointtype='S')
        try:
            mypoint = '%f' % myp[0].value
        except:
            mypoint = 'null'
        cals = ps.filter(pointtype='C').values_list('value',flat=True).order_by('coorder')
        line = {
                'id'        : "%i" % s.id,
                'date'      : s.timestamp.isoformat(" "),
                'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                'data'      : { 'source' : list(ps.filter(pointtype='S').values_list('value',flat=True)),
                                'background' :  list(ps.filter(pointtype='B').values_list('value',flat=True)),
                                'calibrator' :  list(cals),
                            },
                }
        data.append(line)
    return data,points
    
def calibrator_data(calid,code):
    data = []
    sources, times = zip(*DataSource.objects.filter(event__name=code).values_list('id','timestamp').order_by('timestamp'))
    points  = Datapoint.objects.filter(data__in=sources)
    #points.filter(pointtype='C').values('data__id','user','value')
    people = Decision.objects.filter(source__id=calid,planet__name=code,value='D',current=True).values_list('person__username',flat=True).distinct()
    norm = dict((key,0) for key in sources)
    for pid in people:
        cal = []
        sc = dict(points.filter(user__username=pid,pointtype='S').values_list('data__id','value'))
        bg = dict(points.filter(user__username=pid,pointtype='B').values_list('data__id','value'))
        c = dict(points.filter(user__username=pid,pointtype='C',coorder__source__id=calid).values_list('data__id','value'))
        sc_norm = dict(norm.items() + sc.items())
        bg_norm = dict(norm.items() + bg.items())
        c_norm = dict(norm.items() + c.items())
        #print sc_norm,bg_norm,c_norm
        for v in sources:
            try:
                cal.append((sc_norm[v]- bg_norm[v])/(c_norm[v] - bg_norm[v]))
            except:
                cal.append(0)
        data.append(cal)
    return data,[timegm(s.timetuple())+1e-6*s.microsecond for s in times],list(people)
        
@login_required  
def graphview(request,code,mode,calid):
    #measurement = Datapoint.objects.filter(taken=date,data__event__name=code)
    #calibrate(measurement)
    o = personcheck(request)
    progress = checkprogress(o.user,code)
    n = 0
    if mode == 'simple':
        d1 = ds.Dataset(code,o.user.username)
        data,points = d1.my_data()#my_data(o,code)
        dc = DataCollection.objects.filter(person=o.user,planet=d1.planet)
        if dc.count() > n:
            n = range(0,dc.count())
            cats = []
            for order in n:
                try:
                    ## Sometimes the sequence of calibrators is not continuous 0..n  -- BUG
                    dc0 = dc.filter(calid=order)[0]
                    c = points.filter(pointtype='C',coorder=dc0)[:1]
                    valid = c[0].coorder.display
                    coll = {'order' : order,
                            'name'  : c[0].coorder.source,
                            'valid' : valid,
                            }
                    cats.append(coll)
                except:
                    pass
        else:
            cats = None
        classif = classified(o,code)
        return render_to_response('agentex/graph_flot.html', {'event':d1.planet,
                                                                'data':data,
                                                                'n':n,
                                                                'sources':cats,
                                                                'classified':classif,
                                                                'progress' : progress,
                                                                'target':DataSource.objects.filter(event__name=code)[0].target}, 
                                                                context_instance=RequestContext(request))
    elif mode == 'ave':
        data = []
        # get and restructure the average data JS can read it nicely
        now = datetime.now()
        cals,normcals,sb,bg,dates,stamps,ids,cats = photometry(code,o.user,progress) 
        numcals = len(normcals)
        print normcals
        for i,id in enumerate(ids):
            #mycalibs = []
            calibs = []
            normcalibs = []
            for j in range(0,numcals):
                calibs.append([cals[j][i],cats[j]['order']])
                #mycalibs.append(mycals[j][i])
                normcalibs.append(normcals[j][i])
            line = {
                    'id'        : id,
                    'date'      : dates[i],
                    'datestamp' : stamps[i],
                    'data'      : { 'source' : sb[i],
                                    'background' :  bg[i],
                                    'calibration' :  normcalibs,
                                    #'mycals'     :  mycalibs,
                                    'calibrator' : calibs,
                                },
                    }
            data.append(line)
        planet = Event.objects.filter(name=code)[0]        
        ### Make sure person gets a different calibrator (that they haven't classified) after each POST
        currentcal = None
        dec = Decision.objects.values('source__name').filter(person=o.user,planet__name=code,value__in=['D','N','B','P','R','S'],current=True).annotate(count=Count('source')).order_by('count')
        if calid:
            for cat in cats:
                # Which calibrator is being requested, if one is requested
                if int(cat['order']) == int(calid)-1:
                    currentcal = {'order': cat['order'], 'sourcename' : "%s" % cat['sourcename'],'total':len(cats),'progress':dec.count()}  
        else:
            if dec.count() == 0 and cats:
                currentcal = {'order': cats[0]['order'], 'sourcename' : "%s" % cats[0]['sourcename'], 'total':len(cats),'progress':dec.count()}
            elif dec.count() < len(cats):
                tmp, declist = zip(*dec.values_list('count','source__name'))
                for cat in cats:
                    if (cat['sourcename']  not in declist):
                        currentcal = {'order': cat['order'], 'sourcename' : "%s" % cat['sourcename'], 'total':len(cats),'progress':dec.count()}
            elif dec:
                for cat in cats:
                    if cat['sourcename'] == dec[0]['source__name']:
                        currentcal = {'order': cat['order'], 'sourcename' : "%s" % cat['sourcename'], 'total':len(cats),'progress':dec.count()}
        if currentcal:
            ## Send decision person made last time they were here
            mychoice = Decision.objects.values('value').filter(person=o.user,planet__name=code,value__in=['D','N','B','P','R'],source__name=currentcal['sourcename'])
            if mychoice:
                choice = mychoice.latest('taken')
                rev_dec = dict((v,k) for k, v in decisions.iteritems())
                prev = rev_dec[choice['value']]
            else:
                prev = None
            # How many have I classified
        elif len(cats) == 0 and calid == None:
            prev = None
        else:
            messages.error(request,'The lightcurve using the selected calibrator is not complete')
            return HttpResponseRedirect(reverse('average-graph',args=[planet.name]))
        #print datetime.now() - now
        classif = classified(o,code)
        resp = achievementscheck(o.user,planet,0,0,0,len(cats),0)
        unlock = False
        nunlock = 0
        msg = '<br />'
        
        for item in resp:
            if messages.SUCCESS == item['code'] :
                msg += "<img src=\""+STATIC_URL+item['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />"
                unlock = True
                nunlock += 1

        if unlock :
            if nunlock > 1 : msg = 'Achievements unlocked'+msg
            else : msg = 'Achievement unlocked'+msg
            messages.add_message(request, messages.SUCCESS, msg)
        print classif
        return render_to_response('agentex/graph_average.html', {'event': planet,
                                                                'data':data,
                                                                'sources':cats,
                                                                'cals':json.dumps(cats),
                                                                'calid': currentcal,
                                                                'prevchoice' : prev,
                                                                'classified':classif,
                                                                'progress' : progress,
                                                                'target':DataSource.objects.filter(event=planet)[0].target},
                                                                context_instance=RequestContext(request))
            
    elif mode == 'advanced':
        opt = {'S' :'source','C':'calibrator','B':'sky'}
        if 'dataid' in request.GET:
            dataid = request.GET.get('dataid','')
        else:    
            dataid = Datapoint.objects.filter(user=o[0].user).order_by('taken')[0].data.id
        try:
            s = DataSource.objects.filter(id=dataid)[0]
        except:
            raise Http404  
        ps  = Datapoint.objects.filter(~Q(pointtype = 'R'),data = s).order_by('-pointtype')
        datalist = [{'mine': ismypoint(o[0],dp.user),'x' : dp.xpos,'y' : dp.ypos, 'r' : dp.radius, 'value' : "%.0f" % dp.value,'type':opt[dp.pointtype]} for dp in ps]
        line = {
                'id'        : "%i" % s.id,
                'date'      : s.timestamp.isoformat(" "),
                'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                'data'      : datalist,
                }
        return render_to_response('agentex/graph_advanced.html', {'event':Event.objects.filter(name=code)[0],
                                                                        'framedata':line,
                                                                        'target':DataSource.objects.filter(event__name=code)[0].target,
                                                                        'progress' : progress}, context_instance=RequestContext(request))

def graphsuper(request,code):
    # Construct the supercalibrator lightcurve
    ds1 = ds.Dataset(planetid=code,userid=request.user.username)
    data = ds1.final()
    ###### Setting nodata to True and not showing each person their own data, but just for now
    return render_to_response('agentex/graph_super.html', {'event':ds1.planet,
                                                                'data':data,
                                                                'numsuper':13,
                                                                'target':ds1.target,
                                                                'nodata' : True}, context_instance=RequestContext(request))

def infoview(request,code):
    ds = DataSource.objects.filter(event__name=code)[:1]
    
    if request.user.is_authenticated():
        person = personcheck(request)
        progress = checkprogress(person,code)
    else:
        progress = None
    print progress
    try:
        data = ds[0]
    except:
        raise Http404
    return render_to_response('agentex/info.html', {'object' : data, 'progress' : progress}, context_instance=RequestContext(request))
    
def fitsanalyse(request):
    now = datetime.now()
    if (request.user.is_authenticated()):
        person=request.user
    else:
        person = User.objects.filter(id=guestuser)[0]
    # Flag poor quality result
    #print datetime.now() - now
    flag = ''
    # Extract variables passed from the image
    # Order of variables sent is 'bg','source','cal1','cal2'...
    x = request.POST.get('x','').split(',')
    y = request.POST.get('y','').split(',')
    if (len(x) < 3 or len(y) < 3):
        response = {'message' : 'Please submit calibration, blank sky and source apertures.'}
        return HttpResponse(json.dumps(response),mimetype='application/javascript')
    x = map(float,x)
    y = map(float,y)
    coords = zip(x,y)
    dataid = request.POST.get('dataid','')
    linex = list()
    liney = list()
    counts = list()

    ###########
    # Validate the input data
    # Check radius is less than a max size so the server does not have too much load
    # ***** No longer used as we fix radius from the outset ****
    #if r >= 70:
    #    response = {'message' : 'Apertures are too large. Please make your circles smaller'}
    #    return HttpResponse(json.dumps(response),mimetype='application/javascript')
    # Check all apertures are away from frame edge
    d = DataSource.objects.filter(id=int(dataid))[:1]
    r = d[0].event.radius
    for co in coords:
        xi = co[0]
        yi = co[1]
        if (xi-r < 0 or xi+r >= d[0].max_x or yi-r < 0 or yi+r > d[0].max_y ):
            response = {'message' : 'Please make sure your circles are fully within the image'}
            return HttpResponse(json.dumps(response),mimetype='application/javascript')

    #print datetime.now() - now
    # Grab a fits file
    dfile = "%s%s" % (settings.DATA_LOCATION,d[0].fits)
    #print dfile
    dc = fits.getdata(dfile,header=False)
    #print datetime.now() - now
    
    # Find all the pixels a radial distance r from x0,y0
    for co in coords:
        x0 = int(floor(co[0]))
        y0 = int(floor(co[1]))
        # Sum for this aperture
        sum = 0
        numpix = 0
        ys = y = y0 -r
        ye = y0 +r
        vline = list()
        hline = list()
        while (y < ye):
            angle = fabs(1.*(y-y0)/r)
            dx = int(sin(acos(angle))*r)
            x = xs = x0 - dx
            xe = x0 + dx
            while (x < xe):
                sum += float(dc[y][x])
                x += 1
                if (x == x0):
                    hline.append(float(dc[y][x]))
                if (y == y0):
                    vline.append(float(dc[y][x]))
                    #print "x = %s, y= %s val=%s" % (x,y,float(dc[y][x]))
                numpix += 1
            y += 1
        linex.append(hline)
        liney.append(vline)
        counts.append(sum)
    #print datetime.now() - now
    
    # Send back the raw total counts. Analysis can be done when the graph is produced.
    pointsum = {'bg' :  '%.2f' % counts[0], 'sc' : '%.2f' % counts[1], 'cal' : counts[2:]}
    lines = {'data' : {
               'coords' : {'xy' : coords,'r':r},
                'sum'   : pointsum,
                'points' : {'bg':
                                {'horiz' : linex[0],
                                'vert' : liney[0],
                                },
                            'sc':
                                {'horiz' : linex[1],
                                'vert' : liney[1],
                                },
                            'cal':
                                {'horiz' : linex[2:],
                                'vert' : liney[2:],
                                },
                            },
                #'quality' : flag,
               'pixelcount' : numpix,
                },
            }
    #print (datetime.now() - now)
    # save measurement data on the backend automatically
    entrymode = request.POST.get('entrymode','M')
    resp = savemeasurement(person,pointsum,coords,dataid,entrymode)
    if  resp['code'] == messages.ERROR:
        lines = {'error':  resp['msg']}
    else:
        messages.add_message(request, resp['code'], resp['msg'])
    return HttpResponse(json.dumps(lines,indent = 2),mimetype='application/javascript')
        
def measurementsummary(request,code,format):
    ####################
    # Return a measument data set based on event code and having either 'json' or 'xml' format
    data = []
    maxpixel = 1024
    csv =""
    if (request.user.is_authenticated()):
        o = Observer.objects.filter(user=request.user)
    else:
        o = Observer.objects.filter(user=guestuser)
    options = request.GET.get('mode','')
    if (format == 'xhr' and options ==''):
        #cals = []
        sources = []
        dates = []
        stamps = []
        rawcals = []
        timestamps = []
        cals = []
        mypoints = Datapoint.objects.filter(user=o[0].user,data__event__name=code).order_by('data__timestamp')
        for d in mypoints.filter(pointtype='S'):
            dates.append(d.data.timestamp.isoformat(" "))
            stamps.append(timegm(d.data.timestamp.timetuple())+1e-6*d.data.timestamp.microsecond)
            timestamps.append(d.data.timestamp)
        sources = array(mypoints.filter(pointtype='S').values_list('value',flat=True))
        ids = mypoints.filter(pointtype='S').values_list('data__id',flat=True)
        bg = array(mypoints.filter(pointtype='B').values_list('value',flat=True))
        sb = sources -bg
        cs = mypoints.filter(pointtype='C').order_by('coorder__calid')
        maxcals = cs.aggregate(Max('coorder__calid'))['coorder__calid__max']
        if maxcals == None:
            maxcals = -1
        for i in range(0,maxcals+1):
            vals = []
            for d,item in enumerate(ids):
                cp = cs.filter(data__timestamp=timestamps[d])
                if len(cp) > i:
                    vals.append(sb[d]/(cp[i].value-bg[d]))
                else:
                    vals.append(0.0)
            maxvals = r_[vals[:3],vals[-3:]]
            nz = maxvals.nonzero()
            maxval = mean(maxvals[nz])
            cals.append(list(vals/maxval))
        datapoints = {'calibration' : cals, 'source' : list(sources),'background':list(bg),'dates':dates,'id':list(ids),'datestamps':stamps,'n':maxcals+1}
        dataid = request.GET.get('dataid','')
        return HttpResponse(json.dumps(datapoints,indent=2),mimetype='application/javascript')
    elif (format == 'xhr' and options=='ave'):
        #cals = []
        #cs = mypoints.filter(pointtype='C').order_by('coorder__calid')
        maxcals = DataCollection.objects.filter(person=o[0].user,planet__name=code).aggregate(Max('calid'))['calid__max']
        if maxcals:
            # cals,normcals,mycals,sb,bg,dates,stamps,ids,cats = myaverages(code, o[0].user)
            cals,normcals,sb,bg,dates,stamps,ids,cats = averagecals(code, o[0].user)
            # datapoints = {'calibration' : normcals, 'mycals': mycals,'source' : sb,'background':bg,'calibrator':cals,'dates':dates,'id':ids,'datestamps':stamps,'n':maxcals+1}
            datapoints = {'calibration' : normcals, 'source' : sb,'background':bg,'calibrator':cals,'dates':dates,'id':ids,'datestamps':stamps,'n':maxcals+1}
        else:
            datapoints = {'calibration':None}
        return HttpResponse(json.dumps(datapoints,indent=2),mimetype='application/javascript')
    elif (format == 'xhr' and options == 'super'):
        # Construct the supercalibrator lightcurve
        planet = Event.objects.filter(name=code)[0]
        numsuper, normvals, std,radiusratio = supercaldata(planet)
        sources = DataSource.objects.filter(event=planet).order_by('timestamp')
        dates = []
        for s in sources:
            dates.append(timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,)
        datapoints = {'normalised' : normvals, 'dates':dates, 'std':std}
        return HttpResponse(json.dumps(datapoints),mimetype='application/javascript')
    elif (request.GET and format == 'json'):
        dataid = request.GET.get('dataid','')
        s = DataSource.objects.filter(id=dataid)[0]
        ps  = Datapoint.objects.filter(~Q(pointtype = 'R'),data = s).order_by('-pointtype')
        datalist = [{'mine': ismypoint(o[0],dp.user),'x' : dp.xpos,'y' : dp.ypos, 'r' : dp.radius, 'value' : dp.value,'type':dp.pointtype} for dp in ps]
        line = {
                'id'        : "%i" % s.id,
                'date'      : s.timestamp.isoformat(" "),
                'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                'data'      : datalist,
                }
        return HttpResponse(json.dumps(line,indent = 2),mimetype='application/javascript')
    else:
        planet = Event.objects.filter(name=code)[0]
        numsuper, normvals, myvals, std,radiusratio = supercaldata(request.user,planet)
        sources = DataSource.objects.filter(event=planet).order_by('timestamp')
        n = 0
        if format == 'json':
            data = []
            if len(normvals) == planet.numobs :
                for i,s in enumerate(sources):
                    line = {
                            'id'        : "%i" % s.id,
                            'date'      : s.timestamp.isoformat(" "),
                            'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                            'data'      : {
                                            'mean' : normvals[i],
                                            'std'  : std[i],
                                            'mine' : myvals[i],
                                },
                            }
                    data.append(line)
            else:
                data = None
            return HttpResponse(json.dumps(data,indent = 2),mimetype='application/javascript')
        # elif format == 'xml':
        #     return render_to_response('agentex/data_summary.xml',{'data':data},mimetype="application/xhtml+xml")
        elif format == 'csv':
            csv = "# Date of observation, Unix timestamp, normalised average values, standard deviation, my normalised values\n"
            for i,s in enumerate(sources):
                csv += "%s, %s, %s, %s, %s\n" % (s.timestamp.isoformat(" "),timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,normvals[i],std[i],myvals[i])
            return HttpResponse(csv,mimetype='text/csv')

def calibratemydata(code,user):
    #cs = Datapoints.objects.filter(pointtype='C',user=user).order_by('coorder__calid')
    ds = DataSource.objects.filter(event__name=code).order_by('timestamp')
    stars = DataCollection.objects.filter(planet__name = code,person=user).values_list('source',flat=True)
    cals = []
    # mycals = []
    # dates = []
    # stamps = []
    # timestamps = []
    # ids = []
    # scA = []
    # bgA = []
    for i,st in enumerate(stars):
        vals = []
        #myvals = []
        for d in ds:
            points = Datapoint.objects.filter(data=d)
            cp = points.filter(pointtype='C',coorder__source=st).aggregate(ave=Avg('value'))['ave']
            sb = points.filter(pointtype='S').aggregate(ave=Avg('value'))['ave']
            bg = points.filter(pointtype='B').aggregate(ave=Avg('value'))['ave']
            if cp:
                vals.append((sb-bg)/(cp-bg))
            else:
                vals.append(0.0)
            mypoint = points.filter(user=user)
            if mypoint:
                vals.append((sb-bg)/(mypoint[0].value-bg))
            else:
                vals.append('0.0')
        maxval = max(vals)
        #nz = maxvals.nonzero()
        #maxval = mean(maxvals)
        cals.append(list(vals/maxval)) 
        #mycals.append(list(myvals/maxval))
    return mycals
    
def myaverages(code,person):
    ds = DataSource.objects.filter(event__name=code).order_by('timestamp').values_list('id',flat=True)
    valid_user = False
    if person:
        if person.is_authenticated():
            valid_user = True
    if valid_user:
        now = datetime.now()
        cals = []
        mycals = []
        dates = []
        stamps = []
        timestamps = []
        normcals = []
        maxvals = []
        cats = []
        # Find which Cat Sources I have observed and there is a complete set of (including other people's data)
        # Unlike CalibrateMyData it only includes set where there are full sets
        e = Event.objects.filter(name=code)[0]
        dc = DataCollection.objects.filter(~Q(source=None),person=person,planet=e).order_by('calid')
        cs = CatSource.objects.filter(id__in=[c.source.id for c in dc]).annotate(count=Count('datacollection__datapoint')).filter(count__gte=e.numobs).values_list('id',flat=True)
        mydecisions = Decision.objects.filter(person=person,current=True,planet=e,value='D').values_list('source__id',flat=True)
        if cs.count() > 0:
            # Only use ones where we have more than numobs
            for c in dc:
                # make sure these are in the mydecision list (i.e. I've said they have a Dip)
                if c.source.id in mydecisions:
                    v = Datapoint.objects.filter(coorder__source=c.source.id,pointtype='C',user=person).order_by('data__timestamp').values_list('data__id','value')
                    cals.append(dict(v))
            if cals:
                # Only proceed if we have calibrators in the list (i.e. arrays of numobs)
                points = Datapoint.objects.filter(user=person,data__event__name=code).order_by('data__timestamp')
                scA = points.filter(pointtype='S').values_list('data__id','value')
                bgA = points.filter(pointtype='B').values_list('data__id','value')
                # Create a list of normalised values with gaps if I haven't done the full dataset but have contributed to a 'Dip' classification
                sc=dict(scA)
                bg=dict(bgA)
                sc = dictconv(sc,ds)
                sc = array(sc)
                bg = dictconv(bg,ds)
                bg = array(bg)
                for cal in cals:
                    val = (sc - bg)/(array(dictconv(cal,ds))-bg)
                    val = nan_to_num(val)
                    normcals.append(val)
                normmean = mean(normcals,axis=0)
                return list(normmean/max(normmean))
    # If they have no 'D' decisions
    return [0.]*ds.count()
    
def calibrator_averages(code,person=None,progress=False):
    cals = []
    cats = []
    planet = Event.objects.get(name=code)
    sources = list(DataSource.objects.filter(event=planet).order_by('timestamp').values_list('id','timestamp'))
    ids,stamps = zip(*sources)
    if person:
        ## select calibrator stars used, excluding ones where ID == None, i.e. non-catalogue stars
        dc = DataCollection.objects.filter(~Q(source=None),person=person,planet=planet).order_by('calid')
        ## Measurement values only for selected 'person'
        dps = Datapoint.objects.filter(data__event=planet,user=person).order_by('data__timestamp')
    else:
        # select calibrator stars used, excluding ones where ID == None, i.e. non-catalogue stars
        dc = DataCollection.objects.filter(~Q(source=None),planet=planet).order_by('calid')
        ## Measurement values only for selected 'person'
        dps = Datapoint.objects.filter(data__event=planet).order_by('data__timestamp')
    averages = AverageSet.objects.filter(planet=planet)
    if person:
        # Make a combined list of source values
        measurements = dps.filter(pointtype='S')
        sc = average_combine(measurements,averages,ids,None,'S',progress)
        # Make a combined list of background values
        measurements = dps.filter(pointtype='B')
        bg = average_combine(measurements,averages,ids,None,'B',progress)
    else:
        sc = array(averages.filter(star=None,settype='S')[0].data)
        bg = array(averages.filter(star=None,settype='B')[0].data)
    # Make a combined list of all calibration stars used by 'person'
    for calibrator in dc:
        if person:
            measurements = dps.filter(pointtype='C',coorder=calibrator)
            ave = average_combine(measurements,averages,ids,calibrator.source,'C',progress)
        else:
            ave_cal = averages.filter(star=calibrator,settype='C')
            if ave_cal.count() > 0:
                ave = array(ave_cal[0].data)
            else:
                ave = array([])
        if ave.size > 0:
            cals.append(ave)
            try:
                if person:
                    decvalue = Decision.objects.filter(source=calibrator.source,person=person,planet=planet,current=True)[0].value
                else:
                    decvalue = Decision.objects.filter(source=calibrator.source, planet=planet,current=True)[0].value
            except:
                decvalue ='X'
            cat_item = {'sourcename':calibrator.source.name,'catalogue':calibrator.source.catalogue}
            cat_item['decsion'] = decvalue
            cat_item['order'] = str(calibrator.calid)
            cats.append(cat_item)
    return cals,sc,bg,stamps,ids,cats
    
def average_combine(measurements,averages,ids,star,category,progress,admin=False):
    if progress['done'] < progress['total']:
        ave_measurement = averages.filter(star=star,settype=category)
        if ave_measurement.count() > 0:
            ## Find the array indices of my values and replace these averages
            ave = array(ave_measurement[0].data)
            mine = zip(*measurements.values_list('data','value'))
            try:
                my_ids = [ids.index(x) for x in mine[0]]
                ave[my_ids] = mine[1]
            except Exception, e:
                print e
            return ave
        else:
            return array([])
    elif progress['done'] == progress['total']:
        mine = array(measurements.values_list('value',flat=True))
        return mine
    elif not progress:
        print "No progress was passed"
        return array([])
    else:
        print "Error - too many measurements: %s %s" % (measurements.count() , numobs)
        return array([])
        
def admin_averagecals(code,person):
    # Uses and SQL statement to try to speed up the query for averaging data points
    # If person == 0 this will return all calibrator values individually - for problem solving
    now = datetime.now()
    cals = []
    mycals = []
    dates = []
    stamps = []
    timestamps = []
    normcals = []
    maxvals = []
    callist = []
    cats = []
    # Find which Cat Sources I have observed and there is a complete set of (including other people's data)
    # Unlike CalibrateMyData it only includes set where there are full sets
    e = Event.objects.filter(name=code)[0]
    if person == 0:
        dc = DataCollection.objects.filter(~Q(source=None),planet__name=code).values_list('source__id',flat=True).distinct()
        cs = CatSource.objects.filter(id__in=[c for c in dc]).annotate(count=Count('datacollection__datapoint')).filter(count__gte=e.numobs).values_list('id',flat=True).distinct()
        dcall = DataCollection.objects.filter(planet=e,source__in=cs).values_list('id',flat=True)
        # print "** Collections %s" % dcall.count()
        if cs.count() > 0:
            # Only use ones where we have more than numobs
            for c in dc:
                # make sure these are in the CatSource list (can't use cs because the order isn't right)
                if c in cs:
                    people = Decision.objects.filter(source__id=c,current=True,value='D').values_list('person',flat=True)
                    if people:
                        v = Datapoint.objects.filter(coorder__source=c,pointtype='C',user__id__in=people).order_by('data__timestamp').values_list('data__id').annotate(Avg('value'))
                    else:
                        v = Datapoint.objects.filter(coorder__source=c,pointtype='C').order_by('data__timestamp').values_list('data__id').annotate(Avg('value'))
                    # Double check we have same number of obs and cals
                    if v.count() == e.numobs:
                        ids,b = zip(*v)
                        cals.append(list(b))
                        decvalue_full = Decision.objects.filter(source=c,planet__name=code,current=True).values_list('value').annotate(total=Count('id')) 
                        decvalue = dict((str(key),value) for key,value in decvalue_full)                          
                        source = CatSource.objects.get(id=c)
                        cat_item = {'sourcename':str(source.name),'catalogue':str(source.catalogue),'sourceid': str(c),'include':source.final}
                        cat_item['decisions'] = decvalue
                        cats.append(cat_item)
                        callist.append(c)
    else:
        dc = DataCollection.objects.filter(~Q(source=None),person=person,planet__name=code).order_by('calid')
        cs = CatSource.objects.filter(id__in=[c.source.id for c in dc]).annotate(count=Count('datacollection__datapoint')).filter(count__gte=e.numobs).values_list('id',flat=True).distinct()
        dcall = DataCollection.objects.filter(planet=e,source__in=cs).values_list('id',flat=True)
        # print "** Collections %s" % dcall.count()
        if cs.count() > 0:
            # Only use ones where we have more than numobs
            for c in dc:
                # make sure these are in the CatSource list (can't use cs because the order isn't right)
                if c.source.id in cs:
                    v = Datapoint.objects.filter(coorder__source=c.source.id,pointtype='C').order_by('data__timestamp').values_list('data__id').annotate(Avg('value'))
                    # Double check we have same number of obs and cals
                    if v.count() == e.numobs:
                        ids,b = zip(*v)
                        cals.append(list(b))
                        try:
                            decvalue = Decision.objects.filter(source=c.source,person=person,planet__name=code,current=True)[0].value
                        except:
                            decvalue ='X'
                        cat_item = {'sourcename':c.source.name,'catalogue':c.source.catalogue}
                        cat_item['decsion'] = decvalue
                        cat_item['order'] = str(c.calid)
                        cats.append(cat_item)
                        callist.append(c.source.id)
    if callist:
        # Only proceed if we have calibrators in the list (i.e. arrays of numobs)
        ds = DataSource.objects.filter(event=e).order_by('timestamp')
        users = DataCollection.objects.filter(id__in=dcall).values_list('person',flat=True).distinct()
        maxnum = ds.count()
        dsmax1 = ds.aggregate(Max('id'))
        dsmax = dsmax1['id__max']
        dsmin = dsmax - maxnum
        ds = ds.values_list('id',flat=True)
        if person == 0:
            people = Decision.objects.filter(planet=e,value='D',current=True).values_list('person',flat=True).distinct()
            dp = Datapoint.objects.filter(data__event=e,user__id__in=people)
            sc = []
            bg = []
            for d in ds:
                sc_ave = dp.filter(pointtype='S',data__id=d).aggregate(val=Avg('value'))
                bg_ave = dp.filter(pointtype='B',data__id=d).aggregate(val=Avg('value'))
                sc.append(sc_ave['val'])
                bg.append(bg_ave['val'])
        else:
            sc_my = ds.filter(datapoint__pointtype='S',datapoint__user=person).annotate(value=Sum('datapoint__value')).values_list('id','value')
            bg_my = ds.filter(datapoint__pointtype='B',datapoint__user=person).annotate(value=Sum('datapoint__value')).values_list('id','value')
            if sc_my.count() < maxnum:
                return cals,normcals,[],[],dates,stamps,[],cats
            else:
                tmp,sc=zip(*sc_my)
                tmp,bg=zip(*bg_my)
        # Convert to numpy arrays to allow simple calibrations
        sc = array(sc)
        bg = array(bg)     
        for cal in cals:
            val = (sc - bg)/(array(cal)-bg)
            maxval = mean(r_[val[:3],val[-3:]])
            maxvals.append(maxval)
            norm = val/maxval
            normcals.append(list(norm))
        # Find my data and create unix timestamps
        unixt = lambda x: timegm(x.timetuple())+1e-6*x.microsecond
        iso = lambda x: x.isoformat(" ")
        times = ds.values_list('timestamp',flat=True)
        stamps = map(unixt,times)
        dates = map(iso,times)
        if person == 0:
            return normcals,stamps,[int(i) for i in ids],cats
        return cals,normcals,list(sc),list(bg),dates,stamps,[int(i) for i in ids],cats
    if person == 0:
        return normcals,stamps,[],[]
    return cals,normcals,[],[],dates,stamps,[],cats
    
def photometry(code,person,progress=False,admin=False):
    normcals = []
    maxvals = []
    cals,sc,bg,times,ids,cats = calibrator_averages(code,person,progress)
    indexes = [int(i) for i in ids]
    #sc = array(sc)
    #bg = array(bg)     
    for cal in cals:
	if len(cal) == progress['total']:
        #### Do not attempt to do the photmetry where the number of calibrators does not match the total        
            val = (sc - bg)/(cal-bg)
            maxval = mean(r_[val[:3],val[-3:]])
            maxvals.append(maxval)
            norm = val/maxval
            normcals.append(list(norm))
        # Find my data and create unix timestamps
    unixt = lambda x: timegm(x.timetuple())+1e-6*x.microsecond
    iso = lambda x: x.isoformat(" ")
    stamps = map(unixt,times)
    dates = map(iso,times)
    if admin:
        return normcals,stamps,indexes,cats
    return cals,normcals,list(sc),list(bg),dates,stamps,indexes,cats
        
def averagecals_async(e):
    #e = Event.objects.get(name=code)
    catsource = DataCollection.objects.values_list('source').filter(planet=e, display=True).annotate(Count('source'))
    for cat in catsource:
        if cat[0] != None:
            dps = Datapoint.objects.filter(data__event=e, coorder__source__id=cat[0], pointtype='C').order_by('data__timestamp').values_list('data').annotate(Avg('value'))
            # Double check we have same number of obs and cals
            if dps.count() == e.numobs:
                ids,values = zip(*dps)
                a = AverageSet.objects.get_or_create(star=CatSource.objects.get(id=cat[0]),planet=e,settype='C')
                a[0].values = ";".join([str(i) for i in values])
                a[0].save()
                print "Updated average sets on planet %s for %s" % (e.title,CatSource.objects.get(id=cat[0]))
    # Make averages for Source star and Background
    for category in ['S','B']:
        dps = Datapoint.objects.filter(data__event=e, pointtype=category).order_by('data__timestamp').values_list('data').annotate(Avg('value'))
        # Double check we have same number of obs and cals
        if dps.count() == e.numobs:
            ids,values = zip(*dps)
            a = AverageSet.objects.get_or_create(planet=e,settype=category)
            a[0].values = ";".join([str(i) for i in values])
            a[0].save()
            print "Updated average sets on planet %s for %s" % (e.title,category)
    return


def supercaldata(user,planet):
    calibs = []
    mypoints = []
    ti = 0.
    # assume data which has Decisions forms part of a complete set
    # People and their sources who have Dips in the select planet
    now = datetime.now()
    planet = Event.objects.get(name = planet)
    decs = Decision.objects.values_list('person','source').filter(value='D', current=True, planet=planet, source__datacollection__display=True).annotate(Count('source'))
    numsuper = decs.count()
    if settings.LOCAL_DEVELOPMENT: print "Number of supercals: %s" % numsuper
    # Create a lists of sources  and people
    if decs:
        peoplelst,sourcelst,tmp = zip(*decs)
        #print "%s - %s" % (ti, datetime.now()-now)
        ti += 1
        people = set(peoplelst)
        sources = set(sourcelst)
        for p in people:
            calslist = []
            vals = Datapoint.objects.filter(data__event=planet,user=p).order_by('data__timestamp')
            sourceave = vals.filter(pointtype='S').annotate(mean=Avg('value')).values_list('mean',flat=True)
            bgave = vals.filter(pointtype='B').annotate(mean=Avg('value')).values_list('mean',flat=True)
            # make into Numpy arrays for easier manipulation
            sc = array(sourceave)
            bg = array(bgave)
            calvals = Datapoint.objects.values('data','coorder__source').filter(user= p,coorder__source__in=sources,pointtype='C',coorder__source__final=True,coorder__complete=True,coorder__display=True)
            for c in sources:
                calaves = calvals.filter(coorder__source=c)
                calpoints = calaves.order_by('data__timestamp').annotate(mean=Avg('value')).values_list('mean',flat=True)
                if calpoints.count() == planet.numobs:
                    calslist.append(list(calpoints))
            if calslist:
                if settings.LOCAL_DEVELOPMENT: print "\033[94mWe have calibrators\033[1;m"
                calstack = vstack(calslist)
                # This throws a wobbly sometimes
                cc = (sc-bg)/(calstack-bg)
                calibs.append(cc.tolist())
            else:
                if settings.LOCAL_DEVELOPMENT: print "\033[1;35mThere are no calibrators in the list!!\033[1;m"
            #print "%s %s - %s" % (ti, p, datetime.now()-now)
            ti += 1
        # Create normalisation function
        norm_a = lambda a: mean(r_[a[:3],a[-3:]])
        mycals = []
        try:
            cala = vstack(calibs)
            norms = apply_along_axis(norm_a, 1, cala)
            dim = len(cala)
            norm1 = cala/norms.reshape(dim,1)
            mynorm1=[]
            if mypoints != []:
                #mynorms = apply_along_axis(norm_a, 1, mypoints)
                myaves = average(mypoints,0)
                mynorm_val = norm_a(myaves)
                mycals = list(myaves/mynorm_val)
        except Exception, e:
            print e
            print "\033[1;35mHave you started again but not removed all the data?\033[1;m"
            return None,[],[],[],None
        #if dim != len(mycals):
        # check if I have a full set of data, if not we need to do all the calibrator averages manually
        norm_alt = mean(norm1,axis=0)
        variance = var(norm1,axis=0)
        std = sqrt(variance)
        fz = list(norm_alt)
        nodata = False
        if mycals == []:
            mycals = myaverages(planet,user)
            nodata = True
        return numsuper,fz,mycals,list(std),nodata
    else:
        return None,[],[],[],None

def leastmeasured(code):
    coords = []
    e = Event.objects.filter(name=code)[:1]
    dc = DataCollection.objects.values('source').filter(~Q(source=None),planet__name=code).annotate(count = Count('source')).order_by('count')[:4]
        # e = Event.objects.filter(name=code)
        # finderdp = Datapoint.objects.values_list('xpos','ypos').filter(user=person,data__id=e[0].finder,pointtype='C',coorder__calid__lt=3).order_by('coorder__calid')
        # finder = basiccoord - array(finderdp)
        # t = transpose(finder)
        # xmean = mean(t[0])
        # ymean = mean(t[1])
    for coll in dc:
        s = CatSource.objects.get(id=coll['source'])
        coords.append({'x':int(s.xpos),'y':int(s.ypos),'r':int(e[0].radius)})
    return coords   
        

def update_web_pref(request,setting):
    #################
    # AJAX update user preference for web or  manual input of data
    if (request.user.is_authenticated()):
        person = request.user
    else:
        person = guestuser
    o = Observer.objects.filter(user=person)
    if setting == 'yes':
        o.update(dataexplorview=True)
        return HttpResponse("Setting changed to use web view")
    elif setting == 'no':
        o.update(dataexploreview = False)
        return HttpResponse("Setting changed to use manual view")
    else:
        return HttpResponse("Setting unchanged")
            
def tester(request):
    return render_to_response('agentex/test.html')
    
def average_sources(code):
    typep = ('S','C','B')
    ds = DataSource.objects.filter(name=code)
    for s in ds:
        points = Datapoint.objects.filter(data=s)
        dates = points.values_list('taken',flat=True)
        for date in dates:
            entry = points.objects.filter(taken=date)
            

def calibrate_update(code):
    dates = Datapoint.objects.values_list('taken',flat=True).filter(data__event__name=code).annotate(Count('taken'))
    for date in dates:
        measurement = Datapoint.objects.filter(taken=date,data__event__name=code)
        source = measurement.filter(pointtype='S')
        calib = measurement.filter(pointtype='C')
        backg = measurement.filter(pointtype='B')
        value = (source[0].value - backg[0].value)/(calib[0].value - backg[0].value)
        reduced = measurement.filter(pointtype='R')[0]
        reduced.value = value
        reduced.save()
        print "Reduced %s" % date
        
def calibrate(measurement):
    source = measurement.filter(pointtype='S')
    calib = measurement.filter(pointtype='C')
    backg = measurement.filter(pointtype='B')
    value = (source[0].value - backg[0].value)/(calib[0].value - backg[0].value)
    return value
    
def img_coord_conv(x,size):
    newx = []
    entries = x.split(",")
    for entry in entries:
        newx.append(floor(float(entry)*size))
    return newx
        
def ismypoint(person,datauser):
    if person.user == datauser:
        return True
    else:
        return False
def personcheck(request):
    if (request.user.is_authenticated()):
        o = Observer.objects.filter(user=request.user)
    else:
        o = Observer.objects.filter(user__id=guestuser)
    return o[0]
    
def classified(o,code):
    dcs = Decision.objects.values('source').filter(person=o.user,planet__name=code).annotate(last = Max('taken'))
    dips = Decision.objects.filter(taken__in=[d['last'] for d in dcs],person=o.user,planet__name=code,value='D').count()
    classifications = Decision.objects.values('source').filter(person=o.user,planet__name=code).annotate(Count('value')).count()
    totalcalibs = DataCollection.objects.values('source').filter(person=o.user,planet__name=code).annotate(Count('display')).count()
    return {'total' : totalcalibs, 'done':classifications,'dip':dips}
    
def checkprogress(person,code):
    n_analysed = Datapoint.objects.filter(user=person, data__event__name=code,pointtype='S').count()
    n_sources = DataSource.objects.filter(event__name=code).count()
    if (n_sources == 0):
	    progress = {'percent'   : "0.0",
                'done'      : n_analysed,
                'total'     : n_sources,}
    else:
	    progress = {'percent'   : "%.0f" % (float(n_analysed)*100/float(n_sources)),
                'done'      : n_analysed,
                'total'     : n_sources,}
    return progress    

def fetch_averages_sql(dsmin,dsmax,pointtype,users):
    cursor = connection.cursor()
    users_str = [int(i) for i in users]
    params = [pointtype,dsmin,dsmax,users_str]
    cursor.execute('SELECT dp.data_id, avg(dp.value) FROM dataexplorer_datapoint as dp RIGHT JOIN dataexplorer_datasource AS ds on dp.data_id = ds.id WHERE dp.pointtype = %s AND (dp.data_id BETWEEN %s AND %s) AND dp.user_id IN %s GROUP BY dp.data_id order by ds.timestamp', params)
    result = list(cursor.fetchall())
    #ave_values = dict(result)
    return result
    
def dictconv(data,ref):
    tmp = []
    for i in ref:
        try:
            tmp.append(data[i])
        except:
            tmp.append(0.)
    return tmp
  
def addcomment(request):
# Log user comments in the Django log
    if request.POST:
        message = request.POST.get('comment','')
        if message:
            if request.user.is_authenticated():
              userid = request.user.pk
              email = request.user.email
            else:
              userid = 1
              email = request.POST.get('emailaddress','')
              message = "%s : %s" % (message,email)
        
            # Attach the comment to User content type pk = 3
            contentpk = 3
            LogEntry.objects.log_action(
                user_id         = userid, 
                content_type_id = contentpk,
                object_id       = userid,
                object_repr     = smart_unicode(User.objects.get(id=userid)), 
                action_flag     = ADDITION,
                change_message  = message,
            )
            messages.success(request,'Thank you for your comments!')
            data = {'emailaddress' : email,'comment':' '}
            form = CommentForm()
        else:
            form = CommentForm(request.POST)
    else:
        if request.user.is_authenticated():
          data = {'emailaddress' : request.user.email,'comment':' '}
          form = CommentForm(data)
        else:
            form = CommentForm()
    return render_to_response('agentex/comments_box.html', {'form':form}, context_instance=RequestContext(request))

def update_final_display():
    c = CatSource.objects.all()
    c.update(final=True)
    decs = Decision.objects.filter(value='D',current=True)
    for d in decs:
        dc = DataCollection.objects.filter(person=d.person,source=d.source)
        dc.update(display=True)
        print d.planet, d.person
        
def update_cat_sources(username,planetcode):
    event = Event.objects.get(name=planetcode)
    points = Datapoint.objects.filter(user__username=username,data__id=event.finder,pointtype='C')
    for p in points:
        cats = CatSource.objects.filter(xpos__lt=p.xpos+5,ypos__lt=p.ypos+5,xpos__gt=p.xpos-5,ypos__gt=p.ypos-5,data__event=event)
        dc = p.coorder
        if cats:
            dc.source=cats[0]
            print dc.id,dc.source.data.event
        else:
            dc.source=None
            print dc.id, 'No catsource found'
        dc.save()
        
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
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model
from django.conf import settings
from django.contrib.auth.models import User, check_password
from django.contrib.auth.backends import ModelBackend
import MySQLdb
import hashlib
from settings import DATABASES as dbc
from agentex.models import Observer

        
def matchRTIPass(username,password):
    # Retreive the database user information from the settings
    db = MySQLdb.connect(user=dbc['wis']['USER'], passwd=dbc['wis']['PASSWORD'], db=dbc['wis']['NAME'], host=dbc['wis']['HOST'])

    # Match supplied user name to one in Drupal database
    sql_users = "SELECT schoolloginname, password, contactemailaddress,tag,schoolname FROM registrations WHERE schoolloginname='%s' AND (accountstatus = 'active' OR accountstatus = 'suspended')" % username
    rti = db.cursor()
    rti.execute(sql_users)
    user = rti.fetchone()
    rti.close()
    db.close()
    if user:
        if (password == user[1]):
            ###### If the user does not have an email address return false
            if user[2]:
                return user[2], user[3], user[4]
            else:
                return False
    else:
        return False
        
def checkUserObject(params,username,password):
    email = params[0]
    tag = params[1]
    org = params[2]
    try:
        user = User.objects.get(username=username)
        hashpass = hashlib.md5(password).hexdigest()
        if (user.password != hashpass):
            user.password = hashpass
            user.save()
    except User.DoesNotExist:
        name_count = User.objects.filter(username__startswith = username).count()
        if name_count:
            username = '%s%s' % (username, name_count + 1)
            user = User.objects.create_user(username,password=password,email=email)
        else:
            user = User.objects.create_user(username,password=password,email=email)
#### Check there is an observer for this user
    try:
        o = Observer.objects.get(user=user)
    except:
        if tag and org:
            o = Observer(user=user,tag=tag,organization=org)
        elif tag:
            o = Observer(user=user,tag=tag)
        else:
            o = Observer(user=user)
        o.save()
    return user   
         
class LCOAuthBackend(ModelBackend):         
    def authenticate(self, username=None, password=None):
        fns =  matchRTIPass(username, password)
        for response in fns:
            if (response):
                return checkUserObject(response,username,password)
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None  

            
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
DATA_LOCATION ='/Volumes/Tardis-type40/AgentExoplanetData/agentexdata'
DATA_URL = 'http://127.0.0.1/agentexdata'

PREFIX = ''
DEBUG = True
PRODUCTION = False
STATIC_ROOT =  '/Users/egomez/Sites/static'
STATIC_URL = '/static/'

LOGIN_URL = 'http://localhost:8000/account/login/'
LOGIN_REDIRECT_URL = '/''''
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
# Django settings for observing project.

import os
import platform
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
from django.utils.crypto import get_random_string


CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
LOCAL_DEVELOPMENT = False if CURRENT_PATH.startswith('/var/www') else True
PRODUCTION = True

DEBUG = False

PREFIX ="/agentexoplanet"
BASE_DIR = os.path.dirname(CURRENT_PATH)

ADMINS = (
     ('Edward Gomez', 'egomez@lcogt.net'),
)

MANAGERS = ADMINS

DATABASES = {
 'default' : {
    'NAME'      : 'citsciportal',
    "USER": os.environ.get('CITSCI_DB_USER',''),
    "PASSWORD": os.environ.get('CITSCI_DB_PASSWD',''),
    "HOST": os.environ.get('CITSCI_DB_HOST',''),
    "OPTIONS"   : {'init_command': 'SET storage_engine=INNODB'},
}
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


MEDIA_ROOT = '/var/www/html/media/'
MEDIA_URL = '/media/'

STATIC_ROOT = '/var/www/html/static/'
STATIC_URL = PREFIX + '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR,'agentex'),os.path.join(BASE_DIR,'showmestars')]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder"
 )

# Make this unique, and don't share it with anybody.
chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
SECRET_KEY = get_random_string(50, chars)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)  

CACHE_MIDDLEWARE_SECONDS = '1'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    )

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.messages',
    'agentex',
    'showmestars',
    'core'
)

LOGIN_REDIRECT_URL = 'http://lcogt.net/agentexoplanet/'
LOGIN_URL = 'http://lcogt.net/agentexoplanet/account/login/'

BASE_URL = "/agentexoplanet/"

DATA_LOCATION = CURRENT_PATH + '/media/data'
DATA_URL = '/agentexoplanet/media/data'

##################
# LOCAL SETTINGS #
##################

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
if LOCAL_DEVELOPMENT:
    try:
        from local_settings import *
    except ImportError as e:
        if "local_settings" not in str(e):
            raise e
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
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles import views
from django.views.generic import RedirectView

admin.autodiscover()

urlpatterns = [
#    (r'^api/', include('odin.api.urls')),
    url(r'^$','agentex.views.home',name='portal'),
    url(r'^agentexoplanet/agentex/', RedirectView.as_view(url='/agentexoplanet/', name=''),
    url(r'^agentexoplanet/admin/agentex/event/(?P<planetid>\d+)/calibrators/(?P<calid>\d+)/$','agentex.admin.calibrator_check', name=''),
    url(r'^agentexoplanet/admin/agentex/event/(?P<planetid>\d+)/calibrators/$','agentex.admin.allcalibrators_check', name=''),
    url(r'^agentexoplanet/admin/', include(admin.site.urls), name=''),
    url(r'^agentexoplanet/',include('agentex.urls'), name=''),
    url(r'^showmestars/newimage/$','showmestars.views.newimage',{'eventid':0}, name=''),
    url(r'^showmestars/(?P<eventid>\w+)/$','showmestars.views.latestimages', name=''),
    url(r'^showmestars/$','showmestars.views.latestimages',{'eventid':0}, name='')
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', views.serve),
    ]
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
from django.db import models

class Event(models.Model):
    hostid = models.CharField(max_length=75)
    name = models.CharField(max_length=75)
    current = models.BooleanField(default=False)
    slotlist = models.CharField(max_length=75)
    start = models.DateTimeField()
    end = models.DateTimeField()
    site = models.CharField(max_length=75,blank=True,null=True)
    class Meta:
        verbose_name = u'show me stars event'
    def __unicode__(self):
        return "%s %s %s" % (self.name,self.start.isoformat(),self.site)
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
from agentex.models import Target, Event, Datapoint, DataSource, Badge, Achievement, DataCollection,Decision,CatSource, Observer, AverageSet
from agentex.views import photometry, calibrator_data, admin_averagecals
from django.contrib import admin
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
import json

class DatapointAd(admin.ModelAdmin):
    list_display = ['taken','data','pointtype','user','xpos','ypos','value','coorder','get_source']
    list_filter = ['pointtype']
    def get_source(self,obj):
        return '%s' % obj.coorder.source
    get_source.allow_tags = True
    get_source.short_description = 'Cat Source'
    
class DCAdmin(admin.ModelAdmin):
    list_display = ['planet','person','calid','display','complete']
    list_filter = ['display','complete','planet','person']

class DecAdmin(admin.ModelAdmin):
    list_display = ['value','person','planet','taken','source']
    list_filter = ['planet','value']
class CatAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['final']
    list_display = ['name','data','get_planet','final']
    def get_planet(self,obj):
        return '%s' % obj.data.event.title
    get_planet.allow_tags = True
    get_planet.short_description = 'Planet'
      
class DSAdmin(admin.ModelAdmin):
    list_filter = ['event','target']
    list_display = ['timestamp','event','target']
    
class EventAdmin(admin.ModelAdmin):
    list_display = ['title','name','start','midpoint','end','numobs','xpos','ypos','enabled']    
class TargetAdmin(admin.ModelAdmin):
    list_display = ['name','ra','dec','period','rstar','mass','ap','inclination']
    
class SetAdmin(admin.ModelAdmin):
    list_display = ['planet','star','settype']
    
def allcalibrators_check(request,planetid):
    # Uses and SQL statement to try to speed up the query for averaging data points
    e = Event.objects.filter(id=planetid)[0]
    normcals,dates,ids,cats = admin_averagecals(e.name,0)
    c = json.dumps(cats)
    # return normcals,stamps,[int(i) for i in ids],cats
    title = 'Check calibrators for %s' % e.title
    return render_to_response('admin/agentex/allcalibrators.html',{'calibrators':normcals,
                                                                    'title':title,
                                                                    'planetid':planetid,
                                                                    'dates':dates,
                                                                    'calids':[int(i) for i in ids],
                                                                    'cats':c},context_instance=RequestContext(request))
    
def calibrator_check(request,planetid,calid):
    planet = Event.objects.get(id=planetid)
    dcs = DataCollection.objects.filter(source__id=calid)
    if request.POST:
        people = request.POST.getlist('user')
        dcs.update(display=False)  
        include = request.POST.get('include','none')
        cs = CatSource.objects.filter(id=calid)
        if include == 'false':
            cs.update(final=False)
        elif include == 'true':
            cs.update(final=True)
        elif include == 'none':
            dcup = dcs.filter(person__username__in=people)
            dcup.update(display=True)
    data,times,people = calibrator_data(calid,planet.name)
    include = dcs.filter(person__username__in=people).values_list('display',flat=True)
    resp = {'data'       : data,
            'timestamps' : times,
            'people'     : people,
            'include'    : list(include),
            }
    return HttpResponse(json.dumps(resp,indent=2),mimetype='application/javascript')
    
admin.site.register(Target, TargetAdmin)
admin.site.register(Event,EventAdmin)
admin.site.register(Datapoint, DatapointAd)
admin.site.register(DataSource,DSAdmin)
admin.site.register(Badge)
admin.site.register(Decision,DecAdmin)
admin.site.register(Achievement)
admin.site.register(Observer)
admin.site.register(CatSource,CatAdmin)
admin.site.register(DataCollection,DCAdmin)
admin.site.register(AverageSet,SetAdmin)
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
decision_images = {
    'D':{'name':'Dip','image':'choice_dip.png'},
    'N':{'name':'No Dip','image':'choice_nodip.png'},
    'O':{'name':'Odd','image':'choice_odd.png'},
    'B':{'name':'Blip','image':'choice_blip.png'},
    'P':{'name':'Periodic','image':'choice_periodic.png'},
    'S':{'name':'Noise','image':'choice_noise.png'},
    'R':{'name':'Other','image':'choice_other.png'},
}

planet_level = {
    'corot2b' : 'beginner',
    'ogletr132b' : 'advanced',
}'''
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
from agentex.models import Event, AverageSet, Decision, Datapoint, DataSource, Target
import agentex as ax

####
#import matplotlib.pyplot as plt
####

from django.contrib.auth.models import User
from django.db.models import Count, Avg
from datetime import datetime
from calendar import timegm
from numpy import array,nan_to_num, vstack, apply_along_axis, mean, var, sqrt,average, r_, linspace

from django.conf import settings

class Dataset(object):
    def __init__(self , planetid=None,userid=None):
        try:
            self.planet = Event.objects.get(name=planetid)
        except:
            self.planet = None
        try:
            self.user = User.objects.get(username=userid)
        except:
            self.user = None
        try:
            self.target = Target.objects.get(name=self.planet.title[:-1])
        except:
            self.target = None
    def calibrators(self):
        sc = AverageSet.objects.filter(planet=self.planet, settype='S')[0].data
        bg = AverageSet.objects.filter(planet=self.planet, settype='B')[0].data
        return cals,sc,bg,time,ids,cats
    def final(self):
        normvals = AverageSet.objects.filter(planet=self.planet,settype='F')[0].data
        std = AverageSet.objects.filter(planet=self.planet,settype='E')[0].data
        sources = DataSource.objects.filter(event=self.planet).order_by('timestamp')
        #myvals = ax.views.myaverages(self.planet,self.user)
        n = 0
        data = []
        if len(normvals) == self.planet.numobs :
            for i,s in enumerate(sources):
                line = {
                        'id'        : "%i" % s.id,
                        'date'      : s.timestamp.isoformat(" "),
                        'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                        'data'      : {
                                        'mean' : normvals[i],
                                        'std'  : std[i],
                                        'mine' : 'null',#myvals[i],
                            },
                        }
                data.append(line)
        else:
            data = None
        return data
    def my_data(self):
        if self.user:
            data = []
            sources = DataSource.objects.filter(event=self.planet).values_list('id','timestamp').order_by('timestamp')
            points  = Datapoint.objects.filter(data__event=self.planet,user=self.user)
            sc = dict(points.filter(pointtype='S').values_list('data__id','value'))
            bg = dict(points.filter(pointtype='B').values_list('data__id','value'))
            cals = points.filter(pointtype='C').values_list('data__id','value').order_by('coorder')
            for d in sources:
                cal = [c[1] for c in cals if int(c[0]) == d[0]]
                line = {
                        'id'        : "%i" % d[0],
                        'date'      : d[1].isoformat(" "),
                        'datestamp' : timegm(d[1].timetuple())+1e-6*d[1].microsecond,
                        'data'      : { 'source' : None,
                                        'background' :  None,
                                        'calibrator' :  cal,
                                    },
                        }
                try:
                    line['data']['source'] = [sc[d[0]]]
                except:
                    line['data']['source'] = 'null'
                try:
                    line['data']['background'] = [bg[d[0]]]
                except:
                    line['data']['background'] = 'null' 
                data.append(line)
            return data,points
        else:
            self.error = "No user specified"
            return False
        # Produce final lightcurve from the average data sets
        # calibs = []
        # mypoints = []
        # calslist = []
        # ti = 0.
        # # assume data which has AverageSet forms part of a complete set
        # # People and their sources who have Dips in the select planet
        # decs = Decision.objects.values_list('person','source').filter(value='D', current=True, planet=self.planet, source__datacollection__display=True).annotate(Count('source'))
        # peoplelst,sourcelst,tmp = zip(*decs)
        # people = set(peoplelst)
        # sources = set(sourcelst)
        # #catsources = Decision.objects.values_list('source',flat=True).filter(value='D', current=True, planet=self.planet)
        # if decs.count() > 0:
        #     vals = Datapoint.objects.filter(data__event=self.planet,user__in=people)
        #     sourceave = vals.filter(pointtype='S').values_list('data').annotate(mean=Avg('value')).order_by('data__timestamp')
        #     bgave = vals.filter(pointtype='B').values_list('data').annotate(mean=Avg('value')).order_by('data__timestamp')
        #     sc_ave = zip(*sourceave)
        #     bg_ave = zip(*bgave)
        #     sc = array(sc_ave[1])
        #     bg = array(bg_ave[1])
        #     sets = AverageSet.objects.filter(planet=self.planet,star__in=sources)
        #     for s in sets:
        #         calslist.append(s.data)
        #     numsuper = sets.count()
        #     if settings.LOCAL_DEVELOPMENT: print "Number of supercals for %s : %s" % (self.planet.title,numsuper)
        #     # sc_set = AverageSet.objects.filter(planet=self.planet, settype='S')[0]
        #     # bg_set = AverageSet.objects.filter(planet=self.planet, settype='B')[0]
        #     # sc = array(sc_set.data)
        #     # bg = array(bg_set.data)
        #     calstack = vstack(calslist)
        #     cc = (sc-bg)/(calstack-bg)
        #     n = 0
        #     sourcelist = list(sources)
        #     calibs.append(cc.tolist())
        #     norm_a = lambda a: mean(r_[a[:3],a[-3:]])
        #     cala = vstack(calibs)
        #     norms = apply_along_axis(norm_a, 1, cala)
        #     dim = len(cala)
        #     norm1 = cala/norms.reshape(dim,1)
        #     for c in norm1:
        #         filename = 'media/transit/%s-%s.png' % (self.planet.name,sourcelist[n])
        #         plt.plot(linspace(0,len(sc),len(sc)),c, lw=2)
        #         plt.savefig(filename)
        #         plt.close()
        #         n+=1
        #     norm_alt = mean(norm1,axis=0)
        #     variance = var(norm1,axis=0)
        #     std = sqrt(variance)
        #     fz = list(norm_alt)
        #     mycals = myaverages(self.planet,self.user)
        #     nodata = True
        #     return numsuper,fz,mycals,list(std),nodata
        # else:
        #     print "No average sets"
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
from django import forms
from types import *
from django.forms import TextInput,Textarea
from django.contrib.auth.models import User

class DataEntryForm(forms.Form):
    sourceradius = forms.CharField(label='Aperture Radius (source)')
    sourcexpos = forms.CharField(label='Source x position')
    sourceypos = forms.CharField(label='Source y position')
    sourcecounts = forms.CharField(label='Source counts')
#    cal1radius = forms.CharField(label='Aperture Radius (calibrator)')
#    cal1xpos = forms.CharField(label='Calibrator x postion')
#    cal1ypos = forms.CharField(label='Calibrator y postion')
#    cal1counts = forms.CharField(label='Calibrator counts')
    bgradius = forms.CharField(label='Aperture Radius (background)')
    bgxpos = forms.CharField(label='Background x position')
    bgypos = forms.CharField(label='Background y position')
    bgcounts = forms.CharField(label='Background counts')
    
class RegisterForm(forms.Form):
    username = forms.CharField(label=u'Choose a username')
    password = forms.CharField(label= u'Password',widget=forms.PasswordInput(render_value=False))
    firstname = forms.CharField(label=u'What should we call you? (e.g. as a greeting)')
    lastname = forms.CharField(label=u'Full Name')
    emailaddress = forms.EmailField(label= u'Contact email address',widget=TextInput(attrs={'size':'60'}))
    
    def clean_username(self):
      username = self.cleaned_data['username']
      try:
          user = User.objects.get(username=username)
      except User.DoesNotExist:
          return username
      raise forms.ValidationError(u'%s already exists' % username )

            
class RegistrationEditForm(forms.Form):
    password = forms.CharField(label= u'Password',widget=forms.PasswordInput(render_value=False),required=False)
    firstname = forms.CharField(label=u'What should we call you? (e.g. as a greeting)')
    lastname = forms.CharField(label=u'Full Name')
    emailaddress = forms.EmailField(label= u'Contact email address',widget=TextInput(attrs={'size':'60'}))
    
class CommentForm(forms.Form):
    emailaddress = forms.EmailField(label= u'Contact email address',widget=TextInput(attrs={'size':'60'}),required=True)
    comment = forms.CharField(label='Comment',max_length=160, help_text='160 characters max.',widget=Textarea(attrs={'rows':4, 'cols':60}),required=True)'''
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
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from calendar import timegm
from json import dumps,loads
TYPECHOICE = (
('S','Source'),
('C','Calibration'),
('B','Background'),
('R','Reduced'),
('F','Final'),
('E','Error bar')
)
ENTRYCHOICE = (
('W','Web'),
('M','Manual'),
('N','No javascript'),
)

DECISIONS = (
('D','Dip'),
('N','No Dip'),
('O','Odd'),
('B','Blip'),
('P','Periodic'),
('S','Noise'),
('R','Other'),
)
decisions = {
    'dip':'D',
    'nodip':'N',
    'odd':'O',
    'blip':'B',
    'periodic':'P',
    'other':'R',
}

class Target(models.Model):
    name = models.CharField(blank=True, max_length=100) # Wordy name. should be the name of the host star
    ra = models.CharField('right ascension',blank=True, max_length=100)
    dec = models.CharField('declination',blank=True, max_length=100)
    constellation = models.CharField(blank=True, max_length=100)
    magv = models.CharField('apparent magnitude V',blank=True, max_length=100)
    inclination = models.FloatField('inclination of planet orbit',blank=True,null=True)
    period = models.FloatField('period of planet orbit (days)',blank=True,null=True)
    rstar = models.FloatField('radius of host star',blank=True,null=True)
    ap = models.FloatField('semi-major axis',blank=True,null=True)
    mass = models.FloatField('mass of host star',blank=True,null=True)
    description = models.TextField()
    finderchart =  models.FileField('Finder chart',upload_to="finderchart", help_text='Image with a clearly marked up target position',blank=True)
    finderchart_tb =  models.FileField('Finder chart thumbnail',upload_to="finderchart/thumb", help_text='Image with a clearly marked up target position',blank=True)
    class Meta:
        verbose_name = u'transiting exoplanet target'
        db_table = u'dataexplorer_target'
    def __unicode__(self):
        return self.name
    
class Event(models.Model):
    name = models.CharField(blank=False, max_length=20, help_text='code, no spaces and no hyphens') # code to be used in URLs i.e. NO spaces
    title = models.CharField(blank=False, max_length=100) # Longer title which can be more wordy
    start = models.DateTimeField(null=True, blank=True, default=datetime.now)
    end = models.DateTimeField(null=True, blank=True, default=datetime.now)
    midpoint = models.DateTimeField(null=True, blank=True)
    numobs = models.IntegerField(blank=True, null=True,default=0)
    finder = models.IntegerField('id of finder chart source',blank=True)
    xpos = models.IntegerField('x pos on finder chart',blank=False,default=0)
    ypos = models.IntegerField('y pos on finder chart',blank=False,default=0)
    enabled = models.BooleanField(default=True,help_text='show this event on main site')
    illustration = models.FileField('illustration',upload_to="illustration", help_text='illustration for this event',blank=True)
    radius = models.IntegerField('aperture radius', blank=False, default=10)
    class Meta:
        verbose_name = u'transit event'
        db_table = u'dataexplorer_event'
    def __unicode__(self):
        return self.name
        
class DataSource(models.Model):
    fits = models.URLField(blank=True)
    image = models.URLField(blank=True, null=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    telescopeid = models.CharField(blank=True, max_length=100)
    event = models.ForeignKey(Event)
    target = models.ForeignKey(Target)
    max_x = models.IntegerField('max pixels (x)',blank=False)
    max_y = models.IntegerField('max pixels (y)',blank=False)
    class Meta:
        verbose_name = u'data source image'
        db_table = u'dataexplorer_datasource'
    def __unicode__(self):
        return self.timestamp.isoformat()
    def unixstamp(self):
        return timegm(self.timestamp.timetuple())+1e-6*self.timestamp.microsecond
    def isostamp(self):
        return self.timestamp.isoformat()
    
class CatSource(models.Model):
    name = models.CharField('object name',blank=False,max_length=50)
    data = models.ForeignKey(DataSource)
    xpos = models.IntegerField('x position on finder image', blank=True)
    ypos = models.IntegerField('y position on finder image', blank=True)
    catalogue = models.CharField('catalogue name',blank=False,max_length=20)
    final = models.BooleanField('include in final curve',default=True)
    class Meta:
        verbose_name = "catalogue source"
        db_table = u'dataexplorer_catsource'
    def __unicode__(self):
        return self.name
    
class DataCollection(models.Model):
    person = models.ForeignKey(User)
    planet = models.ForeignKey(Event)
    display = models.BooleanField(default=False)
    complete = models.BooleanField(default=False)
    calid = models.IntegerField('calibrator order',blank=False,null=False)
    source = models.ForeignKey(CatSource,blank=True, null=True)
    class Meta:
        verbose_name = u'data collection'
        db_table = u'dataexplorer_datacollection'
    def __unicode__(self):
        val = "%s" % self.planet.title
        return val
    
class Datapoint(models.Model):
    data = models.ForeignKey(DataSource)
    taken = models.DateTimeField(blank=True, default=datetime.now)
    value = models.FloatField(blank=True,null=True)  
    user = models.ForeignKey(User)
    pointtype = models.CharField(blank=False,max_length=1,choices=TYPECHOICE)
    coorder = models.ForeignKey(DataCollection,blank=True, null=True, help_text='point order')
    xpos = models.IntegerField('x position', blank=True)
    ypos = models.IntegerField('y position', blank=True)
    radius = models.IntegerField('aperture radius', blank=True)
    entrymode = models.CharField(blank=False,max_length=1,choices=ENTRYCHOICE,default='W')
    offset = models.FloatField('distance from source',blank=True)
    class Meta:
        verbose_name = u'data point'
        db_table = u'dataexplorer_datapoint'
    class Admin:
        list_display = ('event',)
        search_fields = ('user',)
    def __unicode__(self):
        return self.taken.isoformat()
            
class Decision(models.Model):
    source = models.ForeignKey(CatSource)
    value = models.CharField('decision',blank=False,max_length=1,choices=DECISIONS)
    person = models.ForeignKey(User)
    planet = models.ForeignKey(Event)
    taken = models.DateTimeField(default=datetime.now,blank=False)
    current = models.BooleanField(default=False)
    class Meta:
        verbose_name = u'lightcurve decision'
        db_table = u'dataexplorer_decision'
    def __unicode__(self):
        return self.source.name
        
class AverageSet(models.Model):
    planet = models.ForeignKey(Event)
    star = models.ForeignKey(CatSource,blank=True,null=True)
    values = models.TextField(null=True,blank=True)
    settype = models.CharField(blank=False,max_length=1,choices=TYPECHOICE)
    class Meta:
        verbose_name = u'combined lightcurve set'
    @property 
    def data(self):
        return [float(x) for x in self.values.split(';')]
    def __unicode__(self):
        return u"%s" % (self.planet.title)
        
class Badge(models.Model):
    name = models.CharField(blank=False, max_length=20, help_text='code, no spaces')
    description = models.CharField(blank=False, max_length=200, help_text='brief, publicly readable')
    image = models.FileField(upload_to="badge",blank=False)
    class Meta:
        verbose_name = u'badge'
        db_table = u'dataexplorer_badge'
    def __unicode__(self):
        return self.name

class Achievement(models.Model):
    person = models.ForeignKey(User)
    awarded = models.DateTimeField(blank=True, default=datetime.now)
    badge = models.ForeignKey(Badge)
    planet = models.ForeignKey(Event,blank=True, null=True,help_text='planet')
    class Meta:
        verbose_name = u'achievement unlocked'
        verbose_name_plural = u'achievements unlocked'
        db_table = u'dataexplorer_achievement'
    def __unicode__(self):
        if self.planet:
            t = "%s - %s - %s" % (self.badge.name,self.person.username,self.planet.title)
        else:
            t = "%s - %s" % (self.badge.name,self.person.username)
        return t
        
class Observer(models.Model):
    user = models.OneToOneField(User, unique=True,)
    tag = models.CharField(max_length=75, blank=False,default="LCO")
    organization = models.CharField(max_length=150, blank=True)
    dataexploreview = models.BooleanField("use web interface for dataexplorer", default=True)
    class Meta:
        db_table = u'observer'
        verbose_name = "observer"
    def __unicode__(self):
        return self.user.username


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
from django.conf.urls import include, url
from django.contrib.auth.views import login, logout
from .views import *

urlpatterns = [
    url(r'^$',index, name='index'),
    url(r'^account/login/$', login, {'template_name' :'login.html'}, name='login'),
    url(r'^account/logout/$', logout,{'template_name' :'logout.html'}, name='logout'),
    url(r'^account/register/$', register, name='register'),
    url(r'^account/$', editaccount, name='editaccount'),
    url(r'^profile/$',profile, name='profile'),
    url(r'^planets/$',target, name='target'),
    url(r'^fitsanalyse',fitsanalyse, name='fitsanalyse'),
    url(r'^test',tester, name='tester'),
    url(r'^briefing/read/$',read_manual_check, name='read_manual_check'),
    url(r'^briefing/$',briefing, name='briefing'),
    url(r'^comment/$',addcomment, name='addcomment'),
    url(r'^(?P<code>\w+)/view/$',addvalue, name='addvalue'),
    url(r'^(?P<code>\w+)/graph/update/$',updatedataset, name='updatedataset'),
    url(r'^(?P<code>\w+)/lightcurve/advanced/$',graphview, {'mode' : 'advanced','calid':None}, name='advanced-graph'),
    url(r'^(?P<code>\w+)/lightcurve/me/$',graphview, {'mode' : 'simple','calid':None}, name='my-graph'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/update/$',classifyupdate, name='classifyupdate'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/$',graphview, {'mode' : 'ave','calid':None}, name='average-graph'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/(?P<calid>\w+)/$',graphview, {'mode' : 'ave'}, name='calibrator-graph'),
    url(r'^(?P<code>\w+)/lightcurve/$',graphsuper,name='super-graph'),
    url(r'^(?P<code>\w+)/$',infoview, name='infoview'),
    url(r'^(?P<code>\w+)/data.(?P<format>\w+)',measurementsummary, name='measurementsummary'),
]'''
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
import json
from django.utils.encoding import smart_unicode
from django.core.serializers import serialize
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, ADDITION
from django.db.models import Count,Avg,Min,Max,Variance, Q, Sum
from django.contrib import messages
from django.db import connection
import urllib2
from xml.dom.minidom import parse
from math import sin,acos,fabs,sqrt
from numpy import *
from astropy.io import fits 
from datetime import datetime,timedelta
from calendar import timegm
from time import mktime
from math import floor,pi,pow
from itertools import chain
from numpy import array,nan_to_num

from django.contrib.auth.models import User
from agentex.models import Target, Event, Datapoint, DataSource, DataCollection,CatSource, Decision, Achievement, Badge, Observer, AverageSet
from agentex.models import decisions
from agentex.forms import DataEntryForm, RegisterForm, CommentForm,RegistrationEditForm
import agentex.dataset as ds

from django.conf import settings
from agentex.agentex_settings import planet_level

guestuser = 2

def home(request):
    ''' Render the Front page of citizen science portal '''
    return render_to_response('index.html',context_instance=RequestContext(request))

def index(request):  
    return render_to_response('agentex/index.html', context_instance=RequestContext(request))

def briefing(request):
    return render_to_response('agentex/briefing.html', context_instance=RequestContext(request))

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        # Check if User has already registered with same username or email address
        if form.is_valid():
            user = User.objects.create_user(form.cleaned_data['username'],form.cleaned_data['emailaddress'],form.cleaned_data['password'])
            user.first_name=form.cleaned_data['firstname']
            user.last_name=form.cleaned_data['lastname']
            user.save()
            o = Observer(user=user)
            o.save()
            messages.success(request,"Your account has been created")
            new_user = authenticate(username=form.cleaned_data['username'],
                                    password=form.cleaned_data['password'])
            login(request, new_user)         
            next = request.GET.get('next','')
            if next:
                print next
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect(reverse('portal'))
        else:
            return render_to_response("register.html",{'form': form},context_instance=RequestContext(request))
    else:
        return render_to_response("register.html",{'form': RegisterForm()},context_instance=RequestContext(request))
        
@login_required
def editaccount(request):
    p = personcheck(request)
    if request.method == 'POST':
        form = RegistrationEditForm(request.POST)
        # Check if User has already registered with same username or email address
        user = p.user
        if form.is_valid():
            f = form.cleaned_data
            print f
            user.first_name=f['firstname']
            user.last_name=f['lastname']
            user.email=f['emailaddress']
            password =f['password']
            if password:
                user.set_password(password)
            user.save()
            messages.success(request,"Your account has been updated")
        # data = {'firstname' : p.user.first_name,'lastname' : p.user.last_name,'emailaddress':p.user.email,'password':p.user.password,'username':p.user.username}
        return render_to_response("register.html",{'form': form,'edit':True},context_instance=RequestContext(request))
    else:
        form = RegistrationEditForm({'firstname' : p.user.first_name,'lastname' : p.user.last_name,'emailaddress':p.user.email,'password':p.user.password})
        return render_to_response("register.html",{'form': form,'edit':True},context_instance=RequestContext(request))    

@login_required
def profile(request):
    a = Achievement.objects.filter(person=request.user).order_by('badge')
    nomeas = Datapoint.objects.filter(user=request.user).values('taken').annotate(Count('taken')).count()
    noplanet = DataCollection.objects.filter(person=request.user).values('planet').annotate(Count('person')).count()
    completed = DataCollection.objects.values('planet').filter(person=request.user).annotate(Count('complete')).count()
    #ndecs = Decision.objects.filter(person=request.user,planet=d[0].event,current=True).count()
    badgelist = Badge.objects.exclude(id__in=[b.badge.id for b in a]).order_by('name')
    return render_to_response("agentex/profile.html",{'unlocked':a,'badges':badgelist,'planets':noplanet,'measurements':nomeas,'completed':completed},context_instance=RequestContext(request))

#@login_required
def target(request):  
    data = []
    events = Event.objects.filter(enabled=True)
    for e in events:
        if (request.user.is_authenticated()):
            person = request.user
            completed = Datapoint.objects.filter(user=person, data__event__name=e,pointtype='S').count()
        else:
            person = guestuser
            completed = 0
        points =Datapoint.objects.filter(user=person,pointtype='S')
        try:
            level = planet_level[e.name]
        except:
            level = None
        line = {'event':e,'points':points,'completed':completed,'level':level}
        data.append(line)
    return render_to_response('agentex/target.html', {'data':data},context_instance=RequestContext(request))

@login_required
def addvalue(request,code):
    form = DataEntryForm()
    if (request.user.is_authenticated()):
        if request.user.username == 'admin':
            superuser = True
            sudo = request.GET.get('sudo','')
            if sudo:
                person = User.objects.get(id=sudo)
            else:
                person = request.user
        else:
            person = request.user
            superuser = False
    o = Observer.objects.filter(user=person)
    progress = checkprogress(person,code)
    if (progress['done'] >= progress['total']):
        dcolls = DataCollection.objects.filter(person=person,planet__name=code)
        dcolls.update(complete=True)
    ###### Has the user selected to use the web interface
    ###### Default for anonymous is always web interface
    if (person != guestuser):
        try:
            webin = o[0].dataexploreview
        except:
            webin = True
    else:
        webin = True
    least_coords = leastmeasured(code)
    if (request.POST):
    ####### Form data has been submitted
        x = []
        y = []
        nocals = request.POST.get('calibrators','1')
        setting = request.POST.get('entrytype','')
        # Only update the user's preference if they change it
        if (setting == 'manual' and o[0].dataexploreview == True):
            o.update(dataexploreview=False)
            messages.success(request, "Setting changed to use manual view")
            entrymode = 'M'
        elif (setting == 'dataexplorer' and o[0].dataexploreview == False):
            o.update(dataexploreview=True)
            messages.success(request, "Setting changed to use web view")
            entrymode = 'W'
        else:
            entrymode = 'N'
        id = request.POST.get('dataid','')
        form = DataEntryForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            ind = {'source':'S','bg':'B'}
            reduced = 0
            update = request.POST.get('update','')
            counts = list()
            for i in ind:
                value = float(cd[i+'counts'])
                x.append(cd[i+'xpos'])
                y.append(cd[i+'ypos'])
                counts.append(value)
            for vari in range(1,int(nocals)+1):
                cali = str(vari)
                value = request.POST.get('cal'+cali+'counts','')
                x.append(request.POST.get('cal'+cali+'xpos',''))
                y.append(request.POST.get('cal'+cali+'ypos',' '))
                counts.append(float(value))
            pointsum = {'bg' :  '%.2f' % counts[0], 'sc' : '%.2f' % counts[1], 'cal' : counts[2:]}
            if (len(x) < 3 or len(y) < 3):
                messages.warning(request,'Please submit calibration, blank sky and source apertures.')
                url = reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name])
                return HttpResponseRedirect(url)
            x = map(float,x)
            y = map(float,y)
            coords = zip(x,y)
            dataid = request.POST.get('dataid','')
            resp = savemeasurement(person,pointsum,coords,dataid,entrymode)
            messages.add_message(request, resp['code'], resp['msg'])
            if webin == False:
                url = "%s?%s" % (reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name]),"input=manual")
            else:
                url = reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name])
             #messages.success(request, "Measurement successfully added")
            return HttpResponseRedirect(url)
        else:
            return render_to_response('agentex/dataentry.html', {'data':DataSource.objects.get(id=id),'form':form,'data_url':settings.DATA_URL}, context_instance=RequestContext(request))
    else:
        nextcal = request.GET.get('next',False)
        ############ This condition is active when a user edits the frame
        # Find the data sources for the given code
        source = DataSource.objects.filter(event__name=code)
        length = source.count()
        # Pull out data user has viewed and exclude them from the list of possible candidates
        ds = Datapoint.objects.values_list('data',flat=True).filter(data__event__name=code,user=person,pointtype='S')
        input = request.GET.get('input',False)
        id = request.GET.get('dataid',False)
        # If an ID is specified return the frame, as long as the person has made measurements of it
        if id:
            dnext = False
            #### If anonymous user tell them they cannot edit points
            if person == guestuser:
                messages.warning(request,'You cannot edit points unless you are logged in')
                try:
                    url = reverse('agentex.views.addvalue',args= [DataSource.objects.get(id=id).event.name])
                    return HttpResponseRedirect(url)
                except:
                    raise Http404
            mycalibs = []
            ##### The page is being displayed with data for editing
            points = Datapoint.objects.filter(data__id=id,user=person)
            if nextcal=='cal':
                print "*******"
                dp = Datapoint.objects.filter(pointtype='S',user=person,data__id=id)
                dd = dp[0].data.timestamp
                ds = Datapoint.objects.filter(pointtype='S',user=person,data__timestamp__gt=dd).order_by('data__timestamp')
                if ds.count() > 0:
                    dnext = ds[0].data
            d = DataSource.objects.filter(id=id)[0]
            otherpoints = Datapoint.objects.filter(~Q(user=person),pointtype='C',data=d)
            cals = Datapoint.objects.values_list('xpos','ypos','radius').filter(data=d,pointtype='C').order_by('coorder__calid')
            calibs = []
            if cals:
                for c in cals:
                    calibs.append({'x' : int(c[0]) , 'y' : int(c[1]), 'r' : int(c[2])})
            source = points.filter(pointtype='S')[:1]
            bg = points.filter(pointtype='B')[:1]
            #### If there are no results, the person is hacking the query string. Return a fresh frame
            if (source.count() == 0 or bg.count() == 0):
                url = reverse('agentex.views.addvalue',args= [code])
                return HttpResponseRedirect(url)
            cal = points.filter(pointtype='C').order_by('coorder__calid')
            for c in cal:
                line = {'x' :c.xpos,'y' : c.ypos}
                mycalibs.append(line)
            ### If more cals have been placed on other frames add these to this frame
            max_cal = Datapoint.objects.filter(pointtype='C',user=person).aggregate(max=Max('coorder__calid'))['max']
            if max_cal+1 > cal.count():
                for order in range(cal.count(),max_cal+1):
                    dp = Datapoint.objects.filter(pointtype='C',user=person,coorder__calid=order,data__event__name=code)
                    if dp.count() > 0:
                        line = {'x': dp[0].xpos, 'y':dp[0].ypos}
                        # Add to the mycalibs array
                        mycalibs.append(line)
            coords = { 'source': {'x' :source[0].xpos,'y' : source[0].ypos},
                     'cal'  : mycalibs,
                     'bg'  : {'x' :bg[0].xpos,'y' : bg[0].ypos},
                     'radius' : source[0].radius,
                     'id'  : id,
                     'numcals' : len(mycalibs),
                     }
            messages.info(request, "Updating measurement")
            return render_to_response('agentex/dataentry.html',{'data':d,
                                                                    'next':dnext,
                                                                    'points':coords,
                                                                    'update':True,
                                                                    'webinput':webin,
                                                                    'progress':progress,
                                                                    'form':form,
                                                                    'calibrators':calibs,
                                                                    'least_data':least_coords,
                                                                    'data_url':settings.DATA_URL},
                                    context_instance=RequestContext(request))                             
        else:
            ######## User is being given a new frame not editing data  
            complete = 0
            if  (progress['done'] >= progress['total'] and person != guestuser):
                ####### No new data can be provided because the user has come to the end
                complete = 1
                numplanets = DataCollection.objects.values('planet').filter(person=person,complete=True).annotate(Count('complete')).count()
                e = Event.objects.filter(name=code)[0]
                resp = achievementscheck(person,e,0,0,0,0,numplanets)

                msg = '<br />'
                for item in resp:
                    if messages.SUCCESS == item['code'] :
                        msg += "<img src=\""+STATIC_URL+item['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />"
                        messages.success(request,msg)
                
                return HttpResponseRedirect(reverse('my-graph',args=[code]))

                return render_to_response('agentex/dataentry.html',
                                        {'event': e,
                                        'complete':complete,
                                        'progress':progress,
                                        'points':Datapoint.objects.filter(user=person,pointtype='S',data__event=e).order_by('data__timestamp'),
                                        'data_url':settings.DATA_URL,
                                        'numplanets':numplanets,},
                                        context_instance=RequestContext(request))            
            else:
                planet = Event.objects.get(name=code)
                mylist = Datapoint.objects.filter(user=person,pointtype='S',data__event=planet).values_list('data',flat=True)
                print mylist
                ### if person does not have a DataCollection it is their first measurement
                if (DataCollection.objects.filter(planet=planet,person=person).count() == 0):
                    d = DataSource.objects.filter(event=planet,id=planet.finder)[0]
                    did = d.id
                    try:
                        dold = d.id
                        first = True   
                    except:
                        messages.error(request,"Finderchart cannot be found")
                        raise Http404    
                elif  person == guestuser:
                    d = DataSource.objects.filter(event=planet).annotate(count=Count('datapoint')).order_by('-count')[0]
                    did = d.id
                    dold = d.id
                    first = True
                else:
                    try:
                        source_rank = DataSource.objects.filter(event=planet ).annotate(count=Count('datapoint') ).values_list('id','count').order_by('-count')  
                        available = [x for x in source_rank if x[0] not in list(mylist)]
                        dold = Datapoint.objects.values_list('data__id',flat=True).filter(user=person,data__event=planet,pointtype='C').annotate(max =Max('coorder__calid')).order_by('-max','-taken')[0]
                    # Find position in set of DataSources
                        d = available[0]
                        did = d[0]
                        first = False
                    except Exception,e:
                        print e
                        messages.error(request,"User has a data collection but no points!")
                        raise Http404
                cals = Datapoint.objects.values_list('xpos','ypos').filter(data=dold,pointtype='C',user=person).order_by('coorder__calid')
                calibs = []
                if cals:
                    for c in cals:
                        calibs.append({'x' : int(c[0]) , 'y' : int(c[1])})
                otherpoints = Datapoint.objects.filter(~Q(user=person),pointtype='C',data__id=did)
                othercals = []
                if otherpoints:
                    for c in otherpoints:
                        othercals.append({'x' : int(c.xpos) , 'y' : int(c.ypos),'r':int(c.radius)})
                prev = Datapoint.objects.filter(user=person,data=dold).order_by('coorder__calid')
                if first == False:
                    coords = { 'source': {'x' :prev.filter(pointtype='S')[0].xpos,'y' : prev.filter(pointtype='S')[0].ypos},
                             'bg'  : {'x' :prev.filter(pointtype='B')[0].xpos,'y' : prev.filter(pointtype='B')[0].ypos},
                             'cal'  : calibs ,
                             'id'  : dold,
                             'radius' : planet.radius
                             }
                else:
                    coords = False
                if person == guestuser:
                    progress = {'percent'   : "0",
                                'done'      : 0,
                                'total'     : n_sources,}
                return render_to_response('agentex/dataentry.html',
                                        {'data':DataSource.objects.get(id=did),
                                        'complete':complete,
                                        'update':False,
                                        'webinput':webin,
                                        'progress':progress,
                                        'form':form,
                                        'calibrators':othercals,
                                        'points':coords,
                                        'least_data':least_coords,
                                        'data_url':settings.DATA_URL},
                                        context_instance=RequestContext(request))        


def savemeasurement(person,pointsum,coords,dataid,entrymode):
    # Only update the user's preference if they change it
    o = Observer.objects.filter(user=person)
    try:
        if (entrymode == 'manual' and o[0].dataexploreview == True):
            o.update(dataexploreview=False)
            messages.success(request, "Setting changed to use manual view")
        elif (entrymode == 'dataexplorer' and o[0].dataexploreview == False):
            o.update(dataexploreview=True)
            messages.success(request, "Setting changed to use web view")
    except:
        print "Having problems with"
    mode = {'dataexplorer':'W','manual':'M'}
    pointtype = {'sc':'S','bg':'B'}
    d = DataSource.objects.filter(id=int(dataid))
    s_x = float(coords[1][0])
    s_y = float(coords[1][1])
    if d[0].id == d[0].event.finder:
        xvar = abs(s_x - d[0].event.xpos)
        yvar = abs(s_y - d[0].event.ypos)
        if (xvar > 3 or yvar > 3):
          # Remove previous values for this point
          return {'msg': 'Target marker not correctly aligned', 'code': messages.ERROR}
    xmean = 0
    ymean = 0 
    # Remove previous values for this point
    oldpoints = Datapoint.objects.filter(data=d[0],user=person)
    oldpoints.delete()
    numpoints = Datapoint.objects.filter(data__event=d[0].event,user=person).count()
    datestamp = datetime.now()
    reduced = 0
    calave = 0.
    error = ''
    ### Add a datacollection for the current user
    r = d[0].event.radius
    for k,value in pointtype.iteritems():
        # Background and source
        data = Datapoint(user=person,
                            pointtype = value,
                            data=d[0], 
                            radius=r,
                            entrymode=mode[entrymode],)
        if k == 'sc':
            coord = coords[1]
            data.offset = 0
        elif k == 'bg':
            coord = coords[0]
            data.offset = int(sqrt((s_x - float(coord[0]))**2 + (s_y - float(coord[1]))**2))
        data.value= float(pointsum[k])
        data.xpos = int(float(coord[0]))
        data.ypos = int(float(coord[1]))
        data.taken=datestamp
        try:
            data.save()
        except:
            return {'msg': 'Error saving data point', 'code': messages.ERROR}
    # Slice coord data so we only have calibration stars
    coord = coords[2:]
    basiccoord = array(coord[:3])
    nocals = len(coord)
    sc_cal = float(pointsum['sc']) - float(pointsum['bg'])
    # Find out if means have been calculated already, if not do it for the source
    # This step can only happen if we are not at the finder frame 
    if numpoints != 0 and d[0].event.finder != d[0].id:
        xmean, ymean = measure_offset(d,person,basiccoord)
        # check the source is within this tolerance too
        sc_xpos = d[0].event.xpos
        sc_ypos = d[0].event.ypos
        xvar = abs(abs(sc_xpos-s_x)-abs(xmean))
        yvar = abs(abs(sc_ypos-s_y)-abs(ymean))
        if (xvar > 5 or yvar > 5):
            # Remove previous values for this point
            oldpoints = Datapoint.objects.filter(data__id=int(dataid),user=person)
            oldpoints.delete()
            return {'msg': 'Target marker not correctly aligned', 'code': messages.ERROR}
    for i,value in enumerate(pointsum['cal']):
        xpos = int(float(coord[i][0]))
        ypos = int(float(coord[i][1]))
        newcoord = coord
        nocolls = DataCollection.objects.filter(planet=d[0].event,person=person,calid=i).count()
        if (nocolls == 0 and person != guestuser):
            ## Find closest catalogue sources
            if i > 2:
                # Add more datacollections if i is > 2 i.e. after basic 3 have been entered
                cats = CatSource.objects.filter(xpos__lt=xpos-xmean+5,ypos__lt=ypos-ymean+5,xpos__gt=xpos-xmean-5,ypos__gt=ypos-ymean-5,data__event=d[0].event)
            else:
                cats = CatSource.objects.filter(xpos__lt=xpos+5,ypos__lt=ypos+5,xpos__gt=xpos-5,ypos__gt=ypos-5,data__event=d[0].event)
            if cats:
                dcoll = DataCollection(person=person,planet=d[0].event,complete=False,calid=i,source=cats[0])
            else:
                dcoll = DataCollection(person=person,planet=d[0].event,complete=False,calid=i)
            dcoll.display = True
            dcoll.save()
        else:
            dcoll = DataCollection.objects.filter(person=person,planet=d[0].event,calid=i)[0]
        data = Datapoint(user=person,
                            pointtype = 'C',
                            data=d[0], 
                            radius=r,
                            entrymode=mode[entrymode])
        data.value= float(value)
        data.xpos = xpos
        data.ypos = ypos
        data.offset = int(sqrt((s_x - float(coord[i][0]))**2 + (s_y - float(coord[i][1]))**2))
        data.taken=datestamp
        data.coorder = dcoll
        try:
            data.save()
        except:
            return {'msg': 'Error saving', 'code': messages.ERROR}
        calave = calave +sc_cal/(value - float(pointsum['bg']))/float(nocals)
    else:
        #resp = achievementcheck(person,d[0].event,nocals,'calibrator')
        #nomeas = Datapoint.objects.filter(data__event__name=d[0].event,user=person).values('taken').annotate(Count('taken')).count()
        nomeas = Datapoint.objects.filter(user=person).values('taken').annotate(Count('taken')).count()
        noplanet = DataCollection.objects.filter(person=person).values('planet').annotate(Count('person')).count()
        ndecs = Decision.objects.filter(person=person,current=True).count() # filter: ,planet=d[0].event
        unlock = False
        nunlock = 0
        resp = achievementscheck(person,d[0].event,nomeas,noplanet,nocals,ndecs,0)
        msg = '<br />'
        for item in resp:
            if messages.SUCCESS == item['code'] :
                msg += "<img src=\""+STATIC_URL+item['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />"
                unlock = True
                nunlock += 1

        if unlock :
            if nunlock > 1 : return {'msg': 'Achievements unlocked'+msg, 'code': messages.SUCCESS}
            else : return {'msg': 'Achievement unlocked'+msg, 'code': messages.SUCCESS}
        return {'msg': 'Measurements saved', 'code': messages.SUCCESS}

def measure_offset(d,person,basiccoord):
    # Find the likely offset of this new calibrator compared to the basic ones and find any sources within 5 pixel radius search
    finderid = d[0].event.finder
    finderdp = Datapoint.objects.values_list('xpos','ypos').filter(user=person,data__id=finderid,pointtype='C',coorder__calid__lt=3).order_by('coorder__calid')
    finder = basiccoord - array(finderdp)
    t = transpose(finder)
    xmean = mean(t[0])
    ymean = mean(t[1])
    return xmean,ymean



def read_manual_check(request):
	if (request.POST.get('read_manual','')=='true' and request.user.is_authenticated()):
		o = personcheck(request)
		resp = achievementunlock(o.user,None,'manual')
		if messages.SUCCESS == resp['code'] :
			messages.add_message(request, messages.SUCCESS, "Achievement unlocked<br /><img src=\""+STATIC_URL+resp['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />")
		
	return HttpResponseRedirect(reverse('agentex.views.target'))
		


# measurements, planets, calibrators descisions
def achievementscheck(person,planet,nmeas,nplan,ncals,ndcsn,ncomp):
    resp = []
    if person.id!=guestuser:
        if nmeas == 1 : resp.append(achievementunlock(person,planet,'measurement_1'))
        if nmeas == 5 : resp.append(achievementunlock(person,planet,'measurement_5'))
        if nmeas == 10 : resp.append(achievementunlock(person,planet,'measurement_10'))
        if nmeas == 25 : resp.append(achievementunlock(person,planet,'measurement_25'))
        if nmeas == 50 : resp.append(achievementunlock(person,planet,'measurement_50'))
        if nmeas == 100 : resp.append(achievementunlock(person,planet,'measurement_100'))
        if nmeas == 250 : resp.append(achievementunlock(person,planet,'measurement_250'))
        if nmeas == 500 : resp.append(achievementunlock(person,planet,'measurement_500'))
        if nmeas == 1000 : resp.append(achievementunlock(person,planet,'measurement_1000'))
        if nmeas == 1500 : resp.append(achievementunlock(person,planet,'measurement_1500'))
        if nmeas == 2000 : resp.append(achievementunlock(person,planet,'measurement_2000'))
        if ncals >= 3 : resp.append(achievementunlock(person,planet,'calibrator_3'))
        if ncals >= 5 : resp.append(achievementunlock(person,planet,'calibrator_5'))
        if ncals >= 10 : resp.append(achievementunlock(person,planet,'calibrator_10'))
        if ncals >= 15 : resp.append(achievementunlock(person,planet,'calibrator_15'))
        if ncals >= 25 : resp.append(achievementunlock(person,planet,'calibrator_25'))
        if nplan == 1 : resp.append(achievementunlock(person,planet,'planet_1'))
        if nplan == 2 : resp.append(achievementunlock(person,planet,'planet_2'))
        if nplan == 3 : resp.append(achievementunlock(person,planet,'planet_3'))
        if nplan == 4 : resp.append(achievementunlock(person,planet,'planet_4'))
        if nplan == 5 : resp.append(achievementunlock(person,planet,'planet_5'))
        if nplan == 6 : resp.append(achievementunlock(person,planet,'planet_6'))
        if nplan == 7 : resp.append(achievementunlock(person,planet,'planet_7'))
        if nplan == 8 : resp.append(achievementunlock(person,planet,'planet_8'))
        if nplan == 9 : resp.append(achievementunlock(person,planet,'planet_9'))
        if ndcsn >= 3 : resp.append(achievementunlock(person,planet,'lightcurve_1star'))
        if ndcsn >= 10 : resp.append(achievementunlock(person,planet,'lightcurve_2star'))
        if ncomp == 1 : resp.append(achievementunlock(person,planet,'completed_1'))
        if ncomp == 2 : resp.append(achievementunlock(person,planet,'completed_2'))
        if ncomp == 3 : resp.append(achievementunlock(person,planet,'completed_3'))
        if ncomp == 4 : resp.append(achievementunlock(person,planet,'completed_4'))
        if ncomp == 5 : resp.append(achievementunlock(person,planet,'completed_5'))
        if ncomp == 6 : resp.append(achievementunlock(person,planet,'completed_6'))
        if ncomp == 7 : resp.append(achievementunlock(person,planet,'completed_7'))
        if ncomp == 8 : resp.append(achievementunlock(person,planet,'completed_8'))
        if ncomp == 9 : resp.append(achievementunlock(person,planet,'completed_9'))
    
    return resp


def achievementunlock(person,planet,typea):
    # Check what badges user has to see if they deserve more
    # The planet will simply be to record where they got this achievement
    achs = Achievement.objects.filter(person=person) #,planet=planet
    badge =  Badge.objects.filter(name=typea)
    if badge.count() == 0:
        return {'msg' : 'Wrong badge code', 'code': messages.ERROR}
    if achs.filter(badge=badge).count() == 0:
        newa = Achievement(badge=badge[0],planet=planet,person=person)	# ,planet=planet
        try:
            newa.save()
            LogEntry.objects.log_action(
                user_id         = person.id, 
                content_type_id = ContentType.objects.get_for_model(newa).pk,
                object_id       = newa.pk,
                object_repr     = smart_unicode(newa), 
                action_flag     = ADDITION,
                change_message  = 'Achievement automatically unlocked'
            )
            return {'msg': 'Achievement unlocked', 'image':"%s" % badge[0].image, 'code': messages.SUCCESS }
        except:
            return {'msg' : 'Achievement save error', 'image':"%s" % badge[0].image, 'code': messages.ERROR }
    else:
        return {'msg' : 'Already has this badge', 'image': '', 'code': messages.WARNING }

def classifyupdate(request,code):
    if (request.POST):
        resp = addvalidset(request,code)
        if resp:
            msg = {'update':False}
        else:
            msg = {'update': True}
    else:
        msg = {'update':False}
    #messages.warning(request,msg)
    return HttpResponse(json.dumps(msg),mimetype='application/javascript')

def updatedataset(request,code):
    formdata = request.POST
    option = request.GET.get('mode','')
    if (formdata and option == 'display'):
        resp = updatedisplay(request,code)
        url = reverse('my-graph',args= [code])
        if resp:
            messages.warning(request,'Your preferences have not been saved.')
        else:
            messages.success(request,'Your display setting has been saved.')
    elif (formdata and option == 'valid'):
        resp = addvalidset(request,code)
        if resp:
            messages.warning(request,'None of your lightcurves have been saved.')
        else:
            messages.success(request,'Your selected classification has been saved.')
        url = reverse('average-graph',args= [code])
    else:
        messages.warning(request,'Nothing to save')
    return HttpResponseRedirect(url)

def updatedisplay(request,code):
    # Wipe all the validations for user and event
    o = personcheck(request)
    dc = DataCollection.objects.filter(person=o.user,planet=Event.objects.get(name=code),complete=True)
    dc.update(display = False)
    empty = True
    formdata = request.POST
    for i,val in formdata.items():
        if i[4:] == val:
            # Add validations back one by one
            col = dc.filter(calid=val)
            col.update(display= True)
            empty = False
    return empty

def addvalidset(request,code):
    o = personcheck(request)
    calid = request.POST.get('calid','')
    choice1 = request.POST.get('choice1','')
    choice2 = request.POST.get('choice2','')
    point = DataCollection.objects.filter(person=o.user,calid=calid,planet__name=code)
    planet = Event.objects.filter(name=code)[0]
    if choice1 and point and calid:
        value = decisions[choice1]
        source = point[0].source
        old = Decision.objects.filter(person=o.user,planet=planet,source=source)
        old.delete()
        decision1 = Decision(source=source,
                        value=value,
                        person=o.user,
                        planet=planet)
        
        if choice2:
            value2 = decisions[choice2]
            decision2 = Decision(source=source,
                            value=value2,
                            person=o.user,
                            planet=planet,
                            current=True)
            decision2.save()
        else:
            decision1.current = True
        decision1.save()
        return False
    else:
        return True
        
@login_required
def my_data(o,code):
    data = []
    sources = DataSource.objects.filter(event__name=code).order_by('timestamp')
    points  = Datapoint.objects.filter(data__event__name=code,user=o.user)
    for s in sources:
        ps = points.filter(data=s)
        myp = ps.filter(pointtype='S')
        try:
            mypoint = '%f' % myp[0].value
        except:
            mypoint = 'null'
        cals = ps.filter(pointtype='C').values_list('value',flat=True).order_by('coorder')
        line = {
                'id'        : "%i" % s.id,
                'date'      : s.timestamp.isoformat(" "),
                'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                'data'      : { 'source' : list(ps.filter(pointtype='S').values_list('value',flat=True)),
                                'background' :  list(ps.filter(pointtype='B').values_list('value',flat=True)),
                                'calibrator' :  list(cals),
                            },
                }
        data.append(line)
    return data,points
    
def calibrator_data(calid,code):
    data = []
    sources, times = zip(*DataSource.objects.filter(event__name=code).values_list('id','timestamp').order_by('timestamp'))
    points  = Datapoint.objects.filter(data__in=sources)
    #points.filter(pointtype='C').values('data__id','user','value')
    people = Decision.objects.filter(source__id=calid,planet__name=code,value='D',current=True).values_list('person__username',flat=True).distinct()
    norm = dict((key,0) for key in sources)
    for pid in people:
        cal = []
        sc = dict(points.filter(user__username=pid,pointtype='S').values_list('data__id','value'))
        bg = dict(points.filter(user__username=pid,pointtype='B').values_list('data__id','value'))
        c = dict(points.filter(user__username=pid,pointtype='C',coorder__source__id=calid).values_list('data__id','value'))
        sc_norm = dict(norm.items() + sc.items())
        bg_norm = dict(norm.items() + bg.items())
        c_norm = dict(norm.items() + c.items())
        #print sc_norm,bg_norm,c_norm
        for v in sources:
            try:
                cal.append((sc_norm[v]- bg_norm[v])/(c_norm[v] - bg_norm[v]))
            except:
                cal.append(0)
        data.append(cal)
    return data,[timegm(s.timetuple())+1e-6*s.microsecond for s in times],list(people)
        
@login_required  
def graphview(request,code,mode,calid):
    #measurement = Datapoint.objects.filter(taken=date,data__event__name=code)
    #calibrate(measurement)
    o = personcheck(request)
    progress = checkprogress(o.user,code)
    n = 0
    if mode == 'simple':
        d1 = ds.Dataset(code,o.user.username)
        data,points = d1.my_data()#my_data(o,code)
        dc = DataCollection.objects.filter(person=o.user,planet=d1.planet)
        if dc.count() > n:
            n = range(0,dc.count())
            cats = []
            for order in n:
                try:
                    ## Sometimes the sequence of calibrators is not continuous 0..n  -- BUG
                    dc0 = dc.filter(calid=order)[0]
                    c = points.filter(pointtype='C',coorder=dc0)[:1]
                    valid = c[0].coorder.display
                    coll = {'order' : order,
                            'name'  : c[0].coorder.source,
                            'valid' : valid,
                            }
                    cats.append(coll)
                except:
                    pass
        else:
            cats = None
        classif = classified(o,code)
        return render_to_response('agentex/graph_flot.html', {'event':d1.planet,
                                                                'data':data,
                                                                'n':n,
                                                                'sources':cats,
                                                                'classified':classif,
                                                                'progress' : progress,
                                                                'target':DataSource.objects.filter(event__name=code)[0].target}, 
                                                                context_instance=RequestContext(request))
    elif mode == 'ave':
        data = []
        # get and restructure the average data JS can read it nicely
        now = datetime.now()
        cals,normcals,sb,bg,dates,stamps,ids,cats = photometry(code,o.user,progress) 
        numcals = len(normcals)
        print normcals
        for i,id in enumerate(ids):
            #mycalibs = []
            calibs = []
            normcalibs = []
            for j in range(0,numcals):
                calibs.append([cals[j][i],cats[j]['order']])
                #mycalibs.append(mycals[j][i])
                normcalibs.append(normcals[j][i])
            line = {
                    'id'        : id,
                    'date'      : dates[i],
                    'datestamp' : stamps[i],
                    'data'      : { 'source' : sb[i],
                                    'background' :  bg[i],
                                    'calibration' :  normcalibs,
                                    #'mycals'     :  mycalibs,
                                    'calibrator' : calibs,
                                },
                    }
            data.append(line)
        planet = Event.objects.filter(name=code)[0]        
        ### Make sure person gets a different calibrator (that they haven't classified) after each POST
        currentcal = None
        dec = Decision.objects.values('source__name').filter(person=o.user,planet__name=code,value__in=['D','N','B','P','R','S'],current=True).annotate(count=Count('source')).order_by('count')
        if calid:
            for cat in cats:
                # Which calibrator is being requested, if one is requested
                if int(cat['order']) == int(calid)-1:
                    currentcal = {'order': cat['order'], 'sourcename' : "%s" % cat['sourcename'],'total':len(cats),'progress':dec.count()}  
        else:
            if dec.count() == 0 and cats:
                currentcal = {'order': cats[0]['order'], 'sourcename' : "%s" % cats[0]['sourcename'], 'total':len(cats),'progress':dec.count()}
            elif dec.count() < len(cats):
                tmp, declist = zip(*dec.values_list('count','source__name'))
                for cat in cats:
                    if (cat['sourcename']  not in declist):
                        currentcal = {'order': cat['order'], 'sourcename' : "%s" % cat['sourcename'], 'total':len(cats),'progress':dec.count()}
            elif dec:
                for cat in cats:
                    if cat['sourcename'] == dec[0]['source__name']:
                        currentcal = {'order': cat['order'], 'sourcename' : "%s" % cat['sourcename'], 'total':len(cats),'progress':dec.count()}
        if currentcal:
            ## Send decision person made last time they were here
            mychoice = Decision.objects.values('value').filter(person=o.user,planet__name=code,value__in=['D','N','B','P','R'],source__name=currentcal['sourcename'])
            if mychoice:
                choice = mychoice.latest('taken')
                rev_dec = dict((v,k) for k, v in decisions.iteritems())
                prev = rev_dec[choice['value']]
            else:
                prev = None
            # How many have I classified
        elif len(cats) == 0 and calid == None:
            prev = None
        else:
            messages.error(request,'The lightcurve using the selected calibrator is not complete')
            return HttpResponseRedirect(reverse('average-graph',args=[planet.name]))
        #print datetime.now() - now
        classif = classified(o,code)
        resp = achievementscheck(o.user,planet,0,0,0,len(cats),0)
        unlock = False
        nunlock = 0
        msg = '<br />'
        
        for item in resp:
            if messages.SUCCESS == item['code'] :
                msg += "<img src=\""+STATIC_URL+item['image']+"\" style=\"width:96px;height:96px;\" alt=\"Badge\" />"
                unlock = True
                nunlock += 1

        if unlock :
            if nunlock > 1 : msg = 'Achievements unlocked'+msg
            else : msg = 'Achievement unlocked'+msg
            messages.add_message(request, messages.SUCCESS, msg)
        print classif
        return render_to_response('agentex/graph_average.html', {'event': planet,
                                                                'data':data,
                                                                'sources':cats,
                                                                'cals':json.dumps(cats),
                                                                'calid': currentcal,
                                                                'prevchoice' : prev,
                                                                'classified':classif,
                                                                'progress' : progress,
                                                                'target':DataSource.objects.filter(event=planet)[0].target},
                                                                context_instance=RequestContext(request))
            
    elif mode == 'advanced':
        opt = {'S' :'source','C':'calibrator','B':'sky'}
        if 'dataid' in request.GET:
            dataid = request.GET.get('dataid','')
        else:    
            dataid = Datapoint.objects.filter(user=o[0].user).order_by('taken')[0].data.id
        try:
            s = DataSource.objects.filter(id=dataid)[0]
        except:
            raise Http404  
        ps  = Datapoint.objects.filter(~Q(pointtype = 'R'),data = s).order_by('-pointtype')
        datalist = [{'mine': ismypoint(o[0],dp.user),'x' : dp.xpos,'y' : dp.ypos, 'r' : dp.radius, 'value' : "%.0f" % dp.value,'type':opt[dp.pointtype]} for dp in ps]
        line = {
                'id'        : "%i" % s.id,
                'date'      : s.timestamp.isoformat(" "),
                'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                'data'      : datalist,
                }
        return render_to_response('agentex/graph_advanced.html', {'event':Event.objects.filter(name=code)[0],
                                                                        'framedata':line,
                                                                        'target':DataSource.objects.filter(event__name=code)[0].target,
                                                                        'progress' : progress}, context_instance=RequestContext(request))

def graphsuper(request,code):
    # Construct the supercalibrator lightcurve
    ds1 = ds.Dataset(planetid=code,userid=request.user.username)
    data = ds1.final()
    ###### Setting nodata to True and not showing each person their own data, but just for now
    return render_to_response('agentex/graph_super.html', {'event':ds1.planet,
                                                                'data':data,
                                                                'numsuper':13,
                                                                'target':ds1.target,
                                                                'nodata' : True}, context_instance=RequestContext(request))

def infoview(request,code):
    ds = DataSource.objects.filter(event__name=code)[:1]
    
    if request.user.is_authenticated():
        person = personcheck(request)
        progress = checkprogress(person,code)
    else:
        progress = None
    print progress
    try:
        data = ds[0]
    except:
        raise Http404
    return render_to_response('agentex/info.html', {'object' : data, 'progress' : progress}, context_instance=RequestContext(request))
    
def fitsanalyse(request):
    now = datetime.now()
    if (request.user.is_authenticated()):
        person=request.user
    else:
        person = User.objects.filter(id=guestuser)[0]
    # Flag poor quality result
    #print datetime.now() - now
    flag = ''
    # Extract variables passed from the image
    # Order of variables sent is 'bg','source','cal1','cal2'...
    x = request.POST.get('x','').split(',')
    y = request.POST.get('y','').split(',')
    if (len(x) < 3 or len(y) < 3):
        response = {'message' : 'Please submit calibration, blank sky and source apertures.'}
        return HttpResponse(json.dumps(response),mimetype='application/javascript')
    x = map(float,x)
    y = map(float,y)
    coords = zip(x,y)
    dataid = request.POST.get('dataid','')
    linex = list()
    liney = list()
    counts = list()

    ###########
    # Validate the input data
    # Check radius is less than a max size so the server does not have too much load
    # ***** No longer used as we fix radius from the outset ****
    #if r >= 70:
    #    response = {'message' : 'Apertures are too large. Please make your circles smaller'}
    #    return HttpResponse(json.dumps(response),mimetype='application/javascript')
    # Check all apertures are away from frame edge
    d = DataSource.objects.filter(id=int(dataid))[:1]
    r = d[0].event.radius
    for co in coords:
        xi = co[0]
        yi = co[1]
        if (xi-r < 0 or xi+r >= d[0].max_x or yi-r < 0 or yi+r > d[0].max_y ):
            response = {'message' : 'Please make sure your circles are fully within the image'}
            return HttpResponse(json.dumps(response),mimetype='application/javascript')

    #print datetime.now() - now
    # Grab a fits file
    dfile = "%s%s" % (settings.DATA_LOCATION,d[0].fits)
    #print dfile
    dc = fits.getdata(dfile,header=False)
    #print datetime.now() - now
    
    # Find all the pixels a radial distance r from x0,y0
    for co in coords:
        x0 = int(floor(co[0]))
        y0 = int(floor(co[1]))
        # Sum for this aperture
        sum = 0
        numpix = 0
        ys = y = y0 -r
        ye = y0 +r
        vline = list()
        hline = list()
        while (y < ye):
            angle = fabs(1.*(y-y0)/r)
            dx = int(sin(acos(angle))*r)
            x = xs = x0 - dx
            xe = x0 + dx
            while (x < xe):
                sum += float(dc[y][x])
                x += 1
                if (x == x0):
                    hline.append(float(dc[y][x]))
                if (y == y0):
                    vline.append(float(dc[y][x]))
                    #print "x = %s, y= %s val=%s" % (x,y,float(dc[y][x]))
                numpix += 1
            y += 1
        linex.append(hline)
        liney.append(vline)
        counts.append(sum)
    #print datetime.now() - now
    
    # Send back the raw total counts. Analysis can be done when the graph is produced.
    pointsum = {'bg' :  '%.2f' % counts[0], 'sc' : '%.2f' % counts[1], 'cal' : counts[2:]}
    lines = {'data' : {
               'coords' : {'xy' : coords,'r':r},
                'sum'   : pointsum,
                'points' : {'bg':
                                {'horiz' : linex[0],
                                'vert' : liney[0],
                                },
                            'sc':
                                {'horiz' : linex[1],
                                'vert' : liney[1],
                                },
                            'cal':
                                {'horiz' : linex[2:],
                                'vert' : liney[2:],
                                },
                            },
                #'quality' : flag,
               'pixelcount' : numpix,
                },
            }
    #print (datetime.now() - now)
    # save measurement data on the backend automatically
    entrymode = request.POST.get('entrymode','M')
    resp = savemeasurement(person,pointsum,coords,dataid,entrymode)
    if  resp['code'] == messages.ERROR:
        lines = {'error':  resp['msg']}
    else:
        messages.add_message(request, resp['code'], resp['msg'])
    return HttpResponse(json.dumps(lines,indent = 2),mimetype='application/javascript')
        
def measurementsummary(request,code,format):
    ####################
    # Return a measument data set based on event code and having either 'json' or 'xml' format
    data = []
    maxpixel = 1024
    csv =""
    if (request.user.is_authenticated()):
        o = Observer.objects.filter(user=request.user)
    else:
        o = Observer.objects.filter(user=guestuser)
    options = request.GET.get('mode','')
    if (format == 'xhr' and options ==''):
        #cals = []
        sources = []
        dates = []
        stamps = []
        rawcals = []
        timestamps = []
        cals = []
        mypoints = Datapoint.objects.filter(user=o[0].user,data__event__name=code).order_by('data__timestamp')
        for d in mypoints.filter(pointtype='S'):
            dates.append(d.data.timestamp.isoformat(" "))
            stamps.append(timegm(d.data.timestamp.timetuple())+1e-6*d.data.timestamp.microsecond)
            timestamps.append(d.data.timestamp)
        sources = array(mypoints.filter(pointtype='S').values_list('value',flat=True))
        ids = mypoints.filter(pointtype='S').values_list('data__id',flat=True)
        bg = array(mypoints.filter(pointtype='B').values_list('value',flat=True))
        sb = sources -bg
        cs = mypoints.filter(pointtype='C').order_by('coorder__calid')
        maxcals = cs.aggregate(Max('coorder__calid'))['coorder__calid__max']
        if maxcals == None:
            maxcals = -1
        for i in range(0,maxcals+1):
            vals = []
            for d,item in enumerate(ids):
                cp = cs.filter(data__timestamp=timestamps[d])
                if len(cp) > i:
                    vals.append(sb[d]/(cp[i].value-bg[d]))
                else:
                    vals.append(0.0)
            maxvals = r_[vals[:3],vals[-3:]]
            nz = maxvals.nonzero()
            maxval = mean(maxvals[nz])
            cals.append(list(vals/maxval))
        datapoints = {'calibration' : cals, 'source' : list(sources),'background':list(bg),'dates':dates,'id':list(ids),'datestamps':stamps,'n':maxcals+1}
        dataid = request.GET.get('dataid','')
        return HttpResponse(json.dumps(datapoints,indent=2),mimetype='application/javascript')
    elif (format == 'xhr' and options=='ave'):
        #cals = []
        #cs = mypoints.filter(pointtype='C').order_by('coorder__calid')
        maxcals = DataCollection.objects.filter(person=o[0].user,planet__name=code).aggregate(Max('calid'))['calid__max']
        if maxcals:
            # cals,normcals,mycals,sb,bg,dates,stamps,ids,cats = myaverages(code, o[0].user)
            cals,normcals,sb,bg,dates,stamps,ids,cats = averagecals(code, o[0].user)
            # datapoints = {'calibration' : normcals, 'mycals': mycals,'source' : sb,'background':bg,'calibrator':cals,'dates':dates,'id':ids,'datestamps':stamps,'n':maxcals+1}
            datapoints = {'calibration' : normcals, 'source' : sb,'background':bg,'calibrator':cals,'dates':dates,'id':ids,'datestamps':stamps,'n':maxcals+1}
        else:
            datapoints = {'calibration':None}
        return HttpResponse(json.dumps(datapoints,indent=2),mimetype='application/javascript')
    elif (format == 'xhr' and options == 'super'):
        # Construct the supercalibrator lightcurve
        planet = Event.objects.filter(name=code)[0]
        numsuper, normvals, std,radiusratio = supercaldata(planet)
        sources = DataSource.objects.filter(event=planet).order_by('timestamp')
        dates = []
        for s in sources:
            dates.append(timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,)
        datapoints = {'normalised' : normvals, 'dates':dates, 'std':std}
        return HttpResponse(json.dumps(datapoints),mimetype='application/javascript')
    elif (request.GET and format == 'json'):
        dataid = request.GET.get('dataid','')
        s = DataSource.objects.filter(id=dataid)[0]
        ps  = Datapoint.objects.filter(~Q(pointtype = 'R'),data = s).order_by('-pointtype')
        datalist = [{'mine': ismypoint(o[0],dp.user),'x' : dp.xpos,'y' : dp.ypos, 'r' : dp.radius, 'value' : dp.value,'type':dp.pointtype} for dp in ps]
        line = {
                'id'        : "%i" % s.id,
                'date'      : s.timestamp.isoformat(" "),
                'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                'data'      : datalist,
                }
        return HttpResponse(json.dumps(line,indent = 2),mimetype='application/javascript')
    else:
        planet = Event.objects.filter(name=code)[0]
        numsuper, normvals, myvals, std,radiusratio = supercaldata(request.user,planet)
        sources = DataSource.objects.filter(event=planet).order_by('timestamp')
        n = 0
        if format == 'json':
            data = []
            if len(normvals) == planet.numobs :
                for i,s in enumerate(sources):
                    line = {
                            'id'        : "%i" % s.id,
                            'date'      : s.timestamp.isoformat(" "),
                            'datestamp' : timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,
                            'data'      : {
                                            'mean' : normvals[i],
                                            'std'  : std[i],
                                            'mine' : myvals[i],
                                },
                            }
                    data.append(line)
            else:
                data = None
            return HttpResponse(json.dumps(data,indent = 2),mimetype='application/javascript')
        # elif format == 'xml':
        #     return render_to_response('agentex/data_summary.xml',{'data':data},mimetype="application/xhtml+xml")
        elif format == 'csv':
            csv = "# Date of observation, Unix timestamp, normalised average values, standard deviation, my normalised values\n"
            for i,s in enumerate(sources):
                csv += "%s, %s, %s, %s, %s\n" % (s.timestamp.isoformat(" "),timegm(s.timestamp.timetuple())+1e-6*s.timestamp.microsecond,normvals[i],std[i],myvals[i])
            return HttpResponse(csv,mimetype='text/csv')

def calibratemydata(code,user):
    #cs = Datapoints.objects.filter(pointtype='C',user=user).order_by('coorder__calid')
    ds = DataSource.objects.filter(event__name=code).order_by('timestamp')
    stars = DataCollection.objects.filter(planet__name = code,person=user).values_list('source',flat=True)
    cals = []
    # mycals = []
    # dates = []
    # stamps = []
    # timestamps = []
    # ids = []
    # scA = []
    # bgA = []
    for i,st in enumerate(stars):
        vals = []
        #myvals = []
        for d in ds:
            points = Datapoint.objects.filter(data=d)
            cp = points.filter(pointtype='C',coorder__source=st).aggregate(ave=Avg('value'))['ave']
            sb = points.filter(pointtype='S').aggregate(ave=Avg('value'))['ave']
            bg = points.filter(pointtype='B').aggregate(ave=Avg('value'))['ave']
            if cp:
                vals.append((sb-bg)/(cp-bg))
            else:
                vals.append(0.0)
            mypoint = points.filter(user=user)
            if mypoint:
                vals.append((sb-bg)/(mypoint[0].value-bg))
            else:
                vals.append('0.0')
        maxval = max(vals)
        #nz = maxvals.nonzero()
        #maxval = mean(maxvals)
        cals.append(list(vals/maxval)) 
        #mycals.append(list(myvals/maxval))
    return mycals
    
def myaverages(code,person):
    ds = DataSource.objects.filter(event__name=code).order_by('timestamp').values_list('id',flat=True)
    valid_user = False
    if person:
        if person.is_authenticated():
            valid_user = True
    if valid_user:
        now = datetime.now()
        cals = []
        mycals = []
        dates = []
        stamps = []
        timestamps = []
        normcals = []
        maxvals = []
        cats = []
        # Find which Cat Sources I have observed and there is a complete set of (including other people's data)
        # Unlike CalibrateMyData it only includes set where there are full sets
        e = Event.objects.filter(name=code)[0]
        dc = DataCollection.objects.filter(~Q(source=None),person=person,planet=e).order_by('calid')
        cs = CatSource.objects.filter(id__in=[c.source.id for c in dc]).annotate(count=Count('datacollection__datapoint')).filter(count__gte=e.numobs).values_list('id',flat=True)
        mydecisions = Decision.objects.filter(person=person,current=True,planet=e,value='D').values_list('source__id',flat=True)
        if cs.count() > 0:
            # Only use ones where we have more than numobs
            for c in dc:
                # make sure these are in the mydecision list (i.e. I've said they have a Dip)
                if c.source.id in mydecisions:
                    v = Datapoint.objects.filter(coorder__source=c.source.id,pointtype='C',user=person).order_by('data__timestamp').values_list('data__id','value')
                    cals.append(dict(v))
            if cals:
                # Only proceed if we have calibrators in the list (i.e. arrays of numobs)
                points = Datapoint.objects.filter(user=person,data__event__name=code).order_by('data__timestamp')
                scA = points.filter(pointtype='S').values_list('data__id','value')
                bgA = points.filter(pointtype='B').values_list('data__id','value')
                # Create a list of normalised values with gaps if I haven't done the full dataset but have contributed to a 'Dip' classification
                sc=dict(scA)
                bg=dict(bgA)
                sc = dictconv(sc,ds)
                sc = array(sc)
                bg = dictconv(bg,ds)
                bg = array(bg)
                for cal in cals:
                    val = (sc - bg)/(array(dictconv(cal,ds))-bg)
                    val = nan_to_num(val)
                    normcals.append(val)
                normmean = mean(normcals,axis=0)
                return list(normmean/max(normmean))
    # If they have no 'D' decisions
    return [0.]*ds.count()
    
def calibrator_averages(code,person=None,progress=False):
    cals = []
    cats = []
    planet = Event.objects.get(name=code)
    sources = list(DataSource.objects.filter(event=planet).order_by('timestamp').values_list('id','timestamp'))
    ids,stamps = zip(*sources)
    if person:
        ## select calibrator stars used, excluding ones where ID == None, i.e. non-catalogue stars
        dc = DataCollection.objects.filter(~Q(source=None),person=person,planet=planet).order_by('calid')
        ## Measurement values only for selected 'person'
        dps = Datapoint.objects.filter(data__event=planet,user=person).order_by('data__timestamp')
    else:
        # select calibrator stars used, excluding ones where ID == None, i.e. non-catalogue stars
        dc = DataCollection.objects.filter(~Q(source=None),planet=planet).order_by('calid')
        ## Measurement values only for selected 'person'
        dps = Datapoint.objects.filter(data__event=planet).order_by('data__timestamp')
    averages = AverageSet.objects.filter(planet=planet)
    if person:
        # Make a combined list of source values
        measurements = dps.filter(pointtype='S')
        sc = average_combine(measurements,averages,ids,None,'S',progress)
        # Make a combined list of background values
        measurements = dps.filter(pointtype='B')
        bg = average_combine(measurements,averages,ids,None,'B',progress)
    else:
        sc = array(averages.filter(star=None,settype='S')[0].data)
        bg = array(averages.filter(star=None,settype='B')[0].data)
    # Make a combined list of all calibration stars used by 'person'
    for calibrator in dc:
        if person:
            measurements = dps.filter(pointtype='C',coorder=calibrator)
            ave = average_combine(measurements,averages,ids,calibrator.source,'C',progress)
        else:
            ave_cal = averages.filter(star=calibrator,settype='C')
            if ave_cal.count() > 0:
                ave = array(ave_cal[0].data)
            else:
                ave = array([])
        if ave.size > 0:
            cals.append(ave)
            try:
                if person:
                    decvalue = Decision.objects.filter(source=calibrator.source,person=person,planet=planet,current=True)[0].value
                else:
                    decvalue = Decision.objects.filter(source=calibrator.source, planet=planet,current=True)[0].value
            except:
                decvalue ='X'
            cat_item = {'sourcename':calibrator.source.name,'catalogue':calibrator.source.catalogue}
            cat_item['decsion'] = decvalue
            cat_item['order'] = str(calibrator.calid)
            cats.append(cat_item)
    return cals,sc,bg,stamps,ids,cats
    
def average_combine(measurements,averages,ids,star,category,progress,admin=False):
    if progress['done'] < progress['total']:
        ave_measurement = averages.filter(star=star,settype=category)
        if ave_measurement.count() > 0:
            ## Find the array indices of my values and replace these averages
            ave = array(ave_measurement[0].data)
            mine = zip(*measurements.values_list('data','value'))
            try:
                my_ids = [ids.index(x) for x in mine[0]]
                ave[my_ids] = mine[1]
            except Exception, e:
                print e
            return ave
        else:
            return array([])
    elif progress['done'] == progress['total']:
        mine = array(measurements.values_list('value',flat=True))
        return mine
    elif not progress:
        print "No progress was passed"
        return array([])
    else:
        print "Error - too many measurements: %s %s" % (measurements.count() , numobs)
        return array([])
        
def admin_averagecals(code,person):
    # Uses and SQL statement to try to speed up the query for averaging data points
    # If person == 0 this will return all calibrator values individually - for problem solving
    now = datetime.now()
    cals = []
    mycals = []
    dates = []
    stamps = []
    timestamps = []
    normcals = []
    maxvals = []
    callist = []
    cats = []
    # Find which Cat Sources I have observed and there is a complete set of (including other people's data)
    # Unlike CalibrateMyData it only includes set where there are full sets
    e = Event.objects.filter(name=code)[0]
    if person == 0:
        dc = DataCollection.objects.filter(~Q(source=None),planet__name=code).values_list('source__id',flat=True).distinct()
        cs = CatSource.objects.filter(id__in=[c for c in dc]).annotate(count=Count('datacollection__datapoint')).filter(count__gte=e.numobs).values_list('id',flat=True).distinct()
        dcall = DataCollection.objects.filter(planet=e,source__in=cs).values_list('id',flat=True)
        # print "** Collections %s" % dcall.count()
        if cs.count() > 0:
            # Only use ones where we have more than numobs
            for c in dc:
                # make sure these are in the CatSource list (can't use cs because the order isn't right)
                if c in cs:
                    people = Decision.objects.filter(source__id=c,current=True,value='D').values_list('person',flat=True)
                    if people:
                        v = Datapoint.objects.filter(coorder__source=c,pointtype='C',user__id__in=people).order_by('data__timestamp').values_list('data__id').annotate(Avg('value'))
                    else:
                        v = Datapoint.objects.filter(coorder__source=c,pointtype='C').order_by('data__timestamp').values_list('data__id').annotate(Avg('value'))
                    # Double check we have same number of obs and cals
                    if v.count() == e.numobs:
                        ids,b = zip(*v)
                        cals.append(list(b))
                        decvalue_full = Decision.objects.filter(source=c,planet__name=code,current=True).values_list('value').annotate(total=Count('id')) 
                        decvalue = dict((str(key),value) for key,value in decvalue_full)                          
                        source = CatSource.objects.get(id=c)
                        cat_item = {'sourcename':str(source.name),'catalogue':str(source.catalogue),'sourceid': str(c),'include':source.final}
                        cat_item['decisions'] = decvalue
                        cats.append(cat_item)
                        callist.append(c)
    else:
        dc = DataCollection.objects.filter(~Q(source=None),person=person,planet__name=code).order_by('calid')
        cs = CatSource.objects.filter(id__in=[c.source.id for c in dc]).annotate(count=Count('datacollection__datapoint')).filter(count__gte=e.numobs).values_list('id',flat=True).distinct()
        dcall = DataCollection.objects.filter(planet=e,source__in=cs).values_list('id',flat=True)
        # print "** Collections %s" % dcall.count()
        if cs.count() > 0:
            # Only use ones where we have more than numobs
            for c in dc:
                # make sure these are in the CatSource list (can't use cs because the order isn't right)
                if c.source.id in cs:
                    v = Datapoint.objects.filter(coorder__source=c.source.id,pointtype='C').order_by('data__timestamp').values_list('data__id').annotate(Avg('value'))
                    # Double check we have same number of obs and cals
                    if v.count() == e.numobs:
                        ids,b = zip(*v)
                        cals.append(list(b))
                        try:
                            decvalue = Decision.objects.filter(source=c.source,person=person,planet__name=code,current=True)[0].value
                        except:
                            decvalue ='X'
                        cat_item = {'sourcename':c.source.name,'catalogue':c.source.catalogue}
                        cat_item['decsion'] = decvalue
                        cat_item['order'] = str(c.calid)
                        cats.append(cat_item)
                        callist.append(c.source.id)
    if callist:
        # Only proceed if we have calibrators in the list (i.e. arrays of numobs)
        ds = DataSource.objects.filter(event=e).order_by('timestamp')
        users = DataCollection.objects.filter(id__in=dcall).values_list('person',flat=True).distinct()
        maxnum = ds.count()
        dsmax1 = ds.aggregate(Max('id'))
        dsmax = dsmax1['id__max']
        dsmin = dsmax - maxnum
        ds = ds.values_list('id',flat=True)
        if person == 0:
            people = Decision.objects.filter(planet=e,value='D',current=True).values_list('person',flat=True).distinct()
            dp = Datapoint.objects.filter(data__event=e,user__id__in=people)
            sc = []
            bg = []
            for d in ds:
                sc_ave = dp.filter(pointtype='S',data__id=d).aggregate(val=Avg('value'))
                bg_ave = dp.filter(pointtype='B',data__id=d).aggregate(val=Avg('value'))
                sc.append(sc_ave['val'])
                bg.append(bg_ave['val'])
        else:
            sc_my = ds.filter(datapoint__pointtype='S',datapoint__user=person).annotate(value=Sum('datapoint__value')).values_list('id','value')
            bg_my = ds.filter(datapoint__pointtype='B',datapoint__user=person).annotate(value=Sum('datapoint__value')).values_list('id','value')
            if sc_my.count() < maxnum:
                return cals,normcals,[],[],dates,stamps,[],cats
            else:
                tmp,sc=zip(*sc_my)
                tmp,bg=zip(*bg_my)
        # Convert to numpy arrays to allow simple calibrations
        sc = array(sc)
        bg = array(bg)     
        for cal in cals:
            val = (sc - bg)/(array(cal)-bg)
            maxval = mean(r_[val[:3],val[-3:]])
            maxvals.append(maxval)
            norm = val/maxval
            normcals.append(list(norm))
        # Find my data and create unix timestamps
        unixt = lambda x: timegm(x.timetuple())+1e-6*x.microsecond
        iso = lambda x: x.isoformat(" ")
        times = ds.values_list('timestamp',flat=True)
        stamps = map(unixt,times)
        dates = map(iso,times)
        if person == 0:
            return normcals,stamps,[int(i) for i in ids],cats
        return cals,normcals,list(sc),list(bg),dates,stamps,[int(i) for i in ids],cats
    if person == 0:
        return normcals,stamps,[],[]
    return cals,normcals,[],[],dates,stamps,[],cats
    
def photometry(code,person,progress=False,admin=False):
    normcals = []
    maxvals = []
    cals,sc,bg,times,ids,cats = calibrator_averages(code,person,progress)
    indexes = [int(i) for i in ids]
    #sc = array(sc)
    #bg = array(bg)     
    for cal in cals:
	if len(cal) == progress['total']:
        #### Do not attempt to do the photmetry where the number of calibrators does not match the total        
            val = (sc - bg)/(cal-bg)
            maxval = mean(r_[val[:3],val[-3:]])
            maxvals.append(maxval)
            norm = val/maxval
            normcals.append(list(norm))
        # Find my data and create unix timestamps
    unixt = lambda x: timegm(x.timetuple())+1e-6*x.microsecond
    iso = lambda x: x.isoformat(" ")
    stamps = map(unixt,times)
    dates = map(iso,times)
    if admin:
        return normcals,stamps,indexes,cats
    return cals,normcals,list(sc),list(bg),dates,stamps,indexes,cats
        
def averagecals_async(e):
    #e = Event.objects.get(name=code)
    catsource = DataCollection.objects.values_list('source').filter(planet=e, display=True).annotate(Count('source'))
    for cat in catsource:
        if cat[0] != None:
            dps = Datapoint.objects.filter(data__event=e, coorder__source__id=cat[0], pointtype='C').order_by('data__timestamp').values_list('data').annotate(Avg('value'))
            # Double check we have same number of obs and cals
            if dps.count() == e.numobs:
                ids,values = zip(*dps)
                a = AverageSet.objects.get_or_create(star=CatSource.objects.get(id=cat[0]),planet=e,settype='C')
                a[0].values = ";".join([str(i) for i in values])
                a[0].save()
                print "Updated average sets on planet %s for %s" % (e.title,CatSource.objects.get(id=cat[0]))
    # Make averages for Source star and Background
    for category in ['S','B']:
        dps = Datapoint.objects.filter(data__event=e, pointtype=category).order_by('data__timestamp').values_list('data').annotate(Avg('value'))
        # Double check we have same number of obs and cals
        if dps.count() == e.numobs:
            ids,values = zip(*dps)
            a = AverageSet.objects.get_or_create(planet=e,settype=category)
            a[0].values = ";".join([str(i) for i in values])
            a[0].save()
            print "Updated average sets on planet %s for %s" % (e.title,category)
    return


def supercaldata(user,planet):
    calibs = []
    mypoints = []
    ti = 0.
    # assume data which has Decisions forms part of a complete set
    # People and their sources who have Dips in the select planet
    now = datetime.now()
    planet = Event.objects.get(name = planet)
    decs = Decision.objects.values_list('person','source').filter(value='D', current=True, planet=planet, source__datacollection__display=True).annotate(Count('source'))
    numsuper = decs.count()
    if settings.LOCAL_DEVELOPMENT: print "Number of supercals: %s" % numsuper
    # Create a lists of sources  and people
    if decs:
        peoplelst,sourcelst,tmp = zip(*decs)
        #print "%s - %s" % (ti, datetime.now()-now)
        ti += 1
        people = set(peoplelst)
        sources = set(sourcelst)
        for p in people:
            calslist = []
            vals = Datapoint.objects.filter(data__event=planet,user=p).order_by('data__timestamp')
            sourceave = vals.filter(pointtype='S').annotate(mean=Avg('value')).values_list('mean',flat=True)
            bgave = vals.filter(pointtype='B').annotate(mean=Avg('value')).values_list('mean',flat=True)
            # make into Numpy arrays for easier manipulation
            sc = array(sourceave)
            bg = array(bgave)
            calvals = Datapoint.objects.values('data','coorder__source').filter(user= p,coorder__source__in=sources,pointtype='C',coorder__source__final=True,coorder__complete=True,coorder__display=True)
            for c in sources:
                calaves = calvals.filter(coorder__source=c)
                calpoints = calaves.order_by('data__timestamp').annotate(mean=Avg('value')).values_list('mean',flat=True)
                if calpoints.count() == planet.numobs:
                    calslist.append(list(calpoints))
            if calslist:
                if settings.LOCAL_DEVELOPMENT: print "\033[94mWe have calibrators\033[1;m"
                calstack = vstack(calslist)
                # This throws a wobbly sometimes
                cc = (sc-bg)/(calstack-bg)
                calibs.append(cc.tolist())
            else:
                if settings.LOCAL_DEVELOPMENT: print "\033[1;35mThere are no calibrators in the list!!\033[1;m"
            #print "%s %s - %s" % (ti, p, datetime.now()-now)
            ti += 1
        # Create normalisation function
        norm_a = lambda a: mean(r_[a[:3],a[-3:]])
        mycals = []
        try:
            cala = vstack(calibs)
            norms = apply_along_axis(norm_a, 1, cala)
            dim = len(cala)
            norm1 = cala/norms.reshape(dim,1)
            mynorm1=[]
            if mypoints != []:
                #mynorms = apply_along_axis(norm_a, 1, mypoints)
                myaves = average(mypoints,0)
                mynorm_val = norm_a(myaves)
                mycals = list(myaves/mynorm_val)
        except Exception, e:
            print e
            print "\033[1;35mHave you started again but not removed all the data?\033[1;m"
            return None,[],[],[],None
        #if dim != len(mycals):
        # check if I have a full set of data, if not we need to do all the calibrator averages manually
        norm_alt = mean(norm1,axis=0)
        variance = var(norm1,axis=0)
        std = sqrt(variance)
        fz = list(norm_alt)
        nodata = False
        if mycals == []:
            mycals = myaverages(planet,user)
            nodata = True
        return numsuper,fz,mycals,list(std),nodata
    else:
        return None,[],[],[],None

def leastmeasured(code):
    coords = []
    e = Event.objects.filter(name=code)[:1]
    dc = DataCollection.objects.values('source').filter(~Q(source=None),planet__name=code).annotate(count = Count('source')).order_by('count')[:4]
        # e = Event.objects.filter(name=code)
        # finderdp = Datapoint.objects.values_list('xpos','ypos').filter(user=person,data__id=e[0].finder,pointtype='C',coorder__calid__lt=3).order_by('coorder__calid')
        # finder = basiccoord - array(finderdp)
        # t = transpose(finder)
        # xmean = mean(t[0])
        # ymean = mean(t[1])
    for coll in dc:
        s = CatSource.objects.get(id=coll['source'])
        coords.append({'x':int(s.xpos),'y':int(s.ypos),'r':int(e[0].radius)})
    return coords   
        

def update_web_pref(request,setting):
    #################
    # AJAX update user preference for web or  manual input of data
    if (request.user.is_authenticated()):
        person = request.user
    else:
        person = guestuser
    o = Observer.objects.filter(user=person)
    if setting == 'yes':
        o.update(dataexplorview=True)
        return HttpResponse("Setting changed to use web view")
    elif setting == 'no':
        o.update(dataexploreview = False)
        return HttpResponse("Setting changed to use manual view")
    else:
        return HttpResponse("Setting unchanged")
            
def tester(request):
    return render_to_response('agentex/test.html')
    
def average_sources(code):
    typep = ('S','C','B')
    ds = DataSource.objects.filter(name=code)
    for s in ds:
        points = Datapoint.objects.filter(data=s)
        dates = points.values_list('taken',flat=True)
        for date in dates:
            entry = points.objects.filter(taken=date)
            

def calibrate_update(code):
    dates = Datapoint.objects.values_list('taken',flat=True).filter(data__event__name=code).annotate(Count('taken'))
    for date in dates:
        measurement = Datapoint.objects.filter(taken=date,data__event__name=code)
        source = measurement.filter(pointtype='S')
        calib = measurement.filter(pointtype='C')
        backg = measurement.filter(pointtype='B')
        value = (source[0].value - backg[0].value)/(calib[0].value - backg[0].value)
        reduced = measurement.filter(pointtype='R')[0]
        reduced.value = value
        reduced.save()
        print "Reduced %s" % date
        
def calibrate(measurement):
    source = measurement.filter(pointtype='S')
    calib = measurement.filter(pointtype='C')
    backg = measurement.filter(pointtype='B')
    value = (source[0].value - backg[0].value)/(calib[0].value - backg[0].value)
    return value
    
def img_coord_conv(x,size):
    newx = []
    entries = x.split(",")
    for entry in entries:
        newx.append(floor(float(entry)*size))
    return newx
        
def ismypoint(person,datauser):
    if person.user == datauser:
        return True
    else:
        return False
def personcheck(request):
    if (request.user.is_authenticated()):
        o = Observer.objects.filter(user=request.user)
    else:
        o = Observer.objects.filter(user__id=guestuser)
    return o[0]
    
def classified(o,code):
    dcs = Decision.objects.values('source').filter(person=o.user,planet__name=code).annotate(last = Max('taken'))
    dips = Decision.objects.filter(taken__in=[d['last'] for d in dcs],person=o.user,planet__name=code,value='D').count()
    classifications = Decision.objects.values('source').filter(person=o.user,planet__name=code).annotate(Count('value')).count()
    totalcalibs = DataCollection.objects.values('source').filter(person=o.user,planet__name=code).annotate(Count('display')).count()
    return {'total' : totalcalibs, 'done':classifications,'dip':dips}
    
def checkprogress(person,code):
    n_analysed = Datapoint.objects.filter(user=person, data__event__name=code,pointtype='S').count()
    n_sources = DataSource.objects.filter(event__name=code).count()
    if (n_sources == 0):
	    progress = {'percent'   : "0.0",
                'done'      : n_analysed,
                'total'     : n_sources,}
    else:
	    progress = {'percent'   : "%.0f" % (float(n_analysed)*100/float(n_sources)),
                'done'      : n_analysed,
                'total'     : n_sources,}
    return progress    

def fetch_averages_sql(dsmin,dsmax,pointtype,users):
    cursor = connection.cursor()
    users_str = [int(i) for i in users]
    params = [pointtype,dsmin,dsmax,users_str]
    cursor.execute('SELECT dp.data_id, avg(dp.value) FROM dataexplorer_datapoint as dp RIGHT JOIN dataexplorer_datasource AS ds on dp.data_id = ds.id WHERE dp.pointtype = %s AND (dp.data_id BETWEEN %s AND %s) AND dp.user_id IN %s GROUP BY dp.data_id order by ds.timestamp', params)
    result = list(cursor.fetchall())
    #ave_values = dict(result)
    return result
    
def dictconv(data,ref):
    tmp = []
    for i in ref:
        try:
            tmp.append(data[i])
        except:
            tmp.append(0.)
    return tmp
  
def addcomment(request):
# Log user comments in the Django log
    if request.POST:
        message = request.POST.get('comment','')
        if message:
            if request.user.is_authenticated():
              userid = request.user.pk
              email = request.user.email
            else:
              userid = 1
              email = request.POST.get('emailaddress','')
              message = "%s : %s" % (message,email)
        
            # Attach the comment to User content type pk = 3
            contentpk = 3
            LogEntry.objects.log_action(
                user_id         = userid, 
                content_type_id = contentpk,
                object_id       = userid,
                object_repr     = smart_unicode(User.objects.get(id=userid)), 
                action_flag     = ADDITION,
                change_message  = message,
            )
            messages.success(request,'Thank you for your comments!')
            data = {'emailaddress' : email,'comment':' '}
            form = CommentForm()
        else:
            form = CommentForm(request.POST)
    else:
        if request.user.is_authenticated():
          data = {'emailaddress' : request.user.email,'comment':' '}
          form = CommentForm(data)
        else:
            form = CommentForm()
    return render_to_response('agentex/comments_box.html', {'form':form}, context_instance=RequestContext(request))

def update_final_display():
    c = CatSource.objects.all()
    c.update(final=True)
    decs = Decision.objects.filter(value='D',current=True)
    for d in decs:
        dc = DataCollection.objects.filter(person=d.person,source=d.source)
        dc.update(display=True)
        print d.planet, d.person
        
def update_cat_sources(username,planetcode):
    event = Event.objects.get(name=planetcode)
    points = Datapoint.objects.filter(user__username=username,data__id=event.finder,pointtype='C')
    for p in points:
        cats = CatSource.objects.filter(xpos__lt=p.xpos+5,ypos__lt=p.ypos+5,xpos__gt=p.xpos-5,ypos__gt=p.ypos-5,data__event=event)
        dc = p.coorder
        if cats:
            dc.source=cats[0]
            print dc.id,dc.source.data.event
        else:
            dc.source=None
            print dc.id, 'No catsource found'
        dc.save()
        
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
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model
from django.conf import settings
from django.contrib.auth.models import User, check_password
from django.contrib.auth.backends import ModelBackend
import MySQLdb
import hashlib
from settings import DATABASES as dbc
from agentex.models import Observer

        
def matchRTIPass(username,password):
    # Retreive the database user information from the settings
    db = MySQLdb.connect(user=dbc['wis']['USER'], passwd=dbc['wis']['PASSWORD'], db=dbc['wis']['NAME'], host=dbc['wis']['HOST'])

    # Match supplied user name to one in Drupal database
    sql_users = "SELECT schoolloginname, password, contactemailaddress,tag,schoolname FROM registrations WHERE schoolloginname='%s' AND (accountstatus = 'active' OR accountstatus = 'suspended')" % username
    rti = db.cursor()
    rti.execute(sql_users)
    user = rti.fetchone()
    rti.close()
    db.close()
    if user:
        if (password == user[1]):
            ###### If the user does not have an email address return false
            if user[2]:
                return user[2], user[3], user[4]
            else:
                return False
    else:
        return False
        
def checkUserObject(params,username,password):
    email = params[0]
    tag = params[1]
    org = params[2]
    try:
        user = User.objects.get(username=username)
        hashpass = hashlib.md5(password).hexdigest()
        if (user.password != hashpass):
            user.password = hashpass
            user.save()
    except User.DoesNotExist:
        name_count = User.objects.filter(username__startswith = username).count()
        if name_count:
            username = '%s%s' % (username, name_count + 1)
            user = User.objects.create_user(username,password=password,email=email)
        else:
            user = User.objects.create_user(username,password=password,email=email)
#### Check there is an observer for this user
    try:
        o = Observer.objects.get(user=user)
    except:
        if tag and org:
            o = Observer(user=user,tag=tag,organization=org)
        elif tag:
            o = Observer(user=user,tag=tag)
        else:
            o = Observer(user=user)
        o.save()
    return user   
         
class LCOAuthBackend(ModelBackend):         
    def authenticate(self, username=None, password=None):
        fns =  matchRTIPass(username, password)
        for response in fns:
            if (response):
                return checkUserObject(response,username,password)
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None  

            
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
DATA_LOCATION ='/Volumes/Tardis-type40/AgentExoplanetData/agentexdata'
DATA_URL = 'http://127.0.0.1/agentexdata'

PREFIX = ''
DEBUG = True
PRODUCTION = False
STATIC_ROOT =  '/Users/egomez/Sites/static'
STATIC_URL = '/static/'

LOGIN_URL = 'http://localhost:8000/account/login/'
LOGIN_REDIRECT_URL = '/''''
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
# Django settings for observing project.

import os
import platform
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
from django.utils.crypto import get_random_string


CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
LOCAL_DEVELOPMENT = False if CURRENT_PATH.startswith('/var/www') else True
PRODUCTION = True

DEBUG = False

PREFIX ="/agentexoplanet"
BASE_DIR = os.path.dirname(CURRENT_PATH)

ADMINS = (
     ('Edward Gomez', 'egomez@lcogt.net'),
)

MANAGERS = ADMINS

DATABASES = {
 'default' : {
    'NAME'      : 'citsciportal',
    "USER": os.environ.get('CITSCI_DB_USER',''),
    "PASSWORD": os.environ.get('CITSCI_DB_PASSWD',''),
    "HOST": os.environ.get('CITSCI_DB_HOST',''),
    "OPTIONS"   : {'init_command': 'SET storage_engine=INNODB'},
}
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


MEDIA_ROOT = '/var/www/html/media/'
MEDIA_URL = '/media/'

STATIC_ROOT = '/var/www/html/static/'
STATIC_URL = PREFIX + '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR,'agentex'),os.path.join(BASE_DIR,'showmestars')]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder"
 )

# Make this unique, and don't share it with anybody.
chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
SECRET_KEY = get_random_string(50, chars)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)  

CACHE_MIDDLEWARE_SECONDS = '1'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    )

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.messages',
    'agentex',
    'showmestars',
    'core'
)

LOGIN_REDIRECT_URL = 'http://lcogt.net/agentexoplanet/'
LOGIN_URL = 'http://lcogt.net/agentexoplanet/account/login/'

BASE_URL = "/agentexoplanet/"

DATA_LOCATION = CURRENT_PATH + '/media/data'
DATA_URL = '/agentexoplanet/media/data'

##################
# LOCAL SETTINGS #
##################

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
if LOCAL_DEVELOPMENT:
    try:
        from local_settings import *
    except ImportError as e:
        if "local_settings" not in str(e):
            raise e
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
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles import views
from django.views.generic import RedirectView

admin.autodiscover()

urlpatterns = [
#    (r'^api/', include('odin.api.urls')),
    url(r'^$','agentex.views.home',name='portal'),
    url(r'^agentexoplanet/agentex/', RedirectView.as_view(url='/agentexoplanet/', name=''),
    url(r'^agentexoplanet/admin/agentex/event/(?P<planetid>\d+)/calibrators/(?P<calid>\d+)/$','agentex.admin.calibrator_check', name=''),
    url(r'^agentexoplanet/admin/agentex/event/(?P<planetid>\d+)/calibrators/$','agentex.admin.allcalibrators_check', name=''),
    url(r'^agentexoplanet/admin/', include(admin.site.urls), name=''),
    url(r'^agentexoplanet/',include('agentex.urls'), name=''),
    url(r'^showmestars/newimage/$','showmestars.views.newimage',{'eventid':0}, name=''),
    url(r'^showmestars/(?P<eventid>\w+)/$','showmestars.views.latestimages', name=''),
    url(r'^showmestars/$','showmestars.views.latestimages',{'eventid':0}, name='')
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', views.serve),
    ]
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
from django.db import models

class Event(models.Model):
    hostid = models.CharField(max_length=75)
    name = models.CharField(max_length=75)
    current = models.BooleanField(default=False)
    slotlist = models.CharField(max_length=75)
    start = models.DateTimeField()
    end = models.DateTimeField()
    site = models.CharField(max_length=75,blank=True,null=True)
    class Meta:
        verbose_name = u'show me stars event'
    def __unicode__(self):
        return "%s %s %s" % (self.name,self.start.isoformat(),self.site)
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
from django.template import RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, Http404
import MySQLdb
from django.conf import settings
from datetime import datetime

import time

from showmestars.models import Event
    
def latestimages(request,eventid):
    try:
        eid = int(eventid)
    except ValueError:
        raise Http404
    if eid == 0:
        event = Event.objects.all().order_by('-start')
    else:
        event = Event.objects.filter(id=eid).order_by('-start')
          
    newevents = []
# Start connection
    db = MySQLdb.connect(user=DATABASES['faulkes']['USER'], passwd=DATABASES['faulkes']['PASSWORD'], db=DATABASES['faulkes']['NAME'], host=DATABASES['faulkes']['HOST'])
    for e in event:
        # Find new observations
        sql_images = "SELECT ImageID, WhenTaken,Filename,TelescopeId,SkyObjectName,filter FROM imagearchive WHERE  SchoolID ='%s' AND WhenTaken > '%s' AND WhenTaken < '%s' order by WhenTaken desc;" % (e.hostid, e.start.strftime("%Y%m%d%H%M%S"), e.end.strftime("%Y%m%d%H%M%S"))
        images = db.cursor()
        images.execute(sql_images)
        obs = []
        for i in images:
            obs.append(makeimagebox(i))
        newevents.append({'details':e,'obs':obs})
    stamp = datetime.utcnow()
    db.close()
    return render_to_response('showmestars/imageportal.html',{'stamp':stamp,'event':newevents}, context_instance=RequestContext(request))
    
def newimage(request,eventid):
    try:
        eid = int(eventid)
        if eventid ==0:
            event = Event.objects.filter(current=True)[0]
        else:
            event = Event.objects.get(id=eid)
    except ValueError:
        raise Http404
    obs = []
    stamp = request.GET.get('stamp','0')
    db = MySQLdb.connect(user=DATABASES['faulkes']['USER'], passwd=DATABASES['faulkes']['PASSWORD'], db=DATABASES['faulkes']['NAME'], host=DATABASES['faulkes']['HOST'])
    sql_images = "SELECT ImageID, WhenTaken,Filename,TelescopeId,SkyObjectName,filter FROM imagearchive  WHERE  SchoolID ='%s' AND WhenTaken > '%s' order by WhenTaken desc limit 20" % (event.hostid,stamp)
    images = db.cursor()
    images.execute(sql_images)
    stamp = datetime.utcnow()
    for i in images:
        obs.append(makeimagebox(i))
    return render_to_response('showmestars/imagebox.html',{'obs':obs,'stamp':stamp}, context_instance=RequestContext(request))


def makeimagebox(image):
    telescopeont = ('ogg/2m0a','coj/2m0a')
    telescope = ('Faulkes Telescope North','Faulkes Telescope South')
    WhenTaken = image[1]
    taken = datetime(*time.strptime(WhenTaken , "%Y%m%d%H%M%S")[0:5])
    #d = "%s" % s.strftime("%a, %d %b %Y")
    filename = image[2]
    try:
        filter = ""
    except:
        filter = "Unknown"
    faulkes_url = "http://rti.faulkes-telescope.com/"
    image_url = "observations/%s/%s/%s/%s" % (WhenTaken[:4],WhenTaken[4:6],WhenTaken[6:8],filename[:-4])
    fullimage_url = "%s%s-%s_150.jpg" % (faulkes_url,image_url,image[3])
    smallimage_url = "%s%s-%s_120.jpg" % (faulkes_url,image_url,image[3])
    urlobs = "http://lcogt.net/observations/%s/%s" % (telescopeont[image[3]-1],image[0])
    obs = {'id'         : image[0],
            'telescope' : telescope[image[3]-1],
            'filter'    : filter,
            'date'      : taken.strftime("%a, %d %b %Y"),
            'imageurl'  : fullimage_url,
            'obsurl'    : urlobs,
            'name'      : image[4],
            'stamp'     : WhenTaken,
    }
    return obs