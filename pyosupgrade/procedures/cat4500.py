from ios import IOSUpgrade
from pyntc import ntc_device as NTC
import re

class Catalyst4500Upgrade(IOSUpgrade):

    check_sup_redundancy = True
    reload_command = "redundancy reload shelf"

    @property
    def steps(self):
        steps = [('Code Transfer', self.code_upload_status, self.code_upload_log_url),
                ('Verify Supervisor Redundancy', self.sup_redundancy_status, self.sup_redundancy_log_url),
                ('Synchronize Code to Standby Supervisor', self.copy_code_to_slave_status, self.copy_code_to_slave_log_url),
                ('Backup Running Config', self.backup_running_config_status, self.backup_running_config_log_url),
                ('Set Boot Variable', self.set_bootvar_status, self.set_bootvar_status_log_url),
                ('Verify Boot Variable', self.verify_bootvar_status, self.verify_bootvar_status_log_url),
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
            'show bootvar',
            'show redundancy',
            'show inventory',
            'show environment',
            'show module',
            'show run',
            'show cdp neighbors',
            'show int status err-disabled',
            'show ip arp',
            'show spanning-tree',
            'show mac address-table'
        ]
        return commands

    def register_custom_tasks(self):
        self.custom_verification_1_name = "Verify FPGA Upgrades"
        self.custom_verification_2_name = "Verify Supervisor TX Queues"

    def identify_platform(self):
        """
        get's supervisor information from a 4500 switch

        :param device: ntc device
        :return: str Supervisor PID
        """

        output = self._pyntc.show('show module')
        if "WS-X45-SUP7-E" in output:
            return "WS-X45-SUP7-E", output
        elif "WS-X45-SUP8-E" in output:
            return "WS-X45-SUP8-E", output
        else:
            return "UNKNOWN", output

    def _verify_fpga(self, device, revision_reg="0x20160929"):
        """
        Verifies FPGA upgrade for 4748-UPOE line cards

        :param device: ntc_device
        :param revision_reg: str expected revision register
        :return: (bool, str) whether verification was successful, and any output
        """
        device.open()
        # this particular case only applies to V03 or higher modules
        # find out how many are present in the system
        mods = device.show('sho inventory | inc Linecard|4748')
        regex = r"WS-X4748.+V0[3-9]"
        matches = re.findall(regex, mods)
        num_affected_mods = len(matches)

        # find out how many modules have the correct RevisionReg
        cmd = 'show platform chassis | inc {}'
        platform_output = device.show(cmd.format(revision_reg))
        upgrades = [l for l in platform_output.split("\n") if l != '']
        num_mods_upgraded = len(upgrades)

        # structure output
        msg = "Detected {} affected 4748 modules\n".format(num_affected_mods)
        msg += "{} modules upgraded\n".format(num_mods_upgraded)
        msg += mods + "\n"
        msg += platform_output

        if num_affected_mods == num_mods_upgraded:
            return True, msg
        else:
            return False, msg

    def _ensure_queues_are_enabled(self):
        output = ""
        try:
            device = NTC(host=self.device,
                         username=self.username,
                         password=self.password,
                         device_type="cisco_ios_ssh")

            hostname = device.facts['hostname']

        except Exception:
            self.status = "FAILED CONNECT"

        output = device.show('show module')

        output += "Idenfitied chassis as "

        chassis_type = device.show('sho mod | inc Chassis').strip().split(':')[1]
        output += chassis_type

        if '4507' in chassis_type:
            sup_ints = ['t3/1','t3/2','t4/1','t4/2']
        elif '4510' in chassis_type:
            sup_ints = ['t5/1','t5/2','t5/1','t5/2']
        else:
            sup_ints = []

        for int in sup_ints:
            output += "\n\nChecking Interface {}\n\n".format(int)
            output += "=" * 20 + "\n"
            int_output = device.show('show platform hardware interface {} tx-queue'.format(int))
            output += int_output
            if 'Disabled' in int_output:
                output += "Bouncing {}\n".format(int)
                shut_noshut = ['interface {}'.format(int),
                               'shutdown',
                               'no shutdown']
                bounce = device.native.send_config_set(shut_noshut)
                output += bounce

            else:
                output += "{} queues are okay".format(int)

        return True, output

    def custom_verification_1(self):
        print "verify fpga upgrades"
        self.custom_verification_1_name = "Verify 4748 FPGA upgrades"
        output = ""
        try:
            device = NTC(host=self.device,
                         username=self.username,
                         password=self.password,
                         device_type="cisco_ios_ssh")

            hostname = device.facts['hostname']

        except Exception:
            self.status = "FAILED CONNECT"

        print("Verify FPGA")
        self.status = "VERIFYING FPGA UPGRADE"
        fpga_status, fpga_output = self._verify_fpga(device)
        logbin_url = self.logbin(fpga_output, description="fpga upgrade verification for {}".format(self.device))
        self.custom_verification_1_status_log_url = logbin_url

        if fpga_status:
            self.custom_verification_1_status = "success"
            return True

        else:
            self.custom_verification_1_status = "danger"
            return False

    def custom_verification_2(self):
        self.custom_verification_2_name = "Verify Supervisor TX Queues"
        self.status = "verify tx queues"
        verified, output = self._ensure_queues_are_enabled()
        description="sup tx queue verification for {}".format(self.device)
        self.custom_verification_2_status_log_url = self.logbin(output, description=description)
        if verified:
            self.custom_verification_2_status = "success"
            return True
        else:
            self.custom_verification_2_status = "danger"
            return False