import datetime
import time

import requests
from netmiko.ssh_exception import NetMikoTimeoutException
from pyntc import ntc_device as NTC
from pyosupgrade.procedures import BaseUpgrade
from pyosupgrade.tasks import generic


class IOSUpgrade(BaseUpgrade):

    def staging_process(self):
        print('starting staging job')
        self._attributes = self.get_job_details()
        self.device = self._attributes['device']
        self.register_custom_tasks()
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
        try:
            regions = requests.get(self.regions_url,
                                   headers=self.request_headers).json()
            regional_fs = regions[hostname[:2].upper()]['regional_fs']
            print("Using server {}".format(regional_fs))
        except KeyError:
            print("Unable to determine regional server")

        self.status = "IDENTIFY PLATFORM"
        sup_type, sup_output = self.identify_platform()

        print("Supervisor identified as {}".format(sup_type))

        self.status = "LOCATING IMAGE"
        images = requests.get(self.images_url,
                              headers=self.request_headers).json()
        image = images[sup_type]['filename']
        print("Using image {}".format(image))
        self.target_image = image

        self.status = "TRANSFERRING"
        print("Initatiating file transfer...")
        url = "tftp://{}/{}".format(regional_fs, image)
        transfer, transfer_output = generic.copy_remote_image(device, url)
        logbin_url = self.logbin(transfer_output)
        self.code_upload_log_url = logbin_url
        if transfer:
            print('File Transfer Suceeded')
            self.code_upload_status = "success"
        else:
            print('File Transfer Failed')
            self.code_upload_status = "danger"
            exit()

        # determine whether there is a sup redundancy
        self.status = "VERIFY_SUP_REDUNDANCY"
        result = generic.verify_sup_redundancy(device)
        sup_redundancy, sup_redundancy_output = result
        self.sup_redundancy_log_url = self.logbin(sup_redundancy_output)
        if sup_redundancy:
            print('Redundant Supervisors detected\n')
            self.sup_redundancy_status = "success"

            self.status = "SYNCHRONIZING IMAGE"
            result = generic.copy_image_to_slave(device, image)
            slave_copy, slave_copy_output = result
            self.copy_code_to_slave_log_url = self.logbin(slave_copy_output)
            if slave_copy:
                print('File Transfer Suceeded')
                self.copy_code_to_slave_status = "success"
            else:
                self.copy_code_to_slave_status = "danger"
        else:
            print('Sups not redundant')
            self.copy_code_to_slave_status = "warning"

        self.status = "CODE STAGING SUCCESSFUL"

        print('staging thread for {} exiting...'.format(self.device))

    def upgrade_process(self):
        print('starting staging job')
        self._attributes = self.get_job_details()
        self.device = self._attributes['device']
        reloaded = False

        # Connect to device
        try:
            connected = NTC(host=self.device,
                            username=self.username,
                            password=self.password,
                            device_type="cisco_ios_ssh")

        except NetMikoTimeoutException:
            connected = None

        # Proceed with upgrade
        self.status = "CONNECTING"

        if connected:
            hostname = connected.facts['hostname']
            start = datetime.datetime.now()
            print("Upgrade for {} started at {}".format(hostname,
                                                        start))

        else:
            self.status = "FAILED - COULD NOT CONNECT TO DEVICE"
            exit()

        # Backup Running Config
        self.status = "BACKING UP RUNNING CONFIG"
        output = connected.show('show running-config')
        if output:
            self.backup_running_config_status = "success"
            logbin_url = self.logbin(output)
            self.backup_running_config_log_url = logbin_url
        else:
            self.status = "FAILED - COULD NOT BACKUP RUNNING CONFIG"
            exit()

        # Change bootvar
        self.status = "SETTING BOOT VARIABLE"
        result = generic.set_bootvar(connected, image=self.target_image)
        bootvar_result, bootvar_output = result
        if bootvar_output:
            logbin_url = self.logbin(bootvar_output)
            self.set_bootvar_status_log_url = logbin_url
            self.set_bootvar_status = "success"
        else:
            self.status = "FAILED - COULD NOT SET BOOT VARIABLE"
            exit()

        # Verify bootvar
        self.status = "VERIFY BOOT VARIABLE"
        result = generic.verify_bootvar(connected, self.target_image)
        valid_bootvar, valid_bootvar_output = result

        if valid_bootvar:
            logbin_url = self.logbin(valid_bootvar_output)
            self.verify_bootvar_status_log_url = logbin_url
            self.set_bootvar_status = "success"
            self.verify_bootvar_status = "success"
            time.sleep(10)
        else:
            self.status = "FAILED - COULD NOT VERIFY BOOT VARIABLE"
            exit()

        # Reload
        self.status = "RELOADING"
        reload_output = generic.reload_device(connected,
                                              command='redundancy reload shelf')
        logbin_url = self.logbin("{}".format(reload_output))
        self.reload_status_log_url = logbin_url

        reloaded = True
        if reloaded:
            self.reload_status = "success"

        else:
            self.status = "FAILED"
            exit()

        # wait for device to come line
        if reloaded and generic.wait_for_reboot(self.device):
            self.status = "BACK ONLINE, WAITING FOR BOOTUP"
            # linecards may still be booting/upgrading
            time.sleep(300)

        else:
            self.status = "FAILED"
            exit()

        # Verify upgrade
        self.status = "VERIFYING UPGRADE"
        online = NTC(host=self.device,
                     username=self.username,
                     password=self.password,
                     device_type="cisco_ios_ssh")

        image_output = online.show('sho ver | inc System image')
        upgraded = self.target_image in image_output
        if upgraded:
            self.verify_upgrade = "success"
            logbin_url = self.logbin(image_output)
            self.verify_upgrade_log_url = logbin_url

        else:
            self.verify_upgrade = "danger"


        custom_1 = self.custom_verification_1()
        custom_2 = self.custom_verification_2()

        if all([online, upgraded, custom_1, custom_2]):
            self.status = "UPGRADE SUCCESSFUL"
            print("Upgrade was successful")
        else:
            self.status = "UPGRADE FAILED"
            print("Unable to verify image load was successful")

        end = datetime.datetime.now()
        print("Upgrade for {} ended at {}".format(hostname, end))

    def custom_verification_1(self):
        return True

    def custom_verification_2(self):
        return True