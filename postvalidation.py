"""
    Post Upgrade validation - Collect and store running config and current
    operational states post OS Upgrade and compare diffs.

    Tasks:
    1) Collect and store running configurations to local machine.
    2) Collect and store napalm getters to local machine.
    3) Validate running OS version meets expected value
    4) Perform Diff on running configurations and operation states.
    5) Perform Misc checks
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
from prevalidation import collect_configs, collect_getters, store_output, store_config
from genie.conf import Genie
from genie.utils.config import Config
from genie.utils.diff import Diff


config_dir = "configs/post/"
facts_dir = "facts/post/"
pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(facts_dir).mkdir(parents=True, exist_ok=True)
#set directories for previously gathered op stats and config
initial_config_dir = "configs/pre/"
initial_facts_dir = "facts/pre/"

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

    for entry in facts_result.result.keys():
        for getter in facts_result:
            filename = entry
            content = json.dumps(getter.result[entry], indent=2)
            store_output(task.host.name, entry_dir, content, filename)


nr = InitNornir(config_file="config.yaml")
#Filter devices to run against
nr = nr.filter(F(groups__contains="iosv"))
print('Running iosstaging.py against the following Nornir inventory hosts:', nr.inventory.hosts.keys())
# Ask for credentials at runtime instead of storing.
nornir_set_creds(nr)

resultconf = nr.run(task=collect_configs)
resultgetters = nr.run(task=collect_getters)
#import ipdb; ipdb.set_trace()

#Loop through napalm getters and output current running version.
print('Current IOS Running Versions:')
for host in resultgetters:
    print(host, '>>', resultgetters[host][1].result['facts']['os_version'])

#Perform a Diff between the pre and post nornir getter files we saved.
for host in nr.inventory.hosts:
    #dont try to open files or compare if a host failed collection
    if host in resultconf.failed_hosts or host in resultgetters.failed_hosts:
        print('!', host, 'failed collection and Op State will not be compared\n')
        continue
    else:
        #load facts in hosts pre and post folder and store to var. since were not using pyats native learn objects we must loop through files
        print("vvv --", host, "--- Begin Comparison between Pre Upgrade and Post Upgrade operational values vvv")
        for filename in os.listdir(initial_facts_dir+host):
            with open(initial_facts_dir+host+'/'+filename, 'r') as f:
                initialstate = json.load(f)
            with open(facts_dir+host+'/'+filename, 'r') as f:
                poststate = json.load(f)
            compare = Diff(initialstate, poststate)
            compare.findDiff()
            print('#', filename, '#\n', compare)
        print("^^^ --", host, "--- End Comparison between Pre Upgrade and Post Upgrade operational values ^^^\n")
