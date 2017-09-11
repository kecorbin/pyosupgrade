import time
import socket
from platform import system as system_name
from os import system as system_call
import sys
import re


def verify_sup_redundancy(device):
    """
    Returns True if supervisors are in SSO mode
    :param device: ntc device
    :return: bool
    """
    device.open()
    output = device.show('show module')
    return "Standby hot" in output, output


def copy_remote_image(device, url, file_system="bootflash:"):
    device.open()
    image = url.split('/')[-1]
    print "Setting file prompt to quiet"
    device.native.send_config_set(["file prompt quiet"])
    print "Copying image from {} to {}{}".format(url, file_system, image)
    command = 'copy {} {}{}'.format(url, file_system, image)
    output = device.native.send_command_expect(command, delay_factor=30)
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


def copy_image_to_slave(device,
                        image,
                        source_fs='bootflash:',
                        dst_fs='slavebootflash:'):
    """
    synchronize an image to the standby supervisor
    :param device: ntc_device
    :param image: str image name
    :param source_fs: str source filesystem (default is bootflash:)
    :param dst_fs: str destination filesystem (default is slavebootflash:)
    :return: bool, str True if image is copied successfully, and any output
    """
    print "Synchronizing image to secondary supervisor"
    output = ""
    try:
        device.open()
        # eventually we should just keep this enabled
        device.native.send_config_set(["file prompt quiet"])
        command = 'copy {}{} {}{}'.format(source_fs, image,
                                          dst_fs, image)
        output = device.native.send_command_expect(command, delay_factor=30)
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
    output = device.native.send_command_expect('verify /md5 {}'.format(image),
                                               delay_factor=5)
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
    output += bootvar_output
    existing_bootstmts = bootvar_output.split('\n')
    print "existing bootstatements = {}".format(existing_bootstmts)
    conf_set = list()
    if len(existing_bootstmts) >= 1:

        for bootstmt in existing_bootstmts:
            # double check to make sure we have a boot statement
            if bootstmt.startswith('boot system'):
                print "removing boot statement: {}".format(bootstmt)
                conf_set.append("no {}".format(bootstmt))
    conf_set.append("boot system {}{}".format(file_system, image))
    output += device.native.send_config_set(conf_set)

    verify_bootvar_output = device.show('show running | inc boot system')
    if image in verify_bootvar_output:

        output += "show running | inc boot system\n"
        output += verify_bootvar_output + '\n'
        output += "copy running-config startup-config\n"
        output += device.show('copy running-config startup-config')
        # in case we get a [startup-config]
        output += device.show('\n')

        return True, output
    else:
        return False, output


def reload_device(device, command='reload'):
    try:
        print("Reloading device with command {}".format(command))
        cmds = [command, '\n']

        output = ""
        raw_output = device.show_list(cmds)

        if isinstance(raw_output, list):
            raw_output = "\n".join(raw_output)
        output += "\noutput from reload command is {}\n".format(raw_output)
        output += "-- dont worry we hit enter for you!"
        # device may not kick us out immediately, but it should
        time.sleep(30)
        return output
    except socket.error:
        # okay to move on if we get booted from the device
        pass


def verify_bootvar(device, image, **kwargs):
    """
    Validates that a device has the desired bootvar and configuration register

    :param device: ntc_device
    :param image: str image name expected
    :param kwargs:
    :return: (bool, str) whether verification was successful, and any output
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


def wait_for_reboot(ip, repeat=500, delay=60):
    """
    Pings a device until it responds

    :param ip: str ip address
    :param delay: int how long to wait before testing begins
    :param repeat: int maximum number of ping attempts before giving up
    :return: bool if device comes online
    """
    try:
        # in case this gets called to soon e.g a device responds to ping
        # for a bit we'll sleep for `delay`
        print "Waiting {} seconds for device to go down completely".format(delay)
        time.sleep(delay)
        # then start testing
        for i in range(repeat):
            if repeat % 60 == 0:
                print("Waiting {} more minutes for host to come online".format(delay / 60))
            ping_success = ping(ip)
            if ping_success:
                print ("Host is responding to pings again!")
                return True
        # after repeat number of pings we say it failed
        return False
    except KeyboardInterrupt:
        sys.exit(1)
