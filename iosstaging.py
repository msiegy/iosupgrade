"""
    Transfer/Stage IOS image for router upgrade and validate MD5. Bootvars not changed.

    Tasks:
    1) Transfer image defined in groups.yaml from client to router using netmiko
    file transfer. Idempotent transfer.
    2) Check File exists and MD5 Hash on completion. if file exists valueerror.

    Requires user with privelge level 15 (without enable) and 'ip scp server enable'

"""

from nornir import InitNornir
from nornir.plugins.tasks.networking import netmiko_file_transfer
from nornir_utilities import nornir_set_creds, std_print
from nornir.plugins.functions.text import print_result
from nornir.core.filter import F

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

def main():
    nr = InitNornir(config_file="config.yaml")
    nr = nr.filter(F(groups__contains="iosv"))
    print('Running iosstaging.py against the following Nornir inventory hosts:', nr.inventory.hosts.keys())
    nornir_set_creds(nr)
    result = nr.run(task=os_staging)
    print_result(result)
    #import ipdb; ipdb.set_trace()

if __name__ == "__main__":
    main()
