import requests
import json
from pyosupgrade.decorators import run_async


class BaseUpgrade(object):

    def __init__(self, job_url, username, password):
        print ("initializing IOS upgrade Task {}".format(self))
        self.request_headers = {"Content-Type": "application/json"}
        self.job_url = job_url
        self.device = None
        self.username = username
        self.password = password
        self._attributes = dict()
        self._status_log = str()

    @run_async
    def start_staging(self):
        try:
            self.staging_process()
        except Exception as e:
            self.status = "FAILED - {}".format(e[:64])

    @run_async
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

    @classmethod
    def from_dict(cls, job_dict):
        print job_dict
        obj = cls(job_dict['id'])
        for k, v in job_dict.items():
            setattr(obj['attributes'], k, v)
        return obj

    def get_job_details(self):
        print "Getting job details from {}".format(self.job_url)
        resp = requests.get(self.job_url, headers=self.request_headers)
        if resp.ok and resp.json():
            return resp.json()

    def _update_job(self):
        resp = requests.post(self.job_url,
                             data=json.dumps(self._attributes),
                             headers=self.request_headers)
        if resp.ok:
            print("Updated job api for id {}".format(self._attributes['id']))

    def logbin(self, msg):
        data = {"text": msg}
        resp = requests.post(self.logbin_url,
                             data=json.dumps(data),
                             headers=self.request_headers)
        return resp.json()['url']

    def log(self, msg):
        self._status_log += msg + "\n"

    @property
    def status(self):
        return self._attributes['status']

    @status.setter
    def status(self, status):
        self    ._attributes['status'] = status
        self._update_job()

    @property
    def target_image(self):
        return self._attributes['target_image']

    @target_image.setter
    def target_image(self, target_image):
        self    ._attributes['target_image'] = target_image
        self._update_job()

    @property
    def code_upload_status(self):
        return self.attributes['code_upload_status']

    @code_upload_status.setter
    def code_upload_status(self, status):
        self._attributes['code_upload_status'] = status
        self._update_job()

    @property
    def code_upload_log_url(self):
        return self._attributes["code_upload_log_url"]

    @code_upload_log_url.setter
    def code_upload_log_url(self, status):
        self._attributes["code_upload_log_url"] = status
        self._update_job()

    @property
    def sup_redundancy_status(self):
        return self._attributes["sup_redundancy_status"]

    @sup_redundancy_status.setter
    def sup_redundancy_status(self, status):
        self._attributes["sup_redundancy_status"] = status
        self._update_job()

    @property
    def sup_redundancy_log_url(self):
        return self._attributes["sup_redundancy_log_url"]

    @sup_redundancy_log_url.setter
    def sup_redundancy_log_url(self, status):
        self._attributes["sup_redundancy_log_url"] = status
        self._update_job()

    @property
    def copy_code_to_slave_status(self):
        return self._attributes["copy_code_to_slave_status"]

    @copy_code_to_slave_status.setter
    def copy_code_to_slave_status(self, status):
        self._attributes["copy_code_to_slave_status"] = status
        self._update_job()

    @property
    def copy_code_to_slave_log_url(self):
        return self._attributes["copy_code_to_slave_log_url"]

    @copy_code_to_slave_log_url.setter
    def copy_code_to_slave_log_url(self, status):
        self._attributes["copy_code_to_slave_log_url"] = status
        self._update_job()

    @property
    def set_bootvar_status(self):
        return self._attributes["set_bootvar_status"]

    @set_bootvar_status.setter
    def set_bootvar_status(self, status):
        self._attributes["set_bootvar_status"] = status
        self._update_job()

    @property
    def backup_running_config_status(self):
        return self._attributes["backup_running_config_status"]

    @backup_running_config_status.setter
    def backup_running_config_status(self, status):
        self._attributes["backup_running_config_status"] = status
        self._update_job()

    @property
    def backup_running_config_log_url(self):
        return self._attributes["backup_running_config_log_url"]

    @backup_running_config_log_url.setter
    def backup_running_config_log_url(self, status):
        self._attributes["backup_running_config_log_url"] = status
        self._update_job()

    @property
    def set_bootvar_status(self):
        return self._attributes["set_bootvar_status"]

    @set_bootvar_status.setter
    def set_bootvar_status(self, status):
        self._attributes["set_bootvar_status"] = status
        self._update_job()

    @property
    def set_bootvar_status_log_url(self):
        return self._attributes["set_bootvar_status_log_url"]

    @set_bootvar_status_log_url.setter
    def set_bootvar_status_log_url(self, status):
        self._attributes["set_bootvar_status_log_url"] = status
        self._update_job()

    @property
    def verify_bootvar_status(self):
        return self._attributes["verify_bootvar_status"]

    @verify_bootvar_status.setter
    def verify_bootvar_status(self, status):
        self._attributes["verify_bootvar_status"] = status
        self._update_job()

    @property
    def verify_bootvar_status_log_url(self):
        return self._attributes["verify_bootvar_status_log_url"]

    @verify_bootvar_status_log_url.setter
    def verify_bootvar_status_log_url(self, status):
        self._attributes["verify_bootvar_status_log_url"] = status
        self._update_job()

    @property
    def reload_status(self):
        return self._attributes["reload_status"]

    @reload_status.setter
    def reload_status(self, status):
        self._attributes["reload_status"] = status
        self._update_job()

    @property
    def reload_status_log_url(self):
        return self._attributes["reload_status_log_url"]

    @reload_status_log_url.setter
    def reload_status_log_url(self, status):
        self._attributes["reload_status_log_url"] = status
        self._update_job()

    @property
    def verify_upgrade(self):
        return self._attributes["verify_upgrade"]

    @verify_upgrade.setter
    def verify_upgrade(self, status):
        self._attributes["verify_upgrade"] = status
        self._update_job()

    @property
    def verify_upgrade_log_url(self):
        return self._attributes["verify_upgrade_log_url"]

    @verify_upgrade_log_url.setter
    def verify_upgrade_log_url(self, status):
        self._attributes["verify_upgrade_log_url"] = status
        self._update_job()

    @property
    def verify_fpga_upgrade_status(self):
        return self._attributes["verify_fpga_upgrade_status"]

    @verify_fpga_upgrade_status.setter
    def verify_fpga_upgrade_status(self, status):
        self._attributes["verify_fpga_upgrade_status"] = status
        self._update_job()

    @property
    def custom_verification_1_name(self):
        return self._attributes["custom_verification_1_name"]

    @custom_verification_1_name.setter
    def custom_verification_1_name(self, name):
        self._attributes["custom_verification_1_name"] = name
        self._update_job()

    @property
    def custom_verification_1_status(self):
        return self._attributes["custom_verification_1_status"]

    @custom_verification_1_status.setter
    def custom_verification_1_status(self, status):
        self._attributes["custom_verification_1_status"] = status
        self._update_job()

    @property
    def custom_verification_1_status_log_url(self):
        return self._attributes["custom_verification_1_status_log_url"]

    @custom_verification_1_status_log_url.setter
    def custom_verification_1_status_log_url(self, url):
        self._attributes["custom_verification_1_status_log_url"] = url
        self._update_job()

    @property
    def custom_verification_2_name(self):
        return self._attributes["custom_verification_2_name"]

    @custom_verification_2_name.setter
    def custom_verification_2_name(self, name):
        self._attributes["custom_verification_2_name"] = name
        self._update_job()

    @property
    def custom_verification_2_status(self):
        return self._attributes["custom_verification_2_status"]

    @custom_verification_2_status.setter
    def custom_verification_2_status(self, status):
        self._attributes["custom_verification_2_status"] = status
        self._update_job()

    @property
    def custom_verification_2_status_log_url(self):
        return self._attributes["custom_verification_2_status_log_url"]

    @custom_verification_2_status_log_url.setter
    def custom_verification_2_status_log_url(self, url):
        self._attributes["custom_verification_2_status_log_url"] = url
        self._update_job()

    # @property
    # def verify_fpga_upgrade_status_log_url(self):
    #     return self._attributes["verify_fpga_upgrade_status_log_url"]
    #
    # @verify_fpga_upgrade_status_log_url.setter
    # def verify_fpga_upgrade_status_log_url(self, status):
    #     self._attributes["verify_fpga_upgrade_status_log_url"] = status
    #     self._update_job()

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
