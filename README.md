# iosupgrade
iosupgrade is a work in progress. It features a collection of python scripts to help automate the image transfer and software upgrade process for IOS routers including the pre and post validation steps. A single command line call is used with flags to initiate Prevalidation, Staging, Upgrade and Postvalidation steps against a Nornir inventory. The collection uses Nornir, Napalm and Genie libraries.

Examples: 
<br>`python iosautomate prevalidate --group C899G`
<br>`python iosautomate stage --host 10.24.15.5`

#### Prevalidation
   Validate storage requirements (bootflash) and store baselines for running config and operational states prior
   to OS Staging and Upgrade.

   <img src=gifs/cli-preval.gif width="615" height="385">
    
#### Staging
   Transfer/Stage IOS image for router upgrade and validate MD5. Bootvars not changed.
    
   <img src=gifs/cli-stage.gif width="615" height="385">
    
#### Upgrade
   Update bootvars and perform IOS upgrade with reload. Validate image exists on flash, set previous image as backup if it exists and then request confirmation before Wr Mem and Reload.
    
   <img src=gifs/cli-upgrade.gif width="615" height="385">
    
#### Postvalidation
   Post Upgrade validation - Collect and store current running config and operational states then compare diffs with earlier collection. 
  
  <img src=gifs/cli-postval.gif width="615" height="385">


#### TODO:
- ~~Refactor four scripts into single command line tool with arguments for various stages and options.~~
- ~~Add command line args for inventory filter definitions at runtime to avoid modifying scripts for different targets.~~
- Add verbose logfile along with output for each run
- Add default enforcement for order of execution, with ability to bypass (i.e: prevalidation must occur before upgrade)
- Add args for verbose modes during execution
- Add args for adding optional VRF and IGP op checks


#### Installation:
- Clone this Repo to your local machine `git clone https://github.com/msiegy/iosupgrade.git`
- Install required python libraries (consider using venv) `pip install -r requirements.txt`
  <br>(the pyATS Genie library requires linux or linux on Mac/Windows, alternatively you can run a docker image of pyats as your base)
- Edit the hosts.yaml and groups.yaml nornir inventory files to include your target routers and the location of the upgrade image.

#### Run:
- Run iosautomate.py from the command line and provide the necessary arguments.
- Example: `python iosautomate.py prevalidation --group iosv`

Disclaimer: These scripts will reload devices and may cause network outages. They are provided AS IS. Test them in a lab and run them at your own risk.

Tested against physical ISR routers (G2/1K/4K), C899G and virtual IOSv platforms. These scripts in there current state are unlikely to work against switches and other hardware families.
