from django.core.management.base import BaseCommand, CommandError
from agentex.models import DataSource, Event, Target, CatSource
import os #, pyfits
from astropy.io import fits
from datetime import datetime
from settings import DATA_LOCATION

#path = '/Users/eg/Sites/data/'

#url1 = "complete/extra/GJ1214/"
#urlj =  "http://localhost/data/M51-R/"

class Command(BaseCommand):
    args = '<event_id> <target_id>'
    help = 'Create DataSource objects for FITS files'

    def handle(self, *args, **options):
        e = Event.objects.get(id=int(args[0]))
        target = Target.objects.get(id=int(args[1]))
        urlj = 'jpgs'
        urlf = 'fits'
        fitsdir = "%s/%s/%s/" % (DATA_LOCATION,e.name,urlf)
        ls = os.listdir(fitsdir)
        listf = []
        listj = []
        i = 0
        for l in ls:
            if l.endswith('.fits'):
                listf.append(l)

        self.stdout.write('%s : %s\n' % (target.name,e.title))
        for lf in listf:
            datapath = "%s/%s/%s/%s" % (DATA_LOCATION,e.name,urlf,lf)
            self.stdout.write('reading from %s' % datapath)
            #head = pyfits.getheader(datapath)
            head = fits.open(datapath)
            imagej = lf.replace('.fits','.jpg')
            fitsurl = "/%s/%s/%s" % (e.name,urlf,lf)
            try:
                self.stdout.write('Telescope %s\n' % head['TELESCOP'])
            except:
                self.stdout.write('Not FTN or FTS\n')
            if head['TELESCOP'] == 'Faulkes Telescope North' or head['TELESCOP'] == 'Faulkes Telescope South':
                # FTN/S data
                timestamp = datetime.strptime(head['DATE-OBS'], "%Y-%m-%dT%H:%M:%S.%f")
                maxx = int(head['CCDXIMSI'])
                maxy = int(head['CCDYIMSI'])
            else:
                # Sedgwick data
                timestamp = datetime.strptime(head['DATE-OBS'], "%Y-%m-%dT%H:%M:%S")
                maxx= int(head['NAXIS1'])
                maxy = int(head['NAXIS2'])
            ds = DataSource(fits = fitsurl,
                        event=e,
                        target=target,
                        timestamp=timestamp,
                        telescopeid=head['TELESCOP'],
                        max_x=maxx,
                        max_y=maxy,
                        )
            try:
                imageurl = "/%s/%s/%s" % (e.name,urlj,imagej)
                ds.image = imageurl
            except:
                raise CommandError('failed to find JPG for lf')
            ds.save()
            i += 1
            self.stdout.write('Saved %s at %s\n' % (ds.id,datapath))
        ds = DataSource.objects.filter(event=e).order_by('timestamp')
        e.numobs = ds.count()
        e.start = ds[0].timestamp
        e.end = ds[ds.count()-1].timestamp
        e.midpoint = ds[ds.count()/2].timestamp
        e.save()

        self.stdout.write('Successfully imported all data for "%s"\n' % e.title)

def f(x,y,z):
     if x.endswith('.fits'):
         return y.append(x)
     elif x.endswith('jpg'):
         return z.append(x)
