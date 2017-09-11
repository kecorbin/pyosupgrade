import yaml
import os
import tasks
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_restful import Resource, Api
from pyosupgrade.procedures.ios import IOSUpgrade
from pyosupgrade.procedures.cat4500 import Catalyst4500Upgrade
from pyosupgrade.procedures.asr1000 import ASR1000Upgrade
from pyosupgrade.procedures.csr1000 import CSR1000Upgrade
from pyosupgrade.views.logbin import Log, viewer
from pyosupgrade.models import db, CodeUpgradeJob

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
api = Api(app)


app.secret_key = 'CHANGEME'
# https://stackoverflow.com/questions/33738467/how-do-i-know-if-i-can-disable-sqlalchemy-track-modifications
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
path = os.path.join(basedir + '/upgrade.db')

app.config.update(
    CELERY_BROKER_URL='redis://redis:6379',
    CELERY_RESULT_BACKEND='redis://redis:6379'
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + path

db.init_app(app)
with app.app_context():
    db.create_all()

LOGBIN_URL = os.getenv('LOGBIN_API')
CALLBACK_API =  os.getenv('CALLBACK_API')
REGIONS_API = os.getenv('REGIONS_API')
IMAGES_API = os.getenv('IMAGES_API')


METHOD_OF_PROCEDURES = {
    "asr1000": {"description": "a fake mop",
                 "procedure": ASR1000Upgrade},
    "csr1000v": {"description": "a fake mop",
                 "procedure": CSR1000Upgrade},
    "cat4500-3.8.4-w-fpga": {"description": "Upgrade Catalyst 4500 with FPGA upgrade validation",
                             "procedure": Catalyst4500Upgrade}
}


@app.errorhandler(404)
def page_not_found(e):
    return render_template('notfound.html'), 404


def home():
    return redirect(url_for('jobview', _external=True))


def jobview(id=None):

    if request.method == 'GET':
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            return render_template('upgrade-detail.html',
                                   title="Job Detail",
                                   job=job,
                                   procedures=METHOD_OF_PROCEDURES)
        else:
            jobs = CodeUpgradeJob.query.all()
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
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            # here we dispatch the request to a worker thread
            # the thread which will update its record via the API

            # old way via threads
            # tasks.upgrade_launcher(job, request, "start_upgrade")
            #

            # new way via celery worker
            url = CALLBACK_API + '/{}'.format(job.id)
            tasks.upgrade_launcher.delay(url, mop, 'start_upgrade', username, password)

            # Notify the user
            flash("Upgrade Started", "success")
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
                    job = CodeUpgradeJob(d,
                                         payload['username'],
                                         payload['password'],
                                         payload['mop'])
                    db.session.add(job)
                    db.session.commit()

                    # old way via threads
                    # thread_launcher(job, request, "start_staging")

                    # new way via celery w/ REST callbacks
                    url = CALLBACK_API + "/{}".format(job.id)
                    tasks.upgrade_launcher.delay(url, mop, 'start_staging', username, password)

            flash("Submitted Job", "success")
            return redirect(url_for('jobview', _external=True))


class CodeUpgradeJobView(Resource):

    def get(self, id=None):
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            return job.as_dict()
        else:

            staging_jobs = CodeUpgradeJob.query.all()
            return [job.as_dict() for job in staging_jobs]

    def post(self, id=None, operation=None):
        # endpoint to start job
        if operation == "start" and id:

            job = CodeUpgradeJob.query.filter_by(id=id).first()

            # new way via celery w/ REST callbacks
            url = CALLBACK_API + "/{}".format(job.id)
            tasks.upgrade_launcher.delay(url, job.mop, 'start_upgrade', request['username'], request['password'])

            return job.as_dict()

        # endpoint to update and existing job
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            print request.json
            for k, v in request.json.items():
                setattr(job, k, v)

            job.save()

        # new job received via api
        else:
            if request.json:
                job = CodeUpgradeJob.from_dict(request.json)
                db.session.add(job)
                db.session.commit()
                # old way via threads
                # thread_launcher(job, request, "start_staging")

                # new way via celery w/ REST callbacks
                url = CALLBACK_API + "/{}".format(job.id)
                tasks.upgrade_launcher.delay(url, job.mop, 'start_staging', request.json['username'], request.json['password'])

                return job.as_dict()

    def delete(self, id=None):
        try:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            print "deleting job {}".format(job)
            job.delete()
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
                 '/api/logbin/<int:logid>',
                 endpoint='logbin')

api.add_resource(CodeUpgradeJobView,
                 '/api/upgrade',
                 '/api/upgrade/<int:id>',
                 '/api/upgrade/<int:id>/<string:operation>',
                 endpoint='upgrade-api')

app.add_url_rule('/',
                 'home',
                 view_func=home,
                 methods=['GET'])

app.add_url_rule('/logbin/viewer/<int:logid>',
                 'viewer',
                 view_func=viewer)

app.add_url_rule('/upgrade',
                 'jobview',
                 view_func=jobview,
                 methods=['GET', 'POST'])

app.add_url_rule('/upgrade/<int:id>',
                 'jobview-detail',
                 view_func=jobview,
                 methods=['GET', 'POST'])


if __name__ == '__main__':


    app.debug = True
    app.run(host='0.0.0.0')
