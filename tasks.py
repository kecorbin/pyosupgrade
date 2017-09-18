from app import app
from celery import Celery
from flask import url_for
from pyosupgrade.procedures.cat4500 import Catalyst4500Upgrade
from pyosupgrade.procedures.asr1000 import ASR1000Upgrade
from pyosupgrade.procedures.csr1000 import CSR1000Upgrade
from pyosupgrade.procedures.healthchecks import IntDescrChecker
#from pyosupgrade.models import CodeUpgradeJob

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)


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

@celery.task
def upgrade_launcher(url, mop, step, username, password):
    """
    this is essentially a class factory which initiates an
    IOS upgrade job from a request via webform or REST API

    :param url: str the url where the job details should be retrieved/updated
    :param stage str the step of the mop to begin (start_staging, start_upgrading)
    :param mop str method of procedure name that will be launched
    :param username: str username to execute the procedure
    :param password: string ios password

    :return:
    """
    print "Hello, i'm your celery worker"
    print ("Executing {} step {} for upgrade task {} on behalf of {}".format(mop, step, url, username))
    # potentially one last time to update the backend
    # job = CodeUpgradeJob.query.filter_by(id=job['id']).first()
    # print job

    procedure = METHOD_OF_PROCEDURES[mop]['procedure'](url, username, password)
    result = getattr(procedure, step)()
    print "Looks like we are just about done here! See You next time!"
