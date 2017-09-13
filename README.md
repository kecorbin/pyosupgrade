# pyosupgrade

Python based utility for automating the upgrade of IOS based switches

Validated on the Catalyst 4500 series switches.  May require minor changes to work
with other platforms


# Architecture

This project follows a microservices architecture and uses the following components/technologies.

### [Flask](http://flask.pocoo.org/)

Flask is a microframework written in python.  We leverage flask from the RESTFul API and rendering the web
based user interface

### [Celery](http://www.celeryproject.org/)

Celery is an asynchronous task queue/job queue based on distributed message passing. Celery is compWe use celery workers
to perform upgrades which gives us the ability to perform many upgrades in parallel

### [Redis](https://redis.io/)

Redis is an open source (BSD licensed), in-memory data structure store, used as a database, cache and message broker
Redis is the broker used by celery to distribute celery tasks.


### [PostgreSQL](https://www.postgresql.org)

Traditional RDMS used for persisting information about our upgrades.  This is really unnecessary at this point
as we don't have a lot of(any) relationships in the object model, but that's what we used initially. Will likely
be replaced with something like Mongo in the future.


# running

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
./start.sh

```
