import requests
import json


class BaseUpgrade(object):

    def __init__(self, job_url, username, password):
        print ("initializing IOS upgrade Task {}".format(self))
        self.request_headers = {"Content-Type": "application/json"}
        self.job_url = job_url
        self.username = username
        self.password = password
        self._attributes = dict()
        self._attributes['job_url'] = job_url
        self._status_log = ""

    def as_dict(self):

        # intialize response
        resp = dict()
        #
        # except for a few "reserved" keys
        ignored_keys = ["_id", "password"]

        for key in self._attributes:
            if key not in ignored_keys:
                # we'll also default out any empty parameters
                # ideally the status should always be a bootstrap class
                resp[key] = self._attributes.get(key)
        return resp

    @classmethod
    def from_dict(cls, job_dict):
        # we may not always have these fields
        job_url = job_dict.get('job_url', None)
        username = job_dict.get('username', None)
        password = job_dict.get('password', None)
        # creates new object
        obj = cls(job_url, username, password)
        for k, v in job_dict.items():
            obj._attributes[k] = v
        return obj

    def start_staging(self):
        try:
            self.staging_process()
        except Exception as e:
            self.status = "FAILED - {}".format(e[:64])

    def start_upgrade(self):
        try:
            self.upgrade_process()
        except Exception as e:
            self.status = "FAILED - {}".format(e[:64])

    def staging_process(self):
        raise NotImplementedError

    def upgrade_process(self):
        raise NotImplementedError

    def register_custom_tasks(self):
        self.custom_verification_1_name = "Custom Verification 1"
        self.custom_verification_2_name = "Custom Verification 2"


    def get_job_details(self):
        print "Getting job details from {}".format(self.job_url)
        resp = requests.get(self.job_url, headers=self.request_headers)
        if resp.ok and resp.json():
            return resp.json()

    def _update_job(self):
        print "seeing if we have a url job with {}".format(self.job_url)
        if self.job_url:
            print "updating job with {}".format(self.as_dict())
            resp = requests.post(self.job_url,
                                 data=json.dumps(self.as_dict()),
                                 headers=self.request_headers)

            if resp.ok:
                print("Updated job api for id {} Successfully".format(self._attributes['id']))
            else:
                print("rur roh - i had a problem updating the api")
            print resp.text

    def logbin(self, msg):
        data = {"text": msg}
        resp = requests.post(self.logbin_url,
                             data=json.dumps(data),
                             headers=self.request_headers)
        return resp.json()['url']

    def log(self, msg):
        self._status_log += msg + "\n"

    @property
    def id(self):
        return self._attributes.get('id', "default")

    @id.setter
    def status(self, id):
        self._attributes['id'] = id
        self._update_job()


    @property
    def status(self):
        return self._attributes.get('status', "default")

    @status.setter
    def status(self, status):
        self._attributes['status'] = status
        self._update_job()

    @property
    def mop(self):
        return self._attributes.get('mop', "default")

    @mop.setter
    def mop(self, mop):
        self._attributes['mop'] = mop
        self._update_job()

    @property
    def device(self):
        return self._attributes.get('device', None)

    @device.setter
    def device(self, device):
        self._attributes['device'] = device
        self._update_job()

    @property
    def target_image(self):
        return self._attributes.get('target_image', "default")

    @target_image.setter
    def target_image(self, target_image):
        self    ._attributes['target_image'] = target_image
        self._update_job()

    @property
    def code_upload_status(self):
        return self._attributes.get('code_upload_status', "default")


    @code_upload_status.setter
    def code_upload_status(self, status):
        self._attributes['code_upload_status'] = status
        self._update_job()

    @property
    def code_upload_log_url(self):
        return self._attributes.get('code_upload_log_url', None)


    @code_upload_log_url.setter
    def code_upload_log_url(self, status):
        self._attributes['code_upload_log_url'] = status
        self._update_job()

    @property
    def sup_redundancy_status(self):
        return self._attributes.get('sup_redundancy_status', "default")


    @sup_redundancy_status.setter
    def sup_redundancy_status(self, status):
        self._attributes["sup_redundancy_status"] = status
        self._update_job()

    @property
    def sup_redundancy_log_url(self):
        return self._attributes.get('sup_redundancy_log_url', None)


    @sup_redundancy_log_url.setter
    def sup_redundancy_log_url(self, status):
        self._attributes["sup_redundancy_log_url"] = status
        self._update_job()

    @property
    def copy_code_to_slave_status(self):
        return self._attributes.get('copy_code_to_slave_status', "default")


    @copy_code_to_slave_status.setter
    def copy_code_to_slave_status(self, status):
        self._attributes["copy_code_to_slave_status"] = status
        self._update_job()

    @property
    def copy_code_to_slave_log_url(self):
        return self._attributes.get('copy_code_to_slave_log_url', None)


    @copy_code_to_slave_log_url.setter
    def copy_code_to_slave_log_url(self, status):
        self._attributes["copy_code_to_slave_log_url"] = status
        self._update_job()

    @property
    def set_bootvar_status(self):
        return self._attributes.get('set_bootvar_status', "default")


    @set_bootvar_status.setter
    def set_bootvar_status(self, status):
        self._attributes["set_bootvar_status"] = status
        self._update_job()

    @property
    def set_bootvar_status_log_url(self):
        return self._attributes.get('set_bootvar_status_log_url', None)

    @set_bootvar_status_log_url.setter
    def set_bootvar_status_log_url(self, status):
        self._attributes["set_bootvar_status_log_url"] = status
        self._update_job()


    @property
    def backup_running_config_status(self):
        return self._attributes.get('backup_running_config_status', "default")


    @backup_running_config_status.setter
    def backup_running_config_status(self, status):
        self._attributes["backup_running_config_status"] = status
        self._update_job()

    @property
    def backup_running_config_log_url(self):
        return self._attributes.get('backup_running_config_log_url', None)


    @backup_running_config_log_url.setter
    def backup_running_config_log_url(self, status):
        self._attributes["backup_running_config_log_url"] = status
        self._update_job()


    @property
    def verify_bootvar_status(self):
        return self._attributes.get('verify_bootvar_status', "default")


    @verify_bootvar_status.setter
    def verify_bootvar_status(self, status):
        self._attributes["verify_bootvar_status"] = status
        self._update_job()

    @property
    def verify_bootvar_status_log_url(self):
        return self._attributes.get('verify_bootvar_status_log_url', None)


    @verify_bootvar_status_log_url.setter
    def verify_bootvar_status_log_url(self, status):
        self._attributes["verify_bootvar_status_log_url"] = status
        self._update_job()

    @property
    def reload_status(self):
        return self._attributes.get('reload_status', "default")

    @reload_status.setter
    def reload_status(self, status):
        self._attributes["reload_status"] = status
        self._update_job()

    @property
    def reload_status_log_url(self):
        return self._attributes.get('reload_status_log_url', None)


    @reload_status_log_url.setter
    def reload_status_log_url(self, status):
        self._attributes["reload_status_log_url"] = status
        self._update_job()

    @property
    def verify_upgrade(self):
        return self._attributes.get('verify_upgrade', "default")


    @verify_upgrade.setter
    def verify_upgrade(self, status):
        self._attributes["verify_upgrade"] = status
        self._update_job()

    @property
    def verify_upgrade_log_url(self):
        return self._attributes.get('verify_upgrade_log_url', None)


    @verify_upgrade_log_url.setter
    def verify_upgrade_log_url(self, status):
        self._attributes["verify_upgrade_log_url"] = status
        self._update_job()

    @property
    def custom_verification_1_name(self):
        return self._attributes.get('custom_verification_1_name', "Custom Verification 1")


    @custom_verification_1_name.setter
    def custom_verification_1_name(self, name):
        self._attributes["custom_verification_1_name"] = name
        self._update_job()

    @property
    def custom_verification_1_status(self):
        return self._attributes.get('custom_verification_1_status', "default")

    @custom_verification_1_status.setter
    def custom_verification_1_status(self, status):
        self._attributes["custom_verification_1_status"] = status
        self._update_job()

    @property
    def custom_verification_1_status_log_url(self):
        return self._attributes.get('custom_verification_1_status_log_url', None)

    @custom_verification_1_status_log_url.setter
    def custom_verification_1_status_log_url(self, url):
        self._attributes["custom_verification_1_status_log_url"] = url
        self._update_job()

    @property
    def custom_verification_2_name(self):
        return self._attributes.get('custom_verification_2_name', "Custom Verification 2")

    @custom_verification_2_name.setter
    def custom_verification_2_name(self, name):
        self._attributes["custom_verification_2_name"] = name
        self._update_job()

    @property
    def custom_verification_2_status(self):
        return self._attributes.get('custom_verification_2_status', "default")

    @custom_verification_2_status.setter
    def custom_verification_2_status(self, status):
        self._attributes["custom_verification_2_status"] = status
        self._update_job()

    @property
    def custom_verification_2_status_log_url(self):
        return self._attributes.get('custom_verification_2_status_log_url', None)

    @custom_verification_2_status_log_url.setter
    def custom_verification_2_status_log_url(self, url):
        self._attributes["custom_verification_2_status_log_url"] = url
        self._update_job()

    @property
    def regions_url(self):
        return self._attributes["regions_url"]

    @regions_url.setter
    def regions_url(self, status):
        self._attributes["regions_url"] = status
        self._update_job()

    @property
    def images_url(self):
        return self._attributes["images_url"]

    @images_url.setter
    def images_url(self, status):
        self._attributes["images_url"] = status
        self._update_job()

    @property
    def logbin_url(self):
        return self._attributes["logbin_url"]

    @logbin_url.setter
    def logbin_url(self, status):
        self._attributes["logbin_url"] = status
        self._update_job()
