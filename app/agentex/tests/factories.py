import factory
import factory.django

import agentex.models as models

import datetime
import random


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Event

    name = 'trenzalore'
    finder = long(random.randint(0,500))

class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataSource

    id = long(random.randint(0,50))
    timestamp = datetime.datetime.now
    event = factory.RelatedFactory(EventFactory)

class CatSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatSource

    id = random.randint(0,50)
    name = u'Raxacoricofallapatorius'
    data = factory.RelatedFactory(DataSourceFactory)

class DatapointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Datapoint

    data = factory.RelatedFactory(DataSourceFactory)
    source = factory.RelatedFactory(CatSourceFactory)

class DecisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Decision

    source = factory.RelatedFactory(CatSourceFactory)
    planet = factory.RelatedFactory(EventFactory)
    value = float(random.randint(0,500))
