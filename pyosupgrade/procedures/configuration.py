from pyosupgrade.procedures import BaseUpgrade
from pyntc import ntc_device as NTC


class BackupRunningConfiguration(BaseUpgrade):

    @property
    def steps(self):
        steps = [('Get Running Config', self.get_running_config_status, self.running_config_url)]
        return steps

    @property
    def get_running_config_status(self):
        return self._attributes.get('get_running_config_status', "default")

    @get_running_config_status.setter
    def get_running_config_status(self, status):
        self._attributes['get_running_config_status'] = status
        self._update_job()

    @property
    def running_config_url(self):
        return self._attributes.get('running_config_url', "default")

    @running_config_url.setter
    def running_config_url(self, url):
        self._attributes['running_config_url'] = url
        self._update_job()


    def staging_process(self):

        print('starting get running config job')
        self._attributes = self.get_job_details()
        self.device = self._attributes['device']
        self.log("Updated job details: {}".format(self._attributes))
        self.status = "CONNECTING"
        self._pyntc = None

        try:
            self._pyntc = NTC(host=self.device,
                              username=self.username,
                              password=self.password,
                              device_type="cisco_ios_ssh")
            device = self._pyntc

        except Exception:
            self.status = "FAILED CONNECT"

        self.status = "Getting Configuration"

        output = device.native.send_command('show running-config')
        self.running_config_url = self.logbin(output)
        if len(output) > 0:
            self.get_running_config_status = "success"
            self.status = "SUCCESS"
        else:
            self.get_running_config_status = "warn"
            self.status = "WARNING"
        # print messages are displayed in worker console
        print('staging thread for {} exiting...'.format(self.device))