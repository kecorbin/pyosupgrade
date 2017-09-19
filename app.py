import yaml
import os
import tasks
import sys
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_restful import Resource, Api
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from bson.json_util import dumps
from pyosupgrade.procedures.cat4500 import Catalyst4500Upgrade
from pyosupgrade.procedures.asr1000 import ASR1000Upgrade
from pyosupgrade.procedures.csr1000 import CSR1000Upgrade
from pyosupgrade.procedures.healthchecks import IntDescrChecker
from pyosupgrade.views.logbin import Log, viewer
from pyosupgrade.views.diffview import diff
# Since this is not a python package we need to do some work to treat it like
# such.
if __name__ == '__main__':
    if __package__ is None:
        sys.path.append(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
api = Api(app)


app.secret_key = 'CHANGEME'
# https://stackoverflow.com/questions/33738467/how-do-i-know-if-i-can-disable-sqlalchemy-track-modifications
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config.update(
    CELERY_BROKER_URL='redis://redis:6379',
    CELERY_RESULT_BACKEND='redis://redis:6379',
    REDIS_HOST='localhost',
    REDIS_PORT=6379,
    REDIS_DB='upgrades'

)


app.config["MONGO_DBNAME"] = "upgrades"
app.config["MONGO_HOST"] = "mongo"
mongo = PyMongo(app, config_prefix='MONGO')

LOGBIN_URL = os.getenv('LOGBIN_API')
CALLBACK_API = os.getenv('CALLBACK_API')
REGIONS_API = os.getenv('REGIONS_API')
IMAGES_API = os.getenv('IMAGES_API')


METHOD_OF_PROCEDURES = {
    "asr1000": {"description": "a fake mop",
                 "procedure": ASR1000Upgrade},
    "csr1000v": {"description": "a fake mop",
                 "procedure": CSR1000Upgrade},
    "cat4500-3.8.4-w-fpga": {"description": "Upgrade Catalyst 4500 with FPGA upgrade validation",
                             "procedure": Catalyst4500Upgrade},
    "verify-int-desc": {"description": "Checks that all enabled interfaces have descriptions",
                        "procedure": IntDescrChecker}
}


@app.errorhandler(404)
def page_not_found(e):
    return render_template('notfound.html'), 404


def home():
    return redirect(url_for('jobview', _external=True))


def jobview(id=None):

    if request.method == 'GET':
        # job detail view
        if id:
            # retrieve mongo document by id
            doc = mongo.db.upgrades.find_one({"id": id})
            # deserialize the job from mongo
            job = METHOD_OF_PROCEDURES[doc['mop']]['procedure'].from_dict(doc)
            before = getattr(job, 'pre_verification_commands_url', None)
            after = getattr(job, 'post_verification_commands_url', None)
            if before and after:
                before = before.split('/')[-1]
                after = after.split('/')[-1]

            return render_template('upgrade-detail.html',
                                   title="Job Detail",
                                   job=job,
                                   before=before,
                                   after=after,
                                   procedures=METHOD_OF_PROCEDURES)
        # job list view
        else:
            cursor = mongo.db.upgrades.find()
            jobs = [j for j in cursor]
            return render_template('upgrade.html',
                                   title='Code Staging',
                                   logo='/static/img/4500.jpg',
                                   jobs=jobs,
                                   procedures=METHOD_OF_PROCEDURES)

    elif request.method == 'POST':
        # gather form data
        username, password = request.form['username'], request.form['password']
        mop = request.form['mop']

        # handle the case where this is an existing job
        # this most likely means the device is ready to be upgraded)

        if id:
            print ("starting upgrade")
            # retrieve mongo document by id
            doc = mongo.db.upgrades.find_one({"id": id})
            # deserialize the job from mongo
            print "RESPONSE FROM MONGO: {}".format(doc)
            job = METHOD_OF_PROCEDURES[doc['mop']]['procedure'].from_dict(doc)
            url = CALLBACK_API + '/{}'.format(id)
            tasks.upgrade_launcher.delay(url, mop, 'start_upgrade', username, password)

            # Notify the user
            flash("Upgrade Started", "alert-success")
            return redirect(url_for('jobview', id=id, _external=True))

        # handle the case where a new job is created
        else:
            # glean info from the form
            payload = request.form

            # this makes sure the final line has a CR
            devices = payload['hostnames'] + "\r\n"
            devices = devices.split('\r\n')
            print devices
            for d in devices:

                # make sure the device name/ip is valid,
                # this could use better verification e.g ping/etc
                if len(d) > 5:
                    print "Creating code upload job for {}".format(d)
                    object_id = ObjectId()
                    url = CALLBACK_API + "/{}".format(object_id)
                    data = {"_id": object_id,
                            "job_url": url,
                            "id": str(object_id),
                            "status": "SUBMITTED",
                            "username": payload['username'],
                            "device": d,
                            "mop": payload['mop'],
                            "regions_url": REGIONS_API,
                            "images_url": IMAGES_API,
                            "logbin_url": LOGBIN_URL}

                    # insert
                    mongo.db.upgrades.insert(data)
                    # start staging
                    tasks.upgrade_launcher.delay(url, mop, 'start_staging', username, password)

            flash("Submitted Job", "alert-success")
            return redirect(url_for('jobview', _external=True))


class CodeUpgradeJobView(Resource):

    def get(self, id=None):
        if id:
            print "getting job with id {} ".format(id)

            job = mongo.db.upgrades.find_one({"_id": ObjectId(id)}, {"_id": 0})
            print "got job {}".format(job)
            print job
            return job
        else:

            cursor = mongo.db.upgrades.find({}, {"_id": 0})
            staging_jobs = [j for j in cursor]
            print "staging jobs {}".format(staging_jobs)
            return staging_jobs

    def post(self, id=None, operation=None):
        # endpoint to start job
        if operation == "start" and id:
            job = mongo.db.upgrades.find_one({"id": id}, {"_id": 0, "update_time": 0})
            url = CALLBACK_API + "/{}".format(job['id'])
            tasks.upgrade_launcher.delay(url, job['mop'], 'start_upgrade', request.json['username'], request.json['password'])
            return job

        # endpoint to update and existing job
        if id:
            job = mongo.db.upgrades.find_one({"id": id}, {"_id": 0, "update_time": 0})
            for k, v in request.json.items():
                job[k] = v
            mongo.db.upgrades.update({"_id": ObjectId(id)}, job)
            return job

        # new job received via api
        else:
            if request.json:

                object_id = ObjectId()
                data = {"id": str(object_id),
                        "status": "SUBMITTED",
                        "username": request.json['username'],
                        "device": request.json['device'],
                        "mop": request.json['mop']}

                mongo.db.upgrades.insert(data)
                job = mongo.db.upgrades.find_one({"id": object_id})
                url = CALLBACK_API + "/{}".format(str(object_id))
                tasks.upgrade_launcher.delay(url, request.json['mop'],
                                             'start_staging',
                                             request.json['username'],
                                             request.json['password'])
                return dumps(job)

    def delete(self, id=None):
        try:
            job = mongo.db.upgrades.find_one({"id": id})
            print "deleting job {}".format(job)
            mongo.db.upgrades.delete_one({'id': id})
            return {'status': 'deleted'}, 200
        except AttributeError:
            return {"status": "not found"}, 404


class Images(Resource):
    """
    Returns a list of image filenames based on platform
    """
    def get(self, id=None):
        with open('images.yaml', 'r') as images:
            IMAGES = yaml.safe_load(images)

        return IMAGES


class Regions(Resource):
    """
    Returns a list of regional tftp servers based
    unique site identifier encoded in hostname
    """
    def get(self, id=None):
        with open('regions.yaml', 'r') as regions:
            REGIONS = yaml.safe_load(regions)
        return REGIONS


api.add_resource(Regions,
                 '/api/regions',
                 endpoint='regions')

api.add_resource(Images,
                 '/api/images',
                 endpoint='images')

api.add_resource(Log,
                 '/api/logbin',
                 '/api/logbin/<string:logid>',
                 endpoint='logbin')

api.add_resource(CodeUpgradeJobView,
                 '/api/upgrade',
                 '/api/upgrade/<string:id>',
                 '/api/upgrade/<string:id>/<string:operation>',
                 endpoint='upgrade-api')

app.add_url_rule('/',
                 'home',
                 view_func=home,
                 methods=['GET'])

app.add_url_rule('/logbin',
                 'viewer',
                 view_func=viewer)

app.add_url_rule('/logbin/viewer/<string:log1>/diff/<string:log2>',
                 'diff-viewer',
                 view_func=diff)

app.add_url_rule('/logbin/embedded/<string:logid>',
                 'embedded-viewer',
                 view_func=viewer)

app.add_url_rule('/upgrade',
                 'jobview',
                 view_func=jobview,
                 methods=['GET', 'POST'])

app.add_url_rule('/upgrade/<string:id>',
                 'jobview-detail',
                 view_func=jobview,
                 methods=['GET', 'POST'])


if __name__ == '__main__':

    app.debug = True
    app.run(host='0.0.0.0')
