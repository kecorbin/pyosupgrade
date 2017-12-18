import time
import socket
from platform import system as system_name
from os import system as system_call
import sys
import re


def capture_commands(device, commands):
    """
    Executes a list of commands on a device

    This adds some context information (ip/command) as well as basic XML tags used for sorting results later

    :param device:  pyntc
    :param commands: list of commands to execute on each device
    :return: string output from commands w/ basic XML tags for sorting
    """
    device.open()
    output = "<snapshot>\n"
    for command in commands:
        output += '<command cmd="{}">\n'.format(command.strip())
        output += "\n{}\n".format(command)
        output += "{}\n".format('-' * 80)
        output += device.native.send_command(command)
        output += "\n</command>\n"
    output += "\n</snapshot>\n"
    return output


def verify_sup_redundancy(device):
    """
    Returns True if supervisors are in SSO mode
    :param device: ntc device
    :return: bool
    """
    device.open()
    output = device.show('show module')
    return "Standby hot" in output, output


def copy_remote_image(device, url, file_system="bootflash:", expect1="bytes copied", expect2="signature successfully verified"):
    """

    :param device: pyntc device
    :param url: source of image
    :param file_system: destination file system
    :return: bool, str tuple containing whether the operation was successful and any output
    """
    device.open()
    image = url.split('/')[-1]
    # checking where the image already exists.  should be rare
    ls = device.native.send_command('dir {}'.format(file_system))
    if image in ls:
        msg = "Image already present verifying hash\n"
        msg += "-----------------------\n"
        valid, verify_output = verify_image(device, "{}{}".format(file_system, image))
        msg += verify_output
        if valid:
            return True, msg
        else:
            return False, msg
    else:
        # proceed with upgrade
        print "Setting file prompt to quiet"
        # Disables's confirmation for dest filename, and automatically verifies MD5
        device.native.send_config_set(["file prompt quiet", "file verify auto"])
        print "Copying image from {} to {}{}".format(url, file_system, image)
        command = 'copy {} {}{}'.format(url, file_system, image)
        output = device.native.send_command_expect(command, delay_factor=30)
        # look for all the following keywords in the output
        expected_patterns = [expect1, expect2]
        try:
            if all(x in output for x in expected_patterns):
                print "Image copied and successfully verified"
                return True, output
            else:
                return False, output
        except IOError:
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
    device.open()

    # checking where the image already exists.  should be rare
    ls = device.native.send_command('dir {}'.format(dst_fs))
    if image in ls:
        msg = "Image already present verifying hash\n"
        msg += "-----------------------\n"
        valid, verify_output = verify_image(device, "{}{}".format(dst_fs, image))
        msg += verify_output
        if valid:
            return True, msg
        else:
            return False, msg
    else:
        # image is not present, proceed with copy
        device.native.send_config_set(["file prompt quiet", "file verify auto"])
        command = 'copy {}{} {}{}'.format(source_fs, image,
                                          dst_fs, image)
        output = device.native.send_command_expect(command, delay_factor=30)
        expected_patterns = ["bytes copied", "signature successfully verified"]
        # checks that all expected_patterns are present in the output
        if all(x in output for x in expected_patterns):
            return True, output
        else:
            return False, output



def verify_image(device, image):
    """
    Perform md5 verfication of *image* on device using a provided md5hash
    Returns True if md5 hash is valid

    :param device: ntc_device
    :param image: str image name including filesystem
    :param md5hash: str expected md5 hash
    :return: bool, str tuple of True if verification is successful, output of verification
    """
    print "Calulating md5 hash of remote file...."
    device.open()
    output = device.native.send_command_expect('verify {}'.format(image),
                                               delay_factor=10)
    if "signature successfully verified" in output:
        return True, output
    # common ASR1K pattern
    elif "verification successful" in output:
        return True, output
    else:
        return False, output

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
    conf_set = ['file prompt quiet']
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
        output += device.native.send_command_expect('copy running-config startup-config\n\n', delay_factor=5)
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
