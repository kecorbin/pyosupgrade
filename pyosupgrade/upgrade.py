import time
import socket
from platform import system as system_name
from os import system as system_call
import sys


def verify_sup_redundancy(device):
    """
    Returns True if supervisors are in SSO mode
    :param device: ntc device
    :return: bool
    """
    device.open()
    output = device.show('show module')
    return "Standby hot" in output, output


def identify_sup(device):
    """
    get's supervisor information from a 4500 switch

    :param device: ntc device
    :return: str Supervisor PID
    """
    device.open()
    output = device.show('show module')
    if "WS-X45-SUP7-E" in output:
        return "WS-X45-SUP7-E", output
    elif "WS-X45-SUP8-E" in output:
        return "WS-X45-SUP8-E", output
    else:
        return "UNKNOWN", output


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
            return True, output
        else:
            print "Restoring file prompt to alert"
            device.native.send_config_set(["file prompt alert"])
            return False, output
    except IOError:
        print "Restoring file prompt to alert"
        device.native.send_config_set(["file prompt alert"])
        return False, output


def copy_image_to_slave(device, image, source_fs='bootflash:', dst_fs='slavebootflash:'):
    """
    synchronize an image to the standby supervisor
    :param device: ntc_device
    :param image: str image name
    :param source_fs: str source filesystem (default is bootflash:)
    :param dst_fs: str destination filesystem (default is slavebootflash:)
    :return: bool, str True if image is copied successfully, and any associated CLI output
    """
    print "Synchronizing image to secondary supervisor"
    output = ""
    try:
        device.open()
        device.native.send_config_set(["file prompt quiet"])
        command = 'copy {}{} {}{}'.format(source_fs, image,
                                          dst_fs, image)
        output = device.native.send_command_expect(command, delay_factor=100)
        return True, output
    except:
        return False, output


def verify_image(device, image, md5hash=None):
    """
    Perform md5 verfication of *image* on device using a provided md5hash
    Returns True if md5 hash is valid

    :param device: ntc_device
    :param image: str image name
    :param md5hash: str expected md5 hash
    :return: bool
    """
    print "Calulating md5 hash of remote file...."
    device.open()
    output = device.native.send_command_expect('verify /md5 {}'.format(image), delay_factor=5)
    match = md5hash.lower() in output

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

    :param host:
    :return: bool
    """
    # Ping parameters as function of OS
    parameters = "-n 1" if system_name().lower() == "windows" else "-c 1"
    # Pinging
    return system_call("ping " + parameters + " " + host + " > /dev/null") == 0


def set_bootvar(device, image, file_system="bootflash:"):
    """
    Removes existing boot statements on *device* and adds one for *image*
    also saves the configuration

    :param device: ntc_device object
    :param image: str image filename
    :param file_system: str filesystem name, defaults to 'bootflash:'
    :returns: None
    """
    device.open()
    print ("Updating boot statement")
    output = ""
    bootvar_output = device.show('show running | inc boot system')
    existing_bootstmts = bootvar_output.split('\n')
    print "existing bootstatements = {}".format(existing_bootstmts)
    if len(existing_bootstmts) >= 1:

        for bootstmt in existing_bootstmts:
            # double check to make sure we have a boot statement
            if bootstmt.startswith('boot system'):
                print "removing boot statement: {}".format(bootstmt)
                device.config("no {}".format(bootstmt))
    device.config("boot system {}{}".format(file_system, image))

    verify_bootvar_output = device.show('show running | inc boot system')
    if image in verify_bootvar_output:

        output += "show running | inc boot system\n" + verify_bootvar_output + '\n'
        output += "copy running-config startup-config\n"
        output += device.show('copy running-config startup-config')
        return True, output
    else:
        return False, output


def reload_device(device, command='reload'):
    try:
        print("Reloading device with cmmand {}".format(command))
        cmds = [command, '\n']
        output = device.show_list(cmds)
        if isinstance(output, list):
            output = "\n".join(output)
        print "output from reload command is {}".format(output)
        # device may not kick us out immediately, but it should
        time.sleep(30)
        return output
    except socket.error:
        # okay to move on if we get booted from the device
        pass


def verify_fpga(device, revision_reg="0x20160929"):
    """
    Verifies FPGA upgrade for 4748-UPOE line cards

    :param device: ntc_device
    :param revision_reg: str expected revision register
    :return: (bool, str) whether the verification was successful, and any associated output
    """
    device.open()
    mods = device.show('show mod | inc 4748-UPOE').split('\n')
    cmd = 'show platform chassis | inc {}'
    upgrades = device.show(cmd.format(revision_reg)).split('\n')

    print "Detected {} 4748 modules".format(len(mods))
    print "{} upgrades verified".format(len(upgrades))
    if len(mods) == len(upgrades):
        upgrades = "\n".join(upgrades)
        return True, upgrades
    else:
        return False, upgrades


def verify_bootvar(device, image, **kwargs):
    """
    Validates that a device has the desired bootvar and configuration register

    :param device: ntc_device
    :param image: str image name expected
    :param kwargs:
    :return: (bool, str) whether the verification was successful, and any associated output
    """
    desired_confreg = kwargs.get("config_register", "0x2102")
    bootvar_pattern = kwargs.get("bootvar_pattern", "BOOT variable")
    output = device.show('show bootvar')
    lines = output.split('\n')
    bootvars = [l for l in lines if bootvar_pattern in l]
    print ("Bootvar is set to {}".format(bootvars))
    confregs = [l for l in lines if "Configuration register" in l]
    print confregs[0]
    valid_bootvars = map(lambda x: image in x, bootvars)
    valid_confregs = map(lambda x: desired_confreg in x, confregs)
    valid = all(valid_bootvars) and all(valid_confregs)
    if valid:
        print("Verfied bootup configuration")
        return True, output


def wait_for_reboot(ip, repeat=500):
    """
    Pings a device until it responds

    :param ip: str ip address
    :param repeat: int maximum number of ping attempts before giving up
    :return: bool if device comes online
    """
    try:
        for i in range(repeat):
            t = ping(ip)
            if t:
                return True
        return False
    except KeyboardInterrupt:
        sys.exit(1)
