# pyosupgrade

Python based utility for automating the upgrade of IOS based switches

Validated on the Catalyst 4500 series switches.  May require minor changes to work
with other platforms

### Sample Procedures included
* Catalyst 4500 w/ advanced FPGA + QoS queue verification
* CSR1000v
* ASR1000 w/ ROMMON upgrade

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


### [MongoDB](https://www.mongodb.com)

MongoDB is an open source database that uses a document-oriented data model. This is where we persist information
about upgrade jobs


# Getting started

Getting started is super easy, just modify the [images.yaml](./images.yaml) to suit your needs

```
WS-X45-SUP7-E:
  filename: cat4500e-universalk9.SPA.03.08.04.E.152-4.E4.bin
```

In this example a platform matching WS-X45-SUP7-E will use `cat4500e-universalk9.SPA.03.08.04.E.152-4.E4.bin`
from the regional TFTP server.

Regions are how we identify which TFTP server to use for the file transfer for a given switch.  Usually
devices contain some geographical region information in their hostname.

Modify [regions.yaml](./regions.yaml) to suit your situation.

 ```
FR:
  regional_fs: 10.250.6.20
BF:
  regional_fs: 10.122.1.10
AS:
  regional_fs: 10.122.1.10
KC:
  regional_fs: 192.168.51.1
 ```

 In this example any switch starting with `AS` will use `10.122.1.10` as the tftp server, likewise, switches
 with starting with `kc` will use `192.168.51.1`

# Certificates

Self-signed certificates are provided for convienence and to provide a base level of encryption, however,
for anything beyond kicking the tires it would probably be a good idea to generate your own, and replace
the default ones in [./nginx/ssl](./nginx/ssl)


# Running

The easiest way to use this project is with docker-compose
```
docker-compose build && docker-compose up
```

you should be able to browse to [https://localhost](https://localhost) to get started!

