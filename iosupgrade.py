import re
import sys
from nornir import InitNornir
from nornir.plugins.tasks.networking import netmiko_file_transfer, netmiko_send_command, netmiko_send_config
from nornir_utilities import nornir_set_creds, std_print
from ciscoconfparse import CiscoConfParse
from nornir.plugins.functions.text import print_result
from nornir.core.filter import F
import ipdb

#Search running configuration and return image file and directory if they exist.
def getcurrentimage(host):
    file = 'configs/'+host+'-running.cfg'
    parse = CiscoConfParse(file, syntax='ios')
    bootstatement = parse.find_objects(r'boot system')
    if not bootstatement:
        return {'directory': 'flash', 'backup_image': 'none'}
    #ipdb.set_trace()
    img_dir = bootstatement[0].re_match(r'(\S+)\:\S+', default='flash')
    current_imgfile = bootstatement[0].re_match(r'\:(\S+)\.bin', default='none')
    current_imgfile = current_imgfile + '.bin'
    #ipdb.set_trace()
    return {'directory': img_dir, 'backup_image': current_imgfile}

def set_boot_image(task):
    print("\nStarting process set boot image on", task.host.name)
    primary_img = task.host.get('img')
    #backup_img = task.host.get('backup_img')
    bootvars = getcurrentimage(task.host.name)
    backup_img = bootvars['backup_image']
    directory = bootvars['directory']
    #ipdb.set_trace()
    if backup_img == 'none':
        print("unable to determine current image bootvar on", task.host.name)
        print("proceeding without backup image")
        commands = f"""
        default boot system
        boot system {directory} {primary_img}
        """

    # Validate that both new and existing image are on device
    #if backup_img == 'none':   #horrible logic... if we don't have backup image, check primary twice instead of duplicating function
        #backup_img = primary_img
    for img in (primary_img, backup_img):
        if img == 'none':
            continue
        result = task.run(
            task=netmiko_send_command,
            command_string=f"dir flash:/{img}"
        )
        output = result[0].result
        # Ignore the first line, since it always contains the searched for filename
        output = re.split(r"Directory of.*", output, flags=re.M)[1]
        if img not in output:
            print("Image not found on Device -", img)
            return False

    if backup_img != 'none':
        commands = f"""
        default boot system
        boot system {directory} {primary_img}
        boot system {directory} {backup_img}
        """

    #ipdb.set_trace()
    command_list = commands.strip().splitlines()
    #ipdb.set_trace()
    result = task.run(
        task=netmiko_send_config,
        config_commands=command_list
    )
    print("Completed process set boot image on", task.host.name)
    return True

def continue_func(msg="Do you want to continue (y/n)? "):
    response = input(msg).lower()
    if 'y' in response:
        return True
    else:
        sys.exit()

def main():
    nr = InitNornir(config_file="config.yaml")
    nornir_set_creds(nr)

    #filter to one device
    #target_routers = nr.filter(hostname='10.83.46.1')
    target_routers = nr.filter(F(groups__contains="iosv"))
    print('Running iosupgrade.py against the following Nornir inventory hosts:', target_routers.inventory.hosts.keys())


    aggr_result = target_routers.run(task=set_boot_image, num_workers=20)
    #ipdb.set_trace()

    for hostname, val in aggr_result.items():
        if val[0].result is False:
            sys.exit("Setting the boot variable failed for device:", hostname)

    #Post validation of boot statements
    result = target_routers.run(
        task=netmiko_send_command,
        command_string="show run | section boot",
        num_workers = 20
    )
    print("Review currently configured boot statements")
    std_print(result)
    #ipdb.set_trace()
    #After reviewing boot statements - ask to continue
    continue_func()

    # Save the configuration
    result = target_routers.run(
        task=netmiko_send_command,
        command_string= "write mem"
    )
    std_print(result)

    # Reload
    continue_func(msg="Do you want to reload the device (y/n)? ")
    result = target_routers.run(
        task=netmiko_send_command,
        use_timing=True,
        command_string="reload"
    )
    ipdb.set_trace()
    # Handle reload confirmation if required
    for device_name, multi_result in result.items():
        if 'confirm' in multi_result[0].result:
            result = target_routers.run(
                task=netmiko_send_command,
                use_timing=True,
                command_string="y"
            )

    print("Devices reloaded")
    ipdb.set_trace()
if __name__ == "__main__":
    main()
