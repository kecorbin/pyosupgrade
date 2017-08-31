import os
import sys
import datetime
import time
import hashlib
import threading
from progress.bar import ChargingBar
from display import success, info, fail
from pyntc import ntc_device as NTC
from netmiko.ssh_exception import NetMikoTimeoutException, NetMikoAuthenticationException
from subprocess import check_call
import socket
import logging
from platform import system as system_name # Returns the system/OS name
from os import system as system_call       # Execute a shell command
import errno
import sys

def mkdir_p(path):
    """http://stackoverflow.com/a/600612/190597 (tzot)"""
    try:
        os.makedirs(path, exist_ok=True)  # Python>3.2
    except TypeError:
        try:
            os.makedirs(path)
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else: raise

class MakeFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=0):
        mkdir_p(os.path.dirname(filename))
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)

class Logger(object):

    def __init__(self, hostname="defaut"):
        logger = logging.getLogger(hostname)
        logger.setLevel(logging.DEBUG)
        fh = MakeFileHandler("logs/{0}/{0}-upgrade.log".format(hostname))
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                  '%(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)

        #self.terminal = sys.stdout
        self.log = logger

    def write(self, message):
        #self.terminal.write(message)
        self.log.info(message)

class DeviceUpgrader(threading.Thread):
    """
    Helper class to run upgrade async
    """

    def __init__(self, ip, username, password, image):
        """
        :param tunnel:
        :return:
        """
        super(DeviceUpgrader, self).__init__()
        self.daemon = True
        self.ip = ip
        self.username = username
        self.password = password
        self.image = image

    def run(self):
        print('starting upgrade async')
        switch_upgrade(self.ip, self.username, self.password, self.image)
        print('upgrade finished')


class CodeUploader(threading.Thread):

    def __init__(self, ip, username, password, mirrors, images):
        """
        :param tunnel:
        :return:
        """
        super(CodeUploader, self).__init__()
        self.daemon = True
        self.ip = ip
        self.username = username
        self.password = password
        self.mirrors = mirrors
        self.images = images


    def run(self):
        print('starting code upload to {} asynchronously'.format(self.ip))
        try:
            device = NTC(host=self.ip, username=self.username, password=self.password, device_type="cisco_ios_ssh")
            hostname = device.facts['hostname']
        except:
           fail("Unable to connect to device")
        try:
            regional_fs = self.mirrors[hostname[:2].upper()]['regional_fs']
            info("Using server {}".format(regional_fs))
        except KeyError:
            fail("Unable to determine regional server")

        sup_type = identify_sup(device)
        info("Supervisor identified as {}".format(sup_type))
        image = self.images[sup_type]['filename']
        info("Using image {}".format(image))

        info("Initatiating file transfer...")
        url = "tftp://{}/{}".format(regional_fs, image)
        if copy_remote_image(device, url):
            success('File Transfer Suceeded')
        else:
            fail('File Transfer Failed')

        if verify_sup_redundancy(device):
            info('Redundant Supervisors detected\n')

            if copy_image_to_slave(device, image):
                success('File Transfer Suceeded')

        print('code upload finished')


def backup_running_config(device, filename=None):
    """
    backup running configuration to local file named <hostname>.cfg
    optionally, a filename can be specified
    """
    facts = device.facts
    if filename is None:
        fname = '{}.cfg'.format(facts['hostname'])
    print("Backing up device configuration as {}".format(fname))
    device.backup_running_config(fname)

def change_tcp_window(device, size=65535):
    print "Optimizing TCP window size for transfer....."
    current = device.show('sho run all | inc ip tcp window-size')
    device.open()
    device.config('ip tcp window-size {}'.format(size))

def verify_sup_redundancy(device):
    """
    verifies that supervisors are operating in SSO mode
    """
    device.open()
    output = device.show('show module')
    return "Standby hot" in output

def identify_sup(device):
    """
    get's supervisor information from a 4500 switch
    """
    device.open()
    output = device.show('show module')
    if "WS-X45-SUP7-E" in output:
        return "WS-X45-SUP7-E"
    elif "WS-X45-SUP8-E" in output:
        return "WS-X45-SUP8-E"
    else:
        return "UNKNOWN"


def copy_remote_image(device, url, file_system='bootflash:'):
    device.open()
    image = url.split('/')[-1]
    print "Setting file prompt to quiet"
    device.native.send_config_set(["file prompt quiet"])
    print "Copying image from {} to {}{}".format(url, file_system, image)
    command = 'copy {} {}{}'.format(url, file_system, image)
    output = device.native.send_command_expect(command, delay_factor=100)
    print output
    try:
        if 'bytes copied' in output:
            stats = [l for l in output.split('\n') if 'bytes copied' in l][0]
            print stats
            print "Restoring file prompt to alert"
            device.native.send_config_set(["file prompt alert"])
            return True
        else:
            print "Restoring file prompt to alert"
            device.native.send_config_set(["file prompt alert"])
            return False
    except IOError:
        print "Restoring file prompt to alert"
        device.native.send_config_set(["file prompt alert"])
        return False

def copy_image(device, image, verify=True, file_system='bootflash:'):
    """
    Copies an IOS image to remote device with MD5 verification
    """
    print "Calulating md5 hash of local file...."
    with open(image) as fh:
        contents = fh.read()
        md5 = hashlib.md5(contents).hexdigest()
        print md5
    print "Copying image to {}{}".format(file_system, image)
    device.open()
    device.file_copy(image, file_system=file_system)
    if verify:
        verify_image(device, '{}{}'.format(file_system,image), md5hash=md5)

def copy_image_to_slave(device, image, source_fs='bootflash:', dst_fs='slavebootflash:'):
    print "Synchronizing image to secondary supervisor"
    try:
        device.open()
        device.native.send_config_set(["file prompt quiet"])
        command = 'copy {}{} {}{}'.format(source_fs, image,
                                          dst_fs, image)
        output = device.native.send_command_expect(command, delay_factor=100)
        print output
        return True
    except:
        return False

def verify_image(device, image, md5hash=None):
    """
    Perform md5 verfication of *image* on device using a provided md5hash
    """
    print "Calulating md5 hash of remote file...."
    device.open()
    output = device.native.send_command_expect('verify /md5 {}'.format(image),
                                              delay_factor=5)
    output_md5_lines = [l for l in output.split('\n') if ('MD5' or 'md5') in l]
    match = md5hash.lower() in output

    # if output_md5_lines:
    #     ios_hash = output_md5_lines[0].split(':')[1].strip()
    #     print ios_hash.lower()
    #     #match = ios_hash.lower() == md5hash.lower()
    #     print "Comparing MD5.....",
    if match:
        print output
    else:
        print "Failed to verify image"
    return match

def ping(host):
    """
    https://stackoverflow.com/questions/2953462/pinging-servers-in-python

    Returns True if host (str) responds to a ping request.
    Remember that some hosts may not respond to a ping
    request even if the host name is valid.
    """
    # Ping parameters as function of OS
    parameters = "-n 1" if system_name().lower()=="windows" else "-c 1"
    # Pinging
    return system_call("ping " + parameters + " " + host + " > /dev/null") == 0

def set_bootvar(device, image, file_system="bootflash:"):
    """
    Removes existing boot statements on *device* and adds one for *image*
    also saves the configuration

    :param device: ntc_device object
    :param image: str image filename
    :returns: None
    """
    device.open()
    print ("Updating boot statement")
    existing_bootstmts = device.show('show running | inc boot system').split('\n')
    for bootstmt in existing_bootstmts:
        # double check to make sure we have a boot statement
        if bootstmt.startswith('boot system'):
            print "removing boot statement: {}".format(bootstmt)
            device.config("no {}".format(bootstmt))
    device.config("boot system {}{}".format(file_system, image))
    device.save()

def verify_fpga(device, revision_reg="0x20160929"):
    """
    Verifies FPGA upgrade for 4748-UPOE line cards
    """
    device.open()
    mods = device.show('show mod | inc 4748-UPOE').split('\n')
    cmd = 'show platform chassis | inc {}'
    upgrades = device.show(cmd.format(revision_reg)).split('\n')

    print "Detected {} 4748 modules".format(len(mods))
    print "{} upgrades verified".format(len(upgrades))
    return len(mods) == len(upgrades)

def reload_device(device, command='reload'):
    try:
        print("Reloading device with cmmand {}".format(command))
        cmds = [command, '\n']
        output = device.show_list(cmds)
        # device may not kick us out immediately, but it should
        time.sleep(30)
    except socket.error:
        # okay to move on if we get booted from the device
        pass

def current_system_image_check(device, image):
    """
    Verify a software image is installed and running
    """
    return image in device.show('sho ver | inc System image')

def verify_bootvar(device, image, **kwargs):
    """
    Validates that a device has the desired bootvar and configuration register
    """
    desired_confreg = kwargs.get("config_register", "0x2102")
    bootvar_pattern = kwargs.get("bootvar_pattern", "BOOT variable")
    confreg_pattern = kwargs.get("confreg_pattern", "Configuration register")
    output = device.show('show bootvar')
    lines = output.split('\n')
    bootvars = [l for l in lines if bootvar_pattern in l]
    print ("Bootvar is set to {}".format(bootvars))
    confregs = [l for l in lines if "Configuration register" in l]
    print confregs[0]
    valid_bootvars = map(lambda x:image in x, bootvars)
    valid_confregs = map(lambda x:desired_confreg in x, confregs)
    valid = all(valid_bootvars) and all(valid_confregs)
    if valid:
        print("Verfied bootup configuration")
        return True

def wait_for_reboot(ip, repeat=500):
    """
    Pings a device until it responds
    """
    try:
        bar = ChargingBar('Waiting for device to reboot', max=20)
        for i in range(repeat):
            bar.next()
            t = ping(ip)
            if t:
                bar.finish()
                return True
        return False
    except KeyboardInterrupt:
        sys.exit(1)

# Main routing for staging Code
def stage_code(device, image_url, device_type='cisco_ios_ssh'):


    if copy_remote_image(device, url):
        success('File Transfer Suceeded')
    else:
        fail('File Transfer Failed')

    if verify_sup_redundancy(device):
        info('Redundant Supervisors detected\n')

        if copy_image_to_slave(device, image):
            success('File Transfer Suceeded')

# Main routine for upgrades
def switch_upgrade(ip, user, passwd, image, device_type='cisco_ios_ssh'):
    reloaded = False
    try:
        connected = NTC(host=ip, username=user, password=passwd, device_type=device_type)

    except NetMikoTimeoutException:
        connected = None

    if connected:
        hostname = connected.facts['hostname']
        sys.stdout = Logger(hostname)
        start = datetime.datetime.now()
        print "Upgrade requested by {} at {}".format(user, start)
        # display_facts(connected)
        backup_running_config(connected)
        change_tcp_window(connected)
        copy_image(connected, image)
        print "Setting boot variable..."
        set_bootvar(connected, image=image)


        print "Verifying bootvar and config-register... "
        if verify_bootvar(connected, image, config_register="0x2102"):
            print("Bootup configuration is valid")
            time.sleep(10)
            reload_device(connected, command='reload')
            reloaded = True
        else:
            sys.stderr.write('Could not verify image')
    else:
        print("Failed to connect to device")

    if reloaded and wait_for_reboot(ip):
        # linecards may still be booting/upgrading
        print("Device is online, sleeping for 5 minutes to allow for boot to complete")
        time.sleep(300)

    print "Verifying upgrade....",
    online = NTC(host=ip, username=user, password=passwd, device_type=device_type)
    if online and current_system_image_check(online, image) and verify_fpga(online):
        print("Upgrade was successful")
    else:
        print("Unable to verify image load was successful, please check manually")
