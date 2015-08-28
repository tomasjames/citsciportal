Citizen Science Portal
======================

This project contains Agent Exoplanet.

Changes
-------

1. Agent Exoplanet now uses the latest version of Django (Django 1.8).
2. The combined lightcurve (the lightcurve that combines everybody's data) now plots live, rather than the cron-job based system previous builds used.
3. The majority of the computation for the combined lightcurve is now done using numpy arrays for speed.
4. Other miscellaneous optimisations to the code have been made.

Agent Exoplanet
---------------

First citizen science project for LCOGT. It involves the analysis of exoplanet transit data.

Docker
======

This project has been converted to use Docker as the deployment method.

Instructions
------------

    $ docker build -t docker.lcogt.net/agentex:latest .
    $ docker push docker.lcogt.net/agentex:latest
