from django.core.management.base import BaseCommand, CommandError
from agentex.models import AverageSet, Datapoint, Event
from datetime import datetime, timedelta
from agentex.views import photometry, calibrator_averages

class Command(BaseCommand):
    args = '<event_name> <force>'
    help = 'Update the AverageSets but only if that planet has had new measurements recently'

    def handle(self, *args, **options):
         cals,sc,bg,times,ids,cats = calibrator_averages(code,person,progress)
         indexes = [int(i) for i in ids]
         #sc = array(sc)
         #bg = array(bg)   
         print code  
         for cal in cals:
             print "sc %s bg %s cals %s" %(len(sc),len(bg),len(cal))
            