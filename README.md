# iosupgrade
iosupgrade is a work in progress. It features a collection of python scripts to help automate the image transfer and software upgrade process for IOS devices including the pre and post validation steps.
The collection uses Nornir, Napalm and Genie libraries.


#### prevalidation.py
    Prevalidate storage requirements and store baselines for running config and operational states prior
    to OS Staging and Upgrade
    
#### iosstaging.py
    Transfer/Stage IOS image for router upgrade and validate MD5. Bootvars not changed.
    
#### iosupgrade.py
    Update bootvars and perform IOS upgrade with reload.
    
#### postvalidation.py
    Post Upgrade validation - Collect and store current running config and operational states and compare diffs.
