from django.conf.urls.defaults import *


urlpatterns = patterns('citsciportal.agentex.views',
    (r'^$','index'),
    (r'^planets/$','target'),
    (r'^fitsanalyse','fitsanalyse'),
    (r'^test','tester'),
    (r'^briefing/read/$','read_manual_check'),
    (r'^briefing/$','briefing'),
    (r'^profile/$','profile'),
    (r'^comment/$','addcomment'),
    (r'^(?P<code>\w+)/view/$','addvalue'),
    (r'^(?P<code>\w+)/graph/update/$','updatedataset'),
    (r'^(?P<code>\w+)/lightcurve/advanced/$','graphview', {'mode' : 'advanced','calid':None}, 'advanced-graph'),
    (r'^(?P<code>\w+)/lightcurve/me/$','graphview', {'mode' : 'simple','calid':None}, 'my-graph'),
    (r'^(?P<code>\w+)/lightcurve/calibrator/update/$','classifyupdate'),
    url(r'^(?P<code>\w+)/lightcurve/calibrator/$','graphview', {'mode' : 'ave','calid':None}, name='average-graph'),
    (r'^(?P<code>\w+)/lightcurve/calibrator/(?P<calid>\w+)/$','graphview', {'mode' : 'ave'}),
    url(r'^(?P<code>\w+)/lightcurve/$','graphsuper',name='super-graph'),
    (r'^(?P<code>\w+)/$','infoview'),
    (r'^(?P<code>\w+)/data.(?P<format>\w+)','measurementsummary'),
)