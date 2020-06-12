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
pathlib.Path(config_dir).mkdir(exist_ok=True)

#set directories for previously gathered op stats and config
intial_config_dir = "configs/pre/"
initial_facts_dir = "facts/pre/"

nr = InitNornir(config_file="config.yaml")
#Filter devices to run against
nr = nr.filter(F(groups__contains="iosv"))

resultconf = nr.run(task=collect_configs)
resultgetters = nr.run(task=collect_getters)


confdiff = Diff(initial_config_dir, config_dir)
opsdiff = Diff(initial_facts_dir, facts_dir)

print(confdiff)
print(opsdiff)
ipdb.set_trace()