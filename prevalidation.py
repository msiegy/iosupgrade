"""
Prevalidate and store relevent values prior to OS Staging and Upgrade
"""
import os
import logging
import pathlib
import json
from nornir import InitNornir
from nornir.plugins.tasks import networking
from nornir.plugins.tasks.networking import napalm_get
from nornir.plugins.functions.text import print_result
from nornir_utilities import nornir_set_creds, std_print
import ipdb

config_dir = "configs/"
facts_dir = "facts/"
pathlib.Path(config_dir).mkdir(exist_ok=True)
nr = InitNornir(config_file="config.yaml")

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
    nornir_set_creds(nr)
    #result = nr.run(task=collect_configs)
    #std_print(result)
    result = nr.run(task=collect_getters)
    #facts_result = nr.run(task=napalm_get, getters=['facts', 'environment', 'lldp_neighbors'])
    #ipdb.set_trace()
    std_print(result)

if __name__ == "__main__":
    main()
