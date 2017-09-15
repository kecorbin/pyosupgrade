# pyosupgrade

Python based utility for automating the upgrade of IOS based switches.

#### features
* workflows/tasks are pretty much anything that can be scripted in python using the [Netmiko](https://github.com/ktbyers/netmiko) SSH library
* Ability to specify custom workflow for upgrade procedure including pre and post verification
* Support sourcing IOS images from geographically desirable sources (infoblox, s3, etc)
* Workflow monitoring with session log output available in near real time accessible via web interface
* Ability to pause for additional user verification before proceeding.


Oh yeah,most importantly it has a RESTful API for integrating with other tools..spark, etc.

#### Verified on the following platforms

* Catalyst 4500
* ASR 1000
* CSR 1000v
* NX-OS (non-upgrade use case)

This project may require some minor changes to work with other platforms.

### Sample Procedures included
* Catalyst 4500 w/ advanced FPGA + QoS queue verification
* CSR1000v upgrade
* ASR1000 w/ ROMMON upgrade
* Verification that all operational ports have description
* NX-OS 'basic show command'

# Architecture

This project follows a microservices architecture and uses the following components/technologies.

### [Netmiko](https://github.com/ktbyers/netmiko)

Multi-vendor library to simplify Paramiko SSH connections to network devices.
We use this to actually perform IOS acrobatics. The basic usage of this library is
easy to learn, and maps really well to CLI based workflows.


### [Flask](http://flask.pocoo.org/)

Flask is a microframework written in python.  We leverage flask from the RESTFul API and rendering the web
based user interface

### [Celery](http://www.celeryproject.org/)

* Celery is an asynchronous task queue/job queue based on distributed message passing.
* It is focused on real-time operation, but supports scheduling as well.
* The execution units, called tasks, are executed concurrently on a single or more or all worker servers
* Tasks can execute asynchronously (in the background) or synchronously (wait until ready).

In our first use case an upgrade is a task, but others could be used. [see here](https://github.com/kecorbin/pyosupgrade/commit/4c3c9a077b5bd7c01f26f8a53a523c262891142a)

### [Flower - Celery monitoring tool](http://flower.readthedocs.io/en/latest/)

Flower is a web based tool for monitoring and administrating Celery clusters

##### Features
* Real-time monitoring using Celery Events
* Task progress and history
* Ability to show task details (arguments, start time, runtime, and more)
* Graphs and statistics
* Remote Control of worker nodes


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


# Running

Okay, so if you've gotten this far, you must be willing to give it a spin!

The easiest way to use this project is with docker-compose
```
docker-compose build
docker-compose up
```

you should be able to browse to [https://localhost](https://localhost) to get started!


# Certificates

Self-signed certificates are provided for convienence and to provide a base level of encryption, however,
for anything beyond kicking the tires it would probably be a good idea to generate your own, and replace
the default ones in [./nginx/ssl](./nginx/ssl)

# Feedback/Suggestions/PR's

Whatcha thinkin?
