import yaml
import os
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_restful import Resource, Api, MethodView
from pyosupgrade.workflows import IOSUpgrade
from pyosupgrade.views.logbin import Log, viewer
from pyosupgrade.models import db, CodeUpgradeJob

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'upgrade.db')
db.init_app(app)
with app.app_context():
    db.create_all()

LOGBIN_URL = "http://127.0.0.1:5000/api/logbin"



@app.errorhandler(404)
def page_not_found(e):
    return render_template('notfound.html'), 404


def home():
    return redirect(url_for('jobview'))

def thread_launcher(job, request, operation):
    """
    initiates an IOS upgrade job from a request via webform or REST API
    :param job: CodeUpgradeJob an instance of CodeUpgradeJob
    :param request: flask.request a flask requst
    :param operation: string containing the desired process e.g start_staging start_upgrading
    :return:
    """

    # construct a URL for the API endpoint and glean user/pass from request
    url = url_for('upgrade-api', id=job.id, _external=True)
    if request.json:
        user, passwd = request.json['username'], request.json['password']
    elif request.form:
        user, passwd = request.form['username'], request.form['password']

    # start an upgrade thread which uses the job api for updating status
    thread = IOSUpgrade(url, user, passwd)

    # depending on operation we will trigger the appropriate process
    # thread.start_upgrade()
    #
    # operation="start_upgrade" invokes IOSUpgrade.start_upgrade()
    getattr(thread, operation)()
    return thread


def jobview(id=None):

    if request.method == 'GET':
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            return render_template('upgrade-detail.html',
                                   title="Job Detail",
                                   job=job)
        else:
            jobs = CodeUpgradeJob.query.all()
            return render_template('upgrade.html',
                                   title='Code Staging',
                                   logo='/static/img/4500.jpg',
                                   jobs=jobs)

    elif request.method == 'POST':
        # handle the case where this is an existing job (probably ready to be upgraded)
        if id:
            print ("starting upgrade")
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            # here we dispatch the request to a worker thread which will update itself via the API
            thread_launcher(job, request, "start_upgrade")
            # Notify the user
            flash("Upgrade Started", "success")
            return redirect(url_for('jobview', id=id))

        # handle the case where a new job is created
        else:
            # glean info from the form
            payload = request.form

            # this makes sure the final line has a CR
            devices = payload['hostnames'] + "\r\n"
            devices = devices.split('\r\n')
            print devices
            for d in devices:

                # make sure the device name/ip is valid, could use better verification e.g ping/etc
                if len(d) > 5:
                    print "Creating code upload job for {}".format(d)
                    job = CodeUpgradeJob(d, payload['username'], payload['password'])
                    db.session.add(job)
                    db.session.commit()
                    thread_launcher(job, request, "start_staging")

            flash("Submitted Job", "success")
            return redirect(url_for('jobview'))


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
            thread_launcher(job, request, "start_upgrade")
            return job.as_dict()

        # endpoint to update and existing job
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            print request.json
            for k, v in request.json.items():
                setattr(job, k, v)

            job.save()

            #print request.json

        else:
            if request.json:
                job = CodeUpgradeJob.from_dict(request.json)
                db.session.add(job)
                db.session.commit()
                thread_launcher(job, request, "start_staging")

                return job.as_dict()


class Images(Resource):
    """
    Returns a list of image filenames based on platform
    """
    def get(self, id=None):
        return IMAGES

class Regions(Resource):
    """
    Returns a list of regional tftp servers based unique site identifier encoded in hostname
    """
    def get(self, id=None):
        return REGIONS

api.add_resource(Regions, '/api/regions', endpoint='regions')
api.add_resource(Images, '/api/images', endpoint='images')

api.add_resource(Log, '/api/logbin', '/api/logbin/<int:id>', endpoint= 'logbin')
api.add_resource(CodeUpgradeJobView, '/api/upgrade', '/api/upgrade/<int:id>', '/api/upgrade/<int:id>/<string:operation>', endpoint='upgrade-api')

app.add_url_rule('/', 'home', view_func=home, methods=['GET'])
app.add_url_rule('/logbin/viewer/<int:id>', 'viewer', view_func=viewer)
app.add_url_rule('/upgrade', 'jobview', view_func=jobview, methods=['GET', 'POST'])
app.add_url_rule('/upgrade/<int:id>', 'jobview-detail' ,view_func=jobview, methods=['GET', 'POST'])


if __name__ == '__main__':
    with open('regions.yaml', 'r') as regions:
        REGIONS = yaml.safe_load(regions)

    with open('images.yaml', 'r') as images:
        IMAGES = yaml.safe_load(images)


    app.secret_key = 'CHANGEME'

    app.debug = True
    app.run()
