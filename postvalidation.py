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

config_dir = "configs/post/"
facts_dir = "facts/post/"
