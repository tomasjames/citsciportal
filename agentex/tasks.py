from agentex.models import AverageSet, Datapoint, Event
from datetime import datetime, timedelta
from agentex.views import averagecals_async, supercaldata
from celery import task

@task()
def update_average_sets(planetcode=None,force=False):
    planet_updates = []
    if planetcode:
        planets = Event.objects.filter(name=planetcode)
    else:
        planets = Event.objects.filter(enabled=True)
    for planet in planets:
        latest = Datapoint.objects.filter(data__event=planet).latest('taken')
        if (datetime.now() - latest.taken < timedelta(minutes=10)) or force:
            averagecals_async(planet)
            ### Create final dataset and store as an average set
            result = supercaldata(None,planet)
            final = [{'type' : 'F', 'data':result[1]},{'type' : 'E', 'data':result[3]}]
            for s in final:
                a = AverageSet.objects.get_or_create(star=None,planet=planet,settype=s['type'])
                a[0].values = ";".join([str(i) for i in s['data']])
                a[0].save()
            planet_updates.append(planet.title)
    if planet_updates:
        msg = "Updated %s" % (", ".join(planet_updates))
    else:
        msg = "No planets needed updates"
    return msg