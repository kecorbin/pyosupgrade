from pyosupgrade.upgrade import copy_remote_image, identify_sup, verify_sup_redundancy, copy_image_to_slave
from pyosupgrade.display import success, fail, info
import sys
import yaml
import getpass
from pyntc import ntc_device as Device

def stage_code(ip, user, pass):

    with open('regions.yaml', 'r') as regions:
        regions = yaml.safe_load(regions)

    with open('images.yaml', 'r') as images:
        images = yaml.safe_load(images)

    try:
        device = Device(host=ip, username=user, password=pw, device_type="cisco_ios_ssh")
        hostname = device.facts['hostname']
    except:
        fail("Unable to connect to device")
    try:
        regional_fs = regions[hostname[:2].upper()]['regional_fs']
        info("Using server {}".format(regional_fs))
    except KeyError:
        fail("Unable to determine regional server")

    sup_type = identify_sup(device)
    info("Supervisor identified as {}".format(sup_type))
    image = images[sup_type]['filename']
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

if __name__ == "__main__":
    ip = raw_input('Switch IP address')
    user = raw_input('Username: ')
    pw = getpass.getpass('Password:')
    stage_code(ip, user, pw)
