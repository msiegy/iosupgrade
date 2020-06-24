# iosupgrade
iosupgrade is a work in progress. It features a collection of python scripts to help automate the image transfer and software upgrade process for IOS routers including the pre and post validation steps. Future versions will feature a single commandline tool.
The collection uses Nornir, Napalm and Genie libraries.

#### Prevalidation
   Prevalidate storage requirements and store baselines for running config and operational states prior
   to OS Staging and Upgrade

   <img src=gifs/cli-preval.gif width="615" height="385">
    
#### Staging
   Transfer/Stage IOS image for router upgrade and validate MD5. Bootvars not changed.
    
   <img src=gifs/cli-stage.gif width="615" height="385">
    
#### Upgrade
   Update bootvars and perform IOS upgrade with reload.
    
   <img src=gifs/cli-upgrade.gif width="615" height="385">
    
#### Postvalidation
   Post Upgrade validation - Collect and store current running config and operational states then compare diffs with earlier collection.
  
  <img src=gifs/cli-postval.gif width="615" height="385">


#### TODO:
- ~~Refactor four scripts into single command line tool with arguments for various stages and options.~~
- ~~Add command line args for inventory filter definitions at runtime to avoid modifying scripts for different targets.~~
- Add color formatting to output.
- Add logfile along with output for each run
- Add default enforcement for order of execution, with ability to bypass (i.e: prevalidation before upgrade)
- Add args for verbose modes during execution


#### Installation:
- Clone this Repo to your local machine `git clone https://github.com/msiegy/iosupgrade.git`
- Install required python libraries (consider using venv) `pip install -r requirements.txt`
  <br>(the pyATS Genie library requires linux or linux on Mac/Windows, alternatively you can run a docker image of pyats as your base)
- Edit the hosts.yaml and groups.yaml nornir inventory files to include your target routers and the location of the upgrade image.

#### Run:
- Run iosautomate.py from the command line and provide the necessary arguments.
- Example: `python iosautomate.py prevalidation --group iosv`

Disclaimer: These scripts will reload devices and may cause network outages. They are provided AS IS. Test them in a lab and run them at your own risk.

Tested against physical ISR routers (G2/1K/4K), C899G and virtual IOSv platforms. These scripts are unlikely to work against switches and other hardware families.
