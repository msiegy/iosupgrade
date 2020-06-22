import argparse
import os
import logging
import pathlib
import json
import re
import sys
from nornir import InitNornir
from nornir.plugins.tasks import networking
from nornir.plugins.tasks.networking import napalm_get, netmiko_file_transfer, netmiko_send_command, netmiko_send_config
from nornir.plugins.functions.text import print_result
from nornir_utilities import nornir_set_creds, std_print
from nornir.core.filter import F
from ciscoconfparse import CiscoConfParse
import ipdb

parser = argparse.ArgumentParser()
parser.add_argument("Action", choices=["prevalidate", "stage", "upgrade", "postvalidate"])
argroup = parser.add_mutually_exclusive_group()
argroup.add_argument('--group', help='set device targets using group filter', required=False)
argroup.add_argument('--host', help='set device targets using hostname or IP', required=False)
args = parser.parse_args()

def prRed(skk): print("\033[91m {}\033[00m" .format(skk))
def prYellow(skk): print("\033[93m {}\033[00m" .format(skk))
def prGreen(skk): print("\033[92m {}\033[00m" .format(skk))
def prCyan(skk): print("\033[96m {}\033[00m" .format(skk))

def validate_storage(task):
    result = task.run(
        task=netmiko_send_command,
        command_string="dir",
        enable=True
    )
    output = result[0].result

    #regex to find space available
    m = re.search(r'^(\d+) bytes total \((\d+) bytes free', output, re.M)
    totalbytes = int(m.group(1))
    availablebytes = int(m.group(2))
    #check planned imaged size against space available
    file_name = task.host.get('img')
    #retrieve file size in bytes
    #insert try/catch for if file exists - if file !exist exit with error
    file_size = os.stat(file_name).st_size

    if file_size >= availablebytes:
        return False
    elif file_size < availablebytes:
        return True

def collect_configs(task):
    config_result = task.run(task=napalm_get, getters=['config'])
    config = config_result[0].result['config']['running']
    store_config(task.host.name, config)

def store_config(hostname, config):
    filename = f"{hostname}-running.cfg"
    with open(os.path.join(preconfig_dir, filename), "w") as f:
        f.write(config)

def store_output(hostname, entry_dir, content, filename):
    filename = f"{filename}.txt"
    with open(os.path.join(entry_dir, filename), "w") as f:
        f.write(str(content))

def collect_getters(task):
    entry_dir = prefacts_dir + task.host.name
    pathlib.Path(entry_dir).mkdir(exist_ok=True)

    facts_result = task.run(task=napalm_get, getters=['facts', 'environment', 'lldp_neighbors', 'interfaces', 'interfaces_ip'])

    for entry in facts_result.result.keys():
        for getter in facts_result:
            filename = entry
            #content = getter.result[entry]
            content = json.dumps(getter.result[entry], indent=2)

            store_output(task.host.name, entry_dir, content, filename)


#use netmiko_file_transfer function within nornir. Returns Bool for File exists && valid MD5
def os_staging(task):
    file_name = task.host.get('img')
    result = task.run(
        task=netmiko_file_transfer,
        source_file=file_name,
        dest_file=file_name,
        direction='put'
    )
    return result

#Search running configuration for bootstatement and return image file and directory if they exist.
def getcurrentimage(host):
    file = preconfig_dir+host+'-running.cfg'
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
            #nr.data.failed_hosts.add(task.host.name)
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


"""
    Prevalidate storage requirements and store baselines for running config and
    operational states prior to OS Staging and Upgrade

    Tasks:
    1) Validate sufficient disk space based on file defined in groups.yaml
    2) Collect and store running configurations to local machine.
    3) Collect and store napalm getters to local machine.
"""
def preval():
    print('Running prevalidation against the following Nornir inventory hosts:', nr.inventory.hosts.keys())
    # Ask for credentials at runtime instead of storing.
    nornir_set_creds(nr)

    #Connect to devices to check if there is sufficient disk space.
    storage_result = nr.run(task=validate_storage, name='Validate Storage Requirements')
    print_result(storage_result) #potentially print only True/False Result, logfile rest of output
    #Summarize Results of Storage validation
    print("vvv Storage Results Summary vvv")
    for host in storage_result:
        if storage_result[host][0].result == True:
            print("Success - Sufficient storage available on", host)
        elif storage_result[host][0].result == False:
            print("Error - There is not enough space to transfer the image on", host)
        else:
            print("Error - An Error occured with", host)
    print("^^^ Storage Results Summary ^^^")
    #Connect to devices and store their running configurations to local folders.

    print("\nCollecting running configurations and operational state from devices")
    result = nr.run(task=collect_configs)

    #Connect to devices and collect napalm getters, store to local folders.
    result = nr.run(task=collect_getters)

    print("Running configurations and operational state have been saved to local machine")
    #ipdb.set_trace()


"""
    Transfer/Stage IOS image for router upgrade and validate MD5. Bootvars not changed.

    Tasks:
    1) Transfer image defined in groups.yaml from client to router using netmiko
    file transfer. Idempotent transfer.
    2) Check File exists and MD5 Hash on completion. if file exists valueerror.

    Requires user with privelge level 15 (without enable) and 'ip scp server enable'
"""

def stage_firmware():
    print('Staging firmware against the following Nornir inventory hosts:', nr.inventory.hosts.keys())
    nornir_set_creds(nr)
    print("Starting Image Transfer")
    result = nr.run(task=os_staging)
    print_result(result)
    #ipdb.set_trace()


def upgrade_ios():
    print('Running iosupgrade.py against the following Nornir inventory hosts:', nr.inventory.hosts.keys())

    # Ask for credentials at runtime instead of storing.
    nornir_set_creds(nr)

    aggr_result = nr.run(task=set_boot_image, num_workers=20)
    print_result(aggr_result)

    #Check result for set_boot_image. True or False.
    for hostname, val in aggr_result.items():
        if val[0].result is False:
            #sys.exit("Setting the boot variable failed for device:", hostname)
            prRed("\n!!!There was an error with " + hostname + " so it will be removed from further processing\n")
            #Add device to failed inventory to prevent future processing in tasks... (poor design)
            nr.data.failed_hosts.add(hostname)
    #Post validation of boot statements
    result = nr.run(
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
    result = nr.run(
        task=netmiko_send_command,
        command_string= "write mem",
        name="Issue Write Mem",
    )
    print_result(result)

    # Reload
    continue_func(msg="Do you want to reload the device (y/n)? ")
    result = nr.run(
        task=netmiko_send_command,
        use_timing=True,
        command_string="reload",
        name="Issue Reload Command",
    )
    #import ipdb; ipdb.set_trace()
    # Handle reload confirmation if required
    for device_name, multi_result in result.items():
        if 'confirm' in multi_result[0].result:
            result = nr.run(
                task=netmiko_send_command,
                use_timing=True,
                command_string="y",
                name="Confirm Reload with Yes",
            )
    print_result(result)
    print("Devices reloaded")
    #ipdb.set_trace()

def postval():
    print('Running postvalidaiton.py against the following Nornir inventory hosts:', nr.inventory.hosts.keys())
    # Ask for credentials at runtime instead of storing.
    nornir_set_creds(nr)

    print("Collecting running configurations and operational values\n")
    resultconf = nr.run(task=collect_configs)
    resultgetters = nr.run(task=collect_getters)
    #import ipdb; ipdb.set_trace()

    #Loop through napalm getters and output current running version.
    prYellow('Current IOS Running Versions:')
    for host in resultgetters:
        print(host, '>>', resultgetters[host][1].result['facts']['os_version'])

    #Perform a Diff between the pre and post nornir getter files we saved.
    for host in nr.inventory.hosts:
        #dont try to open files or compare if a host failed collection
        if host in resultconf.failed_hosts or host in resultgetters.failed_hosts:
            print('!', host, 'failed collection and Op State will not be compared\n')
            #TODO: log netmiko/nornir error to file. otherwise it should exist in nornir.log.
            continue
        else:
            #load facts in hosts pre and post folder and store to var. since were not using pyats native learn objects we must loop through files
            prGreen("vvv --- " + host + " --- Begin Comparison between Pre Upgrade and Post Upgrade operational values vvv")
            for filename in os.listdir(prefacts_dir+host):
                with open(prefacts_dir+host+'/'+filename, 'r') as f:
                    initialstate = json.load(f)
                with open(postfacts_dir+host+'/'+filename, 'r') as f:
                    poststate = json.load(f)
                compare = Diff(initialstate, poststate)
                compare.findDiff()
                print('#', filename, '#\n', compare)
            prGreen("^^^ --- " + host + " --- End Comparison between Pre Upgrade and Post Upgrade operational values ^^^\n")


            prGreen("vvv --- " + host + " --- Begin Comparison between Pre Upgrade and Post Upgrade configurations vvv")
            with open(preconfig_dir+host+'-running.cfg', 'r') as f:
                cfg = f.read()
            initialconfig = Config(cfg)
            initialconfig.tree()
            with open(postconfig_dir+host+'-running.cfg', 'r') as f:
                cfg = f.read()
            postconfig = Config(cfg)
            postconfig.tree()
            compare = Diff(initialconfig, postconfig)
            compare.findDiff()
            prCyan("# " + os.path.basename(f.name) + " #")
            print(compare)
            #ipdb.set_trace()
            prGreen("^^^ --- " + host + " --- End Comparison between Pre Upgrade and Post Upgrade configurations ^^^\n")


""" Set Nornir objects """
nr = InitNornir(config_file="config.yaml")
#Filter devices to run against
if args.group:
    nr = nr.filter(F(groups__contains=args.group))
elif args.host:
    nr = nr.filter(hostname=args.host)
else:
    nr = nr.filter(F(groups__contains="899g"))

#Set/Check environment values and folders
preconfig_dir = "configs/pre/"
prefacts_dir = "facts/pre/"
postconfig_dir = "configs/post/"
postfacts_dir = "facts/post/"
pathlib.Path(preconfig_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(prefacts_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(facts_dir).mkdir(parents=True, exist_ok=True)


if "prevalidate" in args.Action:
    print("you used the --prevalidate flag")
    preval()
elif "stage" in args.Action:
    stage_firmware()
elif "upgrade" in args.Action:
    upgrade_ios()
elif "postvalidate" in args.Action:
    postval()
