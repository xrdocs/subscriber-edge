# _________________________________________________
#
# Cloud BNG/ Cisco Subscriber Edge Demo Portal
#
# Author: Gurpreet Dhaliwal, TME MiG
# __________________________________________________

import sys
import yaml
import day0_lib as dl

from yaml.loader import SafeLoader
from jinja2 import Environment, FileSystemLoader

print("\n")

# Open yaml file and load the file
with open(sys.argv[1]) as f:
    data = yaml.load(f, Loader=SafeLoader)

if(data['cnbng_cp']['cluster']['environment']=="vmware" and data['cnbng_cp']['cluster']['type']=="aio"):
    dl.deploy_vmware_aio(data)
elif(data['cnbng_cp']['cluster']['environment']=="baremetal" and data['cnbng_cp']['cluster']['type']=="aio"):
    dl.deploy_cndp_aio(data)
else:
    print("Error: Unknown Deployment Environment and Type")
    exit()

print("\n====================================================================================")
print("Deployment of cnBNG CP Cluster should have started. To monitor deployment progress, login to-")
print("\n1. SMI Deployer, using: ssh admin@"+data['smi_deployer']['ip']+" -p 2022")
print("2. and to check progress use: \"monitor sync-logs "+data['cnbng_cp']['cluster']['name']+"\" command")
print("====================================================================================")
