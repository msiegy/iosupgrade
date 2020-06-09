"""
    Stage IOS image for router upgrade.
    Image transfered from Nornir system client to router.
    Requires user with privelge level 15 and 'ip scp server enable'
"""

from nornir import InitNornir
from nornir.plugins.tasks.networking import netmiko_file_transfer
from nornir_utilities import nornir_set_creds, std_print


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
    nornir_set_creds(nr)
    result = nr.run(task=os_staging)
    std_print(result)

if __name__ == "__main__":
    main()
