from pyosupgrade import BaseUpgrade
import tasks
import time
import datetime
import requests
from pyntc import ntc_device as NTC
from netmiko.ssh_exception import NetMikoTimeoutException


class IOSUpgrade(BaseUpgrade):

    def staging_process(self):
        print('starting staging job')
        self._attributes = self.get_job_details()
        self.device = self._attributes['device']
        self.log("Updated job details: {}".format(self._attributes))
        self.status = "CONNECTING"

        try:
            device = NTC(host=self.device, username=self.username, password=self.password, device_type="cisco_ios_ssh")
            hostname = device.facts['hostname']

        except Exception:
            self.status = "FAILED CONNECT"
        try:
            regions = requests.get(self.regions_url, headers=self.request_headers).json()
            regional_fs = regions[hostname[:2].upper()]['regional_fs']
            print("Using server {}".format(regional_fs))
        except KeyError:
            print("Unable to determine regional server")

        self.status = "IDENTIFY PLATFORM"
        sup_type, sup_output = tasks.identify_sup(device)

        print("Supervisor identified as {}".format(sup_type))

        self.status = "LOCATING IMAGE"
        images = requests.get(self.images_url, headers=self.request_headers).json()
        image = images[sup_type]['filename']
        print("Using image {}".format(image))
        self.target_image = image

        self.status = "TRANSFERRING"
        print("Initatiating file transfer...")
        url = "tftp://{}/{}".format(regional_fs, image)
        transfer, transfer_output = tasks.copy_remote_image(device, url)
        if transfer:
            print('File Transfer Suceeded')
            self.code_upload_log_url = self.logbin(transfer_output).json()['url']
            self.code_upload_status = "success"

        else:
            print('File Transfer Failed')
            self.sup_redundancy_log_url = self.logbin()

        # determine whether there is a sup redundancy
        self.status = "VERIFY_SUP_REDUNDANCY"
        sup_redundancy, sup_redundancy_output = tasks.verify_sup_redundancy(device)
        if sup_redundancy:
            print('Redundant Supervisors detected\n')
            self.sup_redundancy_log_url = self.logbin(sup_redundancy_output).json()['url']
            self.sup_redundancy_status = "success"

            self.status = "SYNCHRONIZING IMAGE"
            slave_copy, slave_copy_output = tasks.copy_image_to_slave(device, image)
            if slave_copy:
                print('File Transfer Suceeded')
                self.copy_code_to_slave_log_url = self.logbin(slave_copy_output).json()['url']
                self.copy_code_to_slave_status = "success"

        self.status = "CODE STAGING SUCCESSFUL"

        print('staging thread for {} exiting...'.format(self.device))

    def upgrade_process(self):
        print('starting staging job')
        self._attributes = self.get_job_details()
        self.device = self._attributes['device']
        reloaded = False

        # Connect to device
        try:
            connected = NTC(host=self.device, username=self.username,
                            password=self.password, device_type="cisco_ios_ssh")

        except NetMikoTimeoutException:
            connected = None

        # Proceed with upgrade
        self.status = "CONNECTING"

        if connected:
            hostname = connected.facts['hostname']
            start = datetime.datetime.now()

        else:
            self.status = "FAILED - COULD NOT CONNECT TO DEVICE"
            exit()

        # Backup Running Config
        self.status = "BACKING UP RUNNING CONFIG"
        output = connected.show('show running-config')
        if output:
            self.backup_running_config_status = "success"
            resp = self.logbin(output)
            self.backup_running_config_log_url = resp.json()['url']
        else:
            self.status = "FAILED - COULD NOT BACKUP RUNNING CONFIG"
            exit()

        # Change bootvar
        self.status = "SETTING BOOT VARIABLE"
        bootvar_result, bootvar_output = tasks.set_bootvar(connected, image=self.target_image)
        if bootvar_output:
            resp = self.logbin(bootvar_output)
            self.set_bootvar_status_log_url = resp.json()['url']
            self.set_bootvar_status = "success"
        else:
            self.status = "FAILED - COULD NOT SET BOOT VARIABLE"
            exit()

        # Verify bootvar
        self.status = "VERIFY BOOT VARIABLE"
        valid_bootvar, valid_bootvar_output = tasks.verify_bootvar(connected, self.target_image)

        if valid_bootvar:
            resp = self.logbin(valid_bootvar_output)
            self.verify_bootvar_status_log_url = resp.json()['url']
            self.set_bootvar_status = "success"

            self.verify_bootvar_status = "success"
            time.sleep(10)
        else:
            self.status = "FAILED - COULD NOT VERIFY BOOT VARIABLE"
            exit()

        # Reload
        self.status = "RELOADING"
        reload_output = tasks.reload_device(connected, command='redundancy reload shelf')
        resp = self.logbin("{}".format(reload_output))
        self.reload_status_log_url = resp.json()['url']

        reloaded = True
        if reloaded:
            self.reload_status = "success"

        else:
            self.status = "FAILED"
            exit()

        # wait for device to come line
        if reloaded and tasks.wait_for_reboot(self.device):
            self.status = "BACK ONLINE, WAITING FOR BOOTUP"
            # linecards may still be booting/upgrading
            time.sleep(300)

        else:
            self.status = "FAILED"
            exit()

        # Verify upgrade
        self.status = "VERIFYING UPGRADE"
        online = NTC(host=self.device, username=self.username, password=self.password, device_type="cisco_ios_ssh")

        image_output = online.show('sho ver | inc System image')
        upgraded = self.target_image in image_output
        if upgraded:
            self.verify_upgrade = "success"
            resp = self.logbin(image_output)
            self.verify_upgrade_log_url = resp.json()['url']

        else:
            self.verify_upgrade = "danger"

        print("Verify FPGA")
        self.status = "VERIFYING FPGA UPGRADE"
        fpga_status, fpga_output = tasks.verify_fpga(online)
        resp = self.logbin(fpga_output)
        self.verify_fpga_upgrade_status_log_url = resp.json()['url']

        if fpga_status:
            self.verify_fpga_upgrade_status = "success"

        else:
            self.verify_fpga_upgrade_status = "danger"

        if online and fpga_status and upgraded:
            self.status = "UPGRADE SUCCESSFUL"
            print("Upgrade was successful")
        else:
            self.status = "UPGRADE FAILED"
            print("Unable to verify image load was successful, please check manually")


