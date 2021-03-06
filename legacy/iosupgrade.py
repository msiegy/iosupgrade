"""
    Update bootvars and perform IOS Upgrade.

    Tasks:
    1) Check if current image is defined in bootvars so we can set as backup.
    2) Validate that both new and existing/backup image are on device.
    3) Set boot vars so new image is primary image, previous is backup.
    4) Output new Boot Config and Prompt for user review before continuuing
    5) Write Mem (Confirm)
    6) Reload Router (Confirm)

"""


import re
import sys
from nornir import InitNornir
from nornir.plugins.tasks.networking import netmiko_file_transfer, netmiko_send_command, netmiko_send_config
from nornir_utilities import nornir_set_creds, std_print
from ciscoconfparse import CiscoConfParse
from nornir.plugins.functions.text import print_result
from nornir.core.filter import F
import ipdb

def prRed(skk): print("\033[91m {}\033[00m" .format(skk))
def prYellow(skk): print("\033[93m {}\033[00m" .format(skk))

#Search running configuration for bootstatement and return image file and directory if they exist.
def getcurrentimage(host):
    file = 'configs/pre/'+host+'-running.cfg'
    parse = CiscoConfParse(file, syntax='ios')
    bootstatement = parse.find_objects(r'boot system')
    if not bootstatement:
        return {'directory': 'flash', 'backup_image': 'none'}

    img_dir = bootstatement[0].re_match(r'(\S+)\:\S+', default='flash')
    current_imgfile = bootstatement[0].re_match(r'(\S+)\.bin', default='none')
    current_imgfile = current_imgfile + '.bin'

    return {'directory': img_dir, 'backup_image': current_imgfile}

"""
Check that both existing image and new image exist, if they do set them as boot vars.
at a minimum set the new image, if existing image cannot be determind.
this needs serious clean up... consider checking dir for older image and always setting it
as backup.
"""
def set_boot_image(task):
    primary_img = task.host.get('img')
    #backup_img = task.host.get('backup_img')
    bootvars = getcurrentimage(task.host.name)
    backup_img = bootvars['backup_image']
    directory = bootvars['directory']

    if 'none' in backup_img:
        #print("\nunable to determine current image bootvar on", task.host.name)
        #print("\nproceeding without backup image on", task.host.name)
        commands = f"""
        default boot system
        boot system {directory} {primary_img}
        """

    # Validate that both new and existing image are on device
    for img in (primary_img, backup_img):
        if 'none' in img:
            continue
        result = task.run(
            task=netmiko_send_command,
            command_string=f"dir flash:/{img}",
            enable=True,
            name="Confirm Image Exists on Flash"
        )
        output = result[0].result
        #import ipdb; ipdb.set_trace()
        # detect error/image not found
        if output.startswith("%Error"):
            #target_routers.data.failed_hosts.add(task.host.name)
            return False
        # Ignore the first line, since it always contains the searched for filename
        output = re.split(r"Directory of.*", output, flags=re.M)[1]
        if img not in output:
            #print("\nImage not found on Device -", img)
            return False

    if 'none' not in backup_img:
        commands = f"""
        default boot system
        boot system {directory} {primary_img}
        boot system {directory} {backup_img}
        """

    command_list = commands.strip().splitlines()

    result = task.run(
        task=netmiko_send_config,
        config_commands=command_list
    )
    return True

def continue_func(msg="Do you want to continue (y/n)? "):
    response = input(msg).lower()
    if 'y' in response:
        return True
    else:
        sys.exit()

def main():
    nr = InitNornir(config_file="config.yaml")
    #filter to one device
    #target_routers = nr.filter(hostname='10.83.46.1')
    target_routers = nr.filter(F(groups__contains="iosv"))
    print('Running iosupgrade.py against the following Nornir inventory hosts:', target_routers.inventory.hosts.keys())

    # Ask for credentials at runtime instead of storing.
    nornir_set_creds(nr)

    aggr_result = target_routers.run(task=set_boot_image, num_workers=20)
    print_result(aggr_result)

    #Check result for set_boot_image. True or False.
    for hostname, val in aggr_result.items():
        if val[0].result is False:
            #sys.exit("Setting the boot variable failed for device:", hostname)
            prRed("\n!!!There was an error with " + hostname + " so it will be removed from further processing\n")
            #Add device to failed inventory to prevent future processing in tasks... (poor design)
            target_routers.data.failed_hosts.add(hostname)
    #Post validation of boot statements
    result = target_routers.run(
        task=netmiko_send_command,
        command_string="show run | section boot",
        name="show run | section boot",
        num_workers=20
    )
    prYellow("\nReview the configured boot statements before proceeding with Write Mem\n")
    print_result(result)
    #After reviewing boot statements - ask to continue
    continue_func()

    # Save the configuration
    result = target_routers.run(
        task=netmiko_send_command,
        command_string= "write mem",
        name="Issue Write Mem",
    )
    print_result(result)

    # Reload
    continue_func(msg="Do you want to reload the device (y/n)? ")
    result = target_routers.run(
        task=netmiko_send_command,
        use_timing=True,
        command_string="reload",
        name="Issue Reload Command",
    )
    #import ipdb; ipdb.set_trace()
    # Handle reload confirmation if required
    for device_name, multi_result in result.items():
        if 'confirm' in multi_result[0].result:
            result = target_routers.run(
                task=netmiko_send_command,
                use_timing=True,
                command_string="y",
                name="Confirm Reload with Yes",
            )
    print_result(result)
    print("Devices reloaded")
    #ipdb.set_trace()
if __name__ == "__main__":
    main()
