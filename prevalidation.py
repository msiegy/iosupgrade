"""
Prevalidate and store baselines for running config and operational values prior
to OS Staging and Upgrade

Tasks:
1) Validate sufficient disk space based on file defined in groups.yaml
2) Collect and store running configurations to local machine.
3) Collect and store napalm getters to local machine.
"""

import os
import logging
import pathlib
import json
import re
from nornir import InitNornir
from nornir.plugins.tasks import networking
from nornir.plugins.tasks.networking import napalm_get, netmiko_send_command
from nornir.plugins.functions.text import print_result
from nornir_utilities import nornir_set_creds, std_print
from nornir.core.filter import F
import ipdb

config_dir = "configs/"
facts_dir = "facts/"
pathlib.Path(config_dir).mkdir(exist_ok=True)
nr = InitNornir(config_file="config.yaml")
#Filter devices to run against
nr = nr.filter(F(groups__contains="iosv"))

def validate_storage(task):
    result = task.run(
        task=netmiko_send_command,
        command_string="dir"
    )
    output = result[0].result

    #regex to find space available
    m = re.search(r'^(\d+) bytes total \((\d+) bytes free', output, re.M)
    totalbytes = int(m.group(1))
    availablebytes = int(m.group(2))
    #check planned imaged size against space available
    file_name = task.host.get('img')
    #retrieve file size in bytes
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
    with open(os.path.join(config_dir, filename), "w") as f:
        f.write(config)

def store_output(hostname, entry_dir, content, filename):
    filename = f"{filename}.txt"
    with open(os.path.join(entry_dir, filename), "w") as f:
        f.write(str(content))

def collect_getters(task):
    entry_dir = facts_dir + task.host.name
    pathlib.Path(facts_dir).mkdir(exist_ok=True)
    pathlib.Path(entry_dir).mkdir(exist_ok=True)

    facts_result = task.run(task=napalm_get, getters=['facts', 'environment', 'lldp_neighbors', 'interfaces'])
    #ipdb.set_trace()
    for entry in facts_result.result.keys():
        for getter in facts_result:
            filename = entry
            #content = getter.result[entry]
            content = json.dumps(getter.result[entry], indent=2)
            #ipdb.set_trace()
            store_output(task.host.name, entry_dir, content, filename)

def main():
    # Ask for credentials at runtime instead of storing.
    nornir_set_creds(nr)

    #Connect to devices to check if there is sufficient disk space.
    result = nr.run(task=validate_storage, name='Validate Storage Requirements')
    for host in result:
        if result[host][0].result:
            print("Success - Sufficient storage available on", host)
        else:
            print("!!! There is not enough space to transfer the image on", host)
    print_result(result)
    #Connect to devices and store their running configurations to local folders.
    result = nr.run(task=collect_configs)
    #std_print(result)
    #Connect to devices and collect napalm getters, store to local folders.
    result = nr.run(task=collect_getters)
    #print_result(result)
    #ipdb.set_trace()

if __name__ == "__main__":
    main()
