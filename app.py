import requests
import json
import yaml
import os
import time
import datetime
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_restful import Resource, Api, MethodView
from flask_sqlalchemy import SQLAlchemy
import pyosupgrade.upgrade as upgrade
from pyosupgrade.views.logbin import Log, viewer
from pyosupgrade.decorators import run_async
from pyosupgrade.display import success, info, fail
from pyntc import ntc_device as NTC
from netmiko.ssh_exception import NetMikoTimeoutException, NetMikoAuthenticationException


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'upgrade.db')
db = SQLAlchemy(app)
LOGBIN_URL = "http://127.0.0.1:5000/api/logbin"


class CodeUpgradeJob(db.Model):
    __tablename__ = 'staging-jobs'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(64), default="SUBMITTED")
    device = db.Column(db.String(64))
    username = db.Column(db.String(32))
    target_image = db.Column(db.String(128))
    code_upload_status = db.Column(db.String(128), default="unknown")
    code_upload_log_url = db.Column(db.String(128), default=None)

    sup_redundancy_status = db.Column(db.String(128), default="unknown")
    sup_redundancy_log_url = db.Column(db.String(128), default=None)

    copy_code_to_slave_status = db.Column(db.String(128), default="unknown")
    copy_code_to_slave_log_url = db.Column(db.String(128), default=None)

    backup_running_config_status = db.Column(db.String(128), default="unknown")
    backup_running_config_log_url = db.Column(db.String(128), default=None)

    set_bootvar_status = db.Column(db.String(128), default="unknown")
    set_bootvar_status_log_url = db.Column(db.String(128), default=None)

    verify_bootvar_status = db.Column(db.String(128), default="unknown")
    verify_bootvar_status_log_url = db.Column(db.String(128), default=None)

    reload_status = db.Column(db.String(128), default="unknown")
    reload_status_log_url = db.Column(db.String(128), default=None)

    verify_upgrade = db.Column(db.String(128), default = "unknown")
    verify_upgrade_log_url = db.Column(db.String(128), default=None)

    verify_fpga_upgrade_status = db.Column(db.String(128), default="unknown")
    verify_fpga_upgrade_status_log_url = db.Column(db.String(128), default=None)

    def __init__(self, device, username, password, mirrors, images):

        self.device = device
        self.username = username
        self.password = password
        self.mirrors = mirrors
        self.images = images
        self.status_log = ""

    def as_dict(self):
        return {"id": self.id,
                "device": self.device,
                "username": self.username,
                "status": self.status,
                "code_upload_status": self.code_upload_status,
                "code_upload_log_url": self.code_upload_log_url,
                "sup_redundancy_status": self.sup_redundancy_status,
                "sup_redundancy_log_url": self.sup_redundancy_log_url,
                "copy_code_to_slave_status": self.copy_code_to_slave_status,
                "copy_code_to_slave_log_url": self.copy_code_to_slave_log_url,
                "set_bootvar_status": self.set_bootvar_status,
                "backup_running_config_status": self.backup_running_config_status,
                "backup_running_config_log_url":  self.backup_running_config_log_url,
                "set_bootvar_status": self.set_bootvar_status_log_url,
                "set_bootvar_status_log_url": self.set_bootvar_status_log_url,
                "verify_bootvar_status": self.verify_bootvar_status,
                "verify_bootvar_status_log_url": self.verify_bootvar_status_log_url,
                "reload_status": self.reload_status,
                "reload_status_log_url": self.reload_status_log_url,
                "verify_upgrade": self.verify_upgrade,
                "verify_upgrade_log_url": self.verify_upgrade_log_url,
                "verify_fpga_upgrade_status": self.verify_fpga_upgrade_status,
                "verify_fpga_upgrade_status_log_url": self.verify_fpga_upgrade_status_log_url
                }

    def logbin(self, msg):
        headers = {"Content-Type": "application/json"}
        data = {"text": msg}

        resp = requests.post(LOGBIN_URL, data=json.dumps(data), headers=headers)
        return resp

    @classmethod
    def from_dict(cls, job_dict):
        print job_dict
        obj = cls()
        for k, v in job_dict.items():
            setattr(obj, k, v)
        return obj

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update_status(self, status):
        self.status = status
        self.save()

    @run_async
    def start_staging(self):
        info('starting code upload to {} asynchronously\n'.format(self.device))
        self.update_status("CONNECTING")

        try:
            device = NTC(host=self.device, username=self.username, password=self.password, device_type="cisco_ios_ssh")
            hostname = device.facts['hostname']

        except:
           fail("Unable to connect to device")
        try:
            regional_fs = self.mirrors[hostname[:2].upper()]['regional_fs']
            info("Using server {}".format(regional_fs))
        except KeyError:
            fail("Unable to determine regional server")

        self.update_status("IDENTIFY PLATFORM")
        sup_type, sup_output = upgrade.identify_sup(device)

        info("Supervisor identified as {}".format(sup_type))

        self.update_status("LOCATING IMAGE")
        image = self.images[sup_type]['filename']
        info("Using image {}".format(image))
        self.target_image = image
        self.save()

        self.update_status("TRANSFERRING")
        info("Initatiating file transfer...")
        url = "tftp://{}/{}".format(regional_fs, image)
        transfer, transfer_output = upgrade.copy_remote_image(device, url)
        if transfer:
            success('File Transfer Suceeded')
            self.code_upload_log_url = self.logbin(transfer_output).json()['url']
            self.code_upload_status = "success"
            self.save()

        else:
            fail('File Transfer Failed')
            self.sup_redundancy_log_url = self.logbin()
            self.save()

        # determine whether there is a sup redundancy
        self.update_status("VERIFY_SUP_REDUNDANCY")
        sup_redundancy, sup_redundancy_output = upgrade.verify_sup_redundancy(device)
        if sup_redundancy:
            info('Redundant Supervisors detected\n')
            self.sup_redundancy_log_url = self.logbin(sup_redundancy_output).json()['url']
            self.sup_redundancy_status = "success"
            self.save()

            self.update_status("SYNCHRONIZING IMAGE")
            self.save()
            slave_copy, slave_copy_output = upgrade.copy_image_to_slave(device, image)
            if slave_copy:
                success('File Transfer Suceeded')
                self.copy_code_to_slave_log_url = self.logbin(slave_copy_output).json()['url']
                self.copy_code_to_slave_status = "success"
                self.save()

        self.update_status("CODE STAGED")
        self.save()

        print('staging thread for {} exiting...'.format(self.device))

    @run_async
    def start_upgrade(self, user, passwd, device_type='cisco_ios_ssh'):
        reloaded = False

        # Connect to device
        try:
            connected = NTC(host=self.device, username=user, password=passwd, device_type=device_type)

        except NetMikoTimeoutException:
            connected = None

        # Proceed with upgrade
        if connected:
            hostname = connected.facts['hostname']
            start = datetime.datetime.now()
            print "Upgrade requested by {} at {}".format(user, start)
            # display_facts(connected)

            # Backup Running Config
            self.update_status("BACKING UP RUNNING CONFIG")
            output = connected.show('show running-config')
            if output:
                self.backup_running_config_status = "success"
                resp = self.logbin(output)
                self.backup_running_config_log_url = resp.json()['url']
                self.save()

            # Change bootvar
            self.update_status("SETTING BOOT VARIABLE")
            bootvar_result, bootvar_output = upgrade.set_bootvar(connected,
                                                                 image=self.target_image)
            if bootvar_output:
                resp = self.logbin(bootvar_output)
                self.set_bootvar_status_log_url = resp.json()['url']
                self.set_bootvar_status = "success"
                db.session.add(self)
                db.session.commit()

            self.update_status("VERIFY BOOT VARIABLE")
            valid_bootvar, valid_bootvar_output = upgrade.verify_bootvar(connected, self.target_image)

            if valid_bootvar:
                resp = self.logbin(valid_bootvar_output)
                self.verify_bootvar_status_log_url = resp.json()['url']
                self.set_bootvar_status = "success"
                self.save()

                self.verify_bootvar_status = "success"
                self.save()
                time.sleep(10)

                self.update_status("RELOADING")
                self.save()

                reload_output = upgrade.reload_device(connected, command='redundancy reload shelf')
                resp = self.logbin("{}".format(reload_output))
                self.reload_status_log_url = resp.json()['url']
                self.save()

                reloaded = True
                if reloaded:
                    self.reload_status = "success"
                    self.save()

            else:
                self.update_status("FAILED")

        else:
            print("Failed to connect to device")
            self.update_status("FAILED")

        if reloaded and upgrade.wait_for_reboot(self.device):

            self.update_status("BACK ONLINE, WAITING FOR BOOTUP")
            self.save()
            # linecards may still be booting/upgrading
            time.sleep(300)

        else:
            self.update_status("FAILED")

        self.update_status("VERIFYING UPGRADE")
        online = NTC(host=self.device, username=user, password=passwd, device_type=device_type)

        image_output = online.show('sho ver | inc System image')
        upgraded = self.target_image in image_output
        if upgraded:
            self.verify_upgrade = "success"
            resp = self.logbin(image_output)
            self.verify_upgrade_log_url = resp.json()['url']
            self.save()
        else:
            self.verify_upgrade = "danger"

        print("Verify FPGA")
        self.update_status("VERIFYING FPGA UPGRADE")
        fpga_status, fpga_output = upgrade.verify_fpga(online)
        resp = self.logbin(fpga_output)
        self.verify_fpga_upgrade_status_log_url = resp.json()['url']
        self.save()

        if fpga_status:
            self.verify_fpga_upgrade_status = "success"
            self.save()

        else:
            self.verify_fpga_upgrade_status = "danger"
            self.save()

        if online and fpga_status and upgraded:
            self.update_status("UPGRADE SUCCESSFUL")
            print("Upgrade was successful")
        else:
            self.update_status("UPGRADE FAILED")
            print("Unable to verify image load was successful, please check manually")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('notfound.html'), 404

def home():
    return redirect(url_for('jobview'))

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
        if id:
            print ("starting upgrade")
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            job.start_upgrade(request.form['username'], request.form['password'])
            flash("Submitted Job", "success")
            return redirect(url_for('jobview', id=id))

        else:
            payload = request.form
            devices = payload['hostnames'].split('\r\n')
            print devices
            for d in devices:
                if len(d) > 5:
                    print "Creating code upload job for {}".format(d)
                    job = CodeUpgradeJob(d, payload['username'], payload['password'], REGIONS, IMAGES)
                    db.session.add(job)
                    db.session.commit()
                    job.start_staging()

            flash("Submitted Job", "success")
            return redirect(url_for('jobview'))


class CodeUpgradeJobView(Resource):

    def get(self, id=None):
        print id
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            return job.as_dict()
        else:

            staging_jobs = CodeUpgradeJob.query.all()
            return [job.as_dict() for job in staging_jobs]

    def post(self, id=None):
        if id:
            job = CodeUpgradeJob.query.filter_by(id=id).first()
            print request.json

        else:
            if request.json:
                job = CodeUpgradeJob.from_dict(request.json)
                db.session.add(job)
                db.session.commit()
                return job.as_dict()


# class Upgrade(MethodView):
#
#     def post(self):
#         if request.json:
#             payload = request.json
#             upgrade = DeviceUpgrader(payload['host'],
#                               payload['username'],
#                               payload['password'],
#                               payload['image_filename'])
#             upgrade.start()
#             return {"status":"ok"}
#         else:
#             return {"status": "no JSON payload detected"}
#

# api.add_resource(Upgrade, '/api/upgrade')

api.add_resource(Log, '/api/logbin', '/api/logbin/<int:id>', endpoint= 'log')
api.add_resource(CodeUpgradeJobView, '/api/upgrade', '/api/upgrade/<int:id>')
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
    db.create_all()
    app.run()
