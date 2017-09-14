from pyosupgrade.procedures import BaseUpgrade
import requests
from pyosupgrade.tasks import generic
from pyntc import ntc_device as NTC
import re


class IntDescrChecker(BaseUpgrade):

    reload_command = "reload"

    @property
    def steps(self):
        steps = [('Verify All Interfaces have Descriptions', self.int_check_status, self.int_check_log_url)]
        return steps


    @property
    def int_check_status(self):
        return self._attributes.get('int_check_status', "default")

    @int_check_status.setter
    def int_check_status(self, status):
        self._attributes['int_check_status'] = status
        self._update_job()

    @property
    def int_check_log_url(self):
        return self._attributes.get('int_check_status_log_url', "default")

    @int_check_log_url.setter
    def int_check_log_url(self, url):
        self._attributes['int_check_status_log_url'] = url
        self._update_job()


    def staging_process(self):

        print('starting verification job')
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
            hostname = self._pyntc.facts['hostname']

        except Exception:
            self.status = "FAILED CONNECT"

        self.status = "Verifying Interfaces"
        output = device.native.send_command('show interface description')

        interfaces = [l.split() for l in output.split('\n')]

        badlist = list()
        for i in interfaces:
            # [u'Gi1/1', u'up', u'up', u'LAB_GW_OUT']
            # [u'Fa1', u'down', u'down']
            if (i[1] == 'up') and (i[2] == 'up'):
                try:
                    descr = i[3]
                except:
                    badlist.append(i)
                    pass

        output = ""
        for i in badlist:
            output += "{} is {}/{} and has no description\n".format(i[0], i[1], i[2])

        self.int_check_log_url = self.logbin(output)
        if len(badlist) > 0:
            self.int_check_status = "warning"
        else:
            self.int_check_status = "success"

        # print messages are displayed in worker console
        print('staging thread for {} exiting...'.format(self.device))