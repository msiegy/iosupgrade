# iosupgrade
iosupgrade is a work in progress. It features a collection of python scripts to help automate the image transfer and software upgrade process for IOS routers including the pre and post validation steps. Future versions will feature a single commandline tool.
The collection uses Nornir, Napalm and Genie libraries.

#### prevalidation.py
    Prevalidate storage requirements and store baselines for running config and operational states prior
    to OS Staging and Upgrade

   <img src=gifs/prevalidation.gif width="615" height="385">
    
#### iosstaging.py
    Transfer/Stage IOS image for router upgrade and validate MD5. Bootvars not changed.
    
   <img src=gifs/iosstaging.gif width="615" height="385">
    
#### iosupgrade.py
    Update bootvars and perform IOS upgrade with reload.
    
   <img src=gifs/iosupgrade.gif width="615" height="385">
    
#### postvalidation.py
    Post Upgrade validation - Collect and store current running config and operational states then compare diffs with earlier collection.
  
  <img src=gifs/postvalidation.gif width="615" height="385">


#### TODO:
- Refactor four scripts into single command line tool with arguments for various stages and options.
- Add color formatting to output.
- Add logfile along with output for each run
- Add default enforcement for order of execution, with ability to bypass (i.e: prevalidation before upgrade)
- Add args for verbose modes during execution

#### Installation:
- Clone this Repo to your local machine `https://github.com/msiegy/iosupgrade.git`
- Install required python libraries (consider using venv) `pip install -r requirements.txt`
- Edit the hosts.yaml and groups.yaml nornir inventory files to include your target routers and the location of the upgrade image.
- Edit each python script file to match the nornir filter to your target device groups. Ex: `nr = nr.filter(F(groups__contains="iosv"))`

Disclaimer: These scripts will reload devices and may cause network outages. They are provided AS IS. Test them in a lab and run them at your own risk.

