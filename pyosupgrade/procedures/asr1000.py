import datetime
import datetime
import time
import requests
from netmiko.ssh_exception import NetMikoTimeoutException
from pyosupgrade.tasks import generic
from ios import IOSUpgrade
from pyntc import ntc_device as NTC


class ASR1000Upgrade(IOSUpgrade):

    reload_command = "reload"

    @property
    def steps(self):
        steps = [('Code Transfer', self.code_upload_status, self.code_upload_log_url),
                 ('Verify Supervisor Redundancy', self.sup_redundancy_status, self.sup_redundancy_log_url),
                 ('Synchronize Code to Standby Supervisor', self.copy_code_to_slave_status, self.copy_code_to_slave_log_url),
                 ('Backup Running Config', self.backup_running_config_status, self.backup_running_config_log_url),
                 ('Set Boot Variable', self.set_bootvar_status, self.set_bootvar_status_log_url),
                 ('Verify Boot Variable', self.verify_bootvar_status, self.verify_bootvar_status_log_url),
                 ('Upgrade ROMMON', self.set_rommon_status, self.set_rommon_log_url),
                 ('Reload Device', self.reload_status, self.reload_status_log_url),
                 ('Verify Upgrade', self.verify_upgrade, self.verify_upgrade_log_url, self.verify_upgrade_log_url),
                 (self.custom_verification_1_name, self.custom_verification_1_status, self.custom_verification_1_status_log_url),
                 (self.custom_verification_2_name, self.custom_verification_2_status, self.custom_verification_2_status_log_url)
                 ]
        return steps

    @property
    def verification_commands(self):
        commands = [
            'show version',
            'show platform',
            'show bootvar',
            'show inventory',
            'show environment all',
            'show run',
            'show cdp neighbors',
            'show ip interface brief',
            'show ip arp',
            'show ip route',
            'show processes cpu history',
            'show processes memory sorted',
            'show log'
        ]
        return commands


    def identify_platform(self):
        """
        get's supervisor information from an ASR1000 this is used to
        identify the correct image to use

        :return: str Supervisor PID
        """

        output = self._pyntc.show('show platform')
        if "ASR1000-RP2" in output:
            return "ASR1000-RP2", output
        # TODO verify this is the appropriate RP1 output
        elif "ASR1000-RP1" in output:
            return "ASR1000-RP1", output
        elif "ASR1002-RP1" in output:
            return "ASR1000-RP1", output
        else:
            return "UNKNOWN", output


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

        self.status = "TRANSFERRING IOS"
        print("Initatiating file transfer...")
        url = "tftp://{}/{}".format(regional_fs, image)
        ios_transfer, ios_transfer_output = generic.copy_remote_image(device, url, expect1="bytes copied", expect2="Signature Verified")

        self.status = "LOCATING ROMMON"
        rommon = images[sup_type]['rommon']

        print("Using image {}".format(rommon))
        self.target_rommon = rommon

        self.status = "TRANSFERRING ROMMON"
        print("Initatiating file transfer...")
        rommon_url = "tftp://{}/{}".format(regional_fs, rommon)
        rommon_transfer, rommon_transfer_output = generic.copy_remote_image(device, rommon_url, expect1="bytes copied", expect2="Signature Verified")
        transfer_output = "{}\n\n{}".format(ios_transfer_output, rommon_transfer_output)
        logbin_url = self.logbin(transfer_output, description="image transfer for {}".format(self.device))
        self.code_upload_log_url = logbin_url
        if ios_transfer and rommon_transfer:
            print('File Transfer Suceeded')
            self.code_upload_status = "success"
        else:
            print('File Transfer Failed')
            self.code_upload_status = "danger"
            exit()

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

        # Capture pre verification commands
        if self.verification_commands:
            pre_output = generic.capture_commands(connected, self.verification_commands)
            if pre_output:
                self.pre_verification_commands_status = "success"
                self.pre_verification_commands_url = self.logbin(pre_output, description="upgrade pre-verification commands for {}".format(self.device))
            else:
                self.status = "FAILED - COULD NOT GATHER VERIFICATION COMMANDS"
                exit(1)

        # Backup Running Config
        self.status = "BACKING UP RUNNING CONFIG"
        output = connected.show('show running-config')
        if output:
            self.backup_running_config_status = "success"
            logbin_url = self.logbin(output, description="backup running config for {}".format(self.device))
            self.backup_running_config_log_url = logbin_url
        else:
            self.status = "FAILED - COULD NOT BACKUP RUNNING CONFIG"
            exit()

        # Change bootvar
        self.status = "SETTING BOOT VARIABLE"
        result = generic.set_bootvar(connected, image=self.target_image)
        bootvar_result, bootvar_output = result
        if bootvar_output:
            logbin_url = self.logbin(bootvar_output, description="setting boot variable for {}".format(self.device))
            self.set_bootvar_status_log_url = logbin_url
            self.set_bootvar_status = "success"
        else:
            self.status = "FAILED - COULD NOT SET BOOT VARIABLE"
            exit()

        # Verify bootvar
        self.status = "VERIFYING BOOT VARIABLE"
        result = generic.verify_bootvar(connected, self.target_image)
        valid_bootvar, valid_bootvar_output = result

        if valid_bootvar:
            logbin_url = self.logbin(valid_bootvar_output,
                                     description="verify boot variable for {}".format(self.device))
            self.verify_bootvar_status_log_url = logbin_url
            self.set_bootvar_status = "success"
            self.verify_bootvar_status = "success"
            time.sleep(10)
        else:
            self.status = "FAILED - COULD NOT VERIFY BOOT VARIABLE"
            exit()

        # Upgrade ROMMON
        self.status = "UPGRADING ROMMON"
        result = generic.upgrade_rommon(connected, rommon=self.target_rommon)
        rommon_result, rommon_output = result
        if rommon_output:
            logbin_url = self.logbin(rommon_output, description="upgrading rommon for {}".format(self.device))
            self.set_rommon_log_url = logbin_url
            self.set_rommon_status = "success"
        else:
            self.status = "FAILED - COULD NOT UPGRADE ROMMON"
            exit()

        # Reload
        self.status = "RELOADING"
        reload_output = generic.reload_device(connected,
                                              command=self.reload_command)
        logbin_url = self.logbin("{}".format(reload_output), description="reload output for {}".format(self.device))
        self.reload_status_log_url = logbin_url

        reloaded = True
        self.status = "RELOAD IN PROGRESS"
        # in case this gets called to soon e.g a device responds to ping
        # for a bit we'll sleep for `delay`
        print ("Waiting 7 minutes for device to reload")
        time.sleep(420)

        # wait for device to come line
        self.status = "VERIFYING DEVICE IS REACHABLE"
        wait_for_reboot = generic.wait_for_reboot(self.device)
        excluded_lines = ['Chassis', 'ok']
        healthy_module = 1
        healthy_module_delay = 0

        online = NTC(host=self.device,
                     username=self.username,
                     password=self.password,
                     device_type="cisco_ios_ssh")

        if reloaded and wait_for_reboot:
            # Repeat if one more more module is not in an 'ok' state
            while healthy_module != 0:
                # Determine how many modules are not in an 'ok' state
                platform_output = online.show('show platform | i ASR')
                lines = platform_output.rstrip().split('\n')
                lines = [l for l in lines if not any(s in l for s in excluded_lines)]
                healthy_module = len(lines)

                # Wait for 20 more seconds if one or more modules not in 'ok' state
                self.status = "BACK ONLINE, VERIFYING LINECARDS"
                print ("{} linecards are not in a 'ok' state.".format(healthy_module))
                time.sleep(20)
                healthy_module_delay += 1
                if healthy_module_delay == 6:
                    self.status = "FAILED - COULD NOT VERIFY LINECARD STATE"
                    exit()
            self.status = "BACK ONLINE, LINECARDS ARE IN 'OK' STATE"
            self.reload_status = "success"
        else:
            self.status = "FAILED - DEVICE NOT REACHABLE"
            exit()

        # Verify upgrade
        self.status = "VERIFYING UPGRADE"

        # here we are formatting the output that will be pushed to the logbin
        # so that it will be able to be viewed as an iframe
        image_output = '\nDetecting image name with `sho ver | inc image`\n'
        image_output += online.show('sho ver | inc image')
        image_output += '\nDetecting uptime with `show ver | inc ptime`\n'
        image_output += online.show('sho ver | inc ptime')

        # some platforms may have limitation in how many chars of the boot image display
        # so we'll do our part to shorten our image name
        match_pattern = self.target_image.split('.bin')[0]
        upgraded = match_pattern in image_output
        image_output += "\nChecking if {} is present in the output...".format(match_pattern)
        if upgraded:
            print("\nFound {} in command output".format(self.target_image))
            image_output += "it is"
            image_upgraded = True

        else:
            print("\nCould not find {} in command output\n".format(self.target_image))
            image_output += "rur roh"
            image_upgraded = False


        rommon_output = online.show('show platform | be Firmware')
        image_output += '\nDetecting ROMMON with `show platform | be Firmware`\n'
        image_output += rommon_output

        # Determine slots requiring ROMMON upgrade, excluding 16.3(2r)
        excluded_lines = ['Slot', 'CPLD', '16.3(2r)', '-----']
        lines = rommon_output.rstrip().split('\n')
        lines = [l for l in lines if not any(s in l for s in excluded_lines)]
        expected_rommon_upgrades = len(lines)

        if expected_rommon_upgrades == 0:
            print("\n16.3(2r) ROMMON seen for all modules")
            rommon_upgraded = True
        else:
            print ("\n16.3(2r) ROMMON not seen for one or more modules\n")
            rommon_upgraded = False

        if image_upgraded == False or rommon_upgraded == False:
            self.verify_upgrade = "danger"
        else:
            self.verify_upgrade = "success"

        # ship the log file and move on
        print image_output
        logbin_url = self.logbin(image_output, description="verify upgrade for {}".format(self.device))
        self.verify_upgrade_log_url = logbin_url

        custom_1 = self.custom_verification_1()
        custom_2 = self.custom_verification_2()

        # Capture post verification commands
        if self.verification_commands:
            post_output = generic.capture_commands(online, self.verification_commands)
            if post_output:
                self.post_verification_commands_status = "success"
                descr = "post upgrade verification commands for {}".format(self.device)
                self.post_verification_commands_url = self.logbin(post_output,
                                                                  description=descr)
            else:
                self.status = "FAILED - COULD NOT GATHER POST VERIFICATION COMMANDS"
                exit(1)

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