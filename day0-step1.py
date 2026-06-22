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

environment, deployment_type = dl.getDeploymentEnvironmentType(data)

if(environment=="vmware" and deployment_type=="aio"):
    dl.deploy_vmware_aio(data)
elif(environment=="baremetal" and deployment_type=="aio"):
    dl.deploy_cndp_aio(data)
elif(environment=="baremetal" and deployment_type=="aio_geo-red"):
    dl.deploy_cndp_aio_gr(data)
elif(environment=="baremetal" and deployment_type=="3server_geo-red"):
    dl.deploy_cndp_3server(data)
else:
    print("Error: Unknown Deployment Environment and Type")
    exit()

print("\n====================================================================================")
print("Deployment of cnBNG CP Cluster should have started. To monitor deployment progress, login to-")
for index, target in enumerate(dl.getMonitorTargets(data), start=1):
    print("\n"+str(index)+". SMI Deployer, using: ssh admin@"+target['smi_ip']+" -p 2022")
    print("   and to check progress use: \"monitor sync-logs "+target['cluster_name']+"\" command")
print("====================================================================================")
