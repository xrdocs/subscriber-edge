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

print("\n")


if(data['cnbng_cp']['cluster']['environment']=="vmware" and data['cnbng_cp']['cluster']['type']=="aio"):
    dl.init_vmware_aio(data)
elif(data['cnbng_cp']['cluster']['environment']=="baremetal" and data['cnbng_cp']['cluster']['type']=="aio"):
    dl.init_cndp_aio(data)
else:
    print("Error: Unknown Deployment Environment and Type")
    exit()




