# _________________________________________________
#
# Cloud BNG/ Cisco Subscriber Edge Demo Portal
#
# Author: Gurpreet Dhaliwal, TME MiG
# __________________________________________________

import yaml
from yaml.loader import SafeLoader
from jinja2 import Environment, FileSystemLoader
from ncclient import manager
import logging
import sys
import time
from io import StringIO

def bannerText(text):
    print("="*100)
    print(text)
    print("="*100)

def sendConfigNetconf(host, port, user, password, config_file):
    m = manager.connect(host=host, port=port, username=user, password=password,
                         hostkey_verify=False, device_params={'name':'default'},
                         look_for_keys=False, allow_agent=False)

    config_file = open(config_file, "r")
    rpc = config_file.read()
    config_file.close()

    reply = m.edit_config(rpc, target='candidate')
    print("RPC reply from "+host+" :")
    print(reply)
    reply = m.commit()
    print(reply)

def deploy_vmware_aio(data):
    bannerText("Create XML Config files from templates for cnBNG CP cluster deployment")
    # Create cluster-config_vmware.xml file for SMI Deployer
    print("1. Creating cluster-config_vmware_aio.xml")
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/cluster-config_vmware_aio.j2")
    filename = 'config/cluster-config_vmware_aio.xml'
    content = template.render(data,K8S_SSH_IP='{{K8S_SSH_IP}}')
    
    with open(filename, mode="w") as message:
        message.write(content)
    
    print("\n")
    bannerText("Start cnBNG CP Cluster Deployment by applying config to SMI Deployer using netconf")
    
    # Apply configurations to SMI Deployer
    print("1. Pushing cnBNG CP Cluster Config XML to SMI Deployer")
    sendConfigNetconf(data['smi_deployer']['ip'],830,data['smi_deployer']['user'],data['smi_deployer']['password'],filename)

def deploy_cndp_aio(data):
    bannerText("Create XML Config files from templates for cnBNG CP cluster deployment")
    # Create cluster-config_vmware.xml file for SMI Deployer
    print("1. Creating cluster-config_cndp_aio.xml")
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/cluster-config_cndp_aio.j2")
    filename = 'config/cluster-config_cndp_aio.xml'
    content = template.render(data)
    
    with open(filename, mode="w") as message:
        message.write(content)
    
    print("\n")
    bannerText("Start cnBNG CP Cluster Deployment by applying config to SMI Deployer using netconf")
    
    # Apply configurations to SMI Deployer
    print("1. Pushing cnBNG CP Cluster Config XML to SMI Deployer")
    sendConfigNetconf(data['smi_deployer']['ip'],830,data['smi_deployer']['user'],data['smi_deployer']['password'],filename)

def init_vmware_aio(data):
    # Create and apply init configuration to BNG Ops Center
    bannerText("Applying cnBNG CP Ops Center Init Config using template bng-ops-center_init-config_vmware_aio.j2")
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/bng-ops-center_init-config_vmware_aio.j2")
    filename = 'config/bng-ops-center_init-config_vmware_aio.xml'
    content = template.render(data)

    with open(filename, mode="w") as message:
        message.write(content)

    sendConfigNetconf(data['cnbng_cp']['node_vm']['ip'],data['cnbng_cp']['cluster']['bng_ops_center']['netconf_port'],'admin','Cisco@123',filename)

    print("\nWait for cluster to be initialized")
    print("\n\n====================================================================================")
    print("====================================================================================")
    print("Access details:")
    print("\ncnBNG CP Ops Center CLI Login: ssh admin@"+data['cnbng_cp']['node_vm']['ip']+" -p "+str(data['cnbng_cp']['cluster']['bng_ops_center']['ssh_port'])+" (pwd: Cisco@123)")
    print("cnBNG CP Ops Center Netconf: ssh admin@"+data['cnbng_cp']['node_vm']['ip']+" -p "+str(data['cnbng_cp']['cluster']['bng_ops_center']['netconf_port'])+" (pwd: Cisco@123)")
    print("\nGrafana Dashboard: https://grafana."+data['cnbng_cp']['node_vm']['ip']+".nip.io (user/pwd: admin/Cisco@123)")
    print("====================================================================================")
    print("====================================================================================")

def init_cndp_aio(data):
    # Create and apply init configuration to BNG Ops Center
    bannerText("Applying cnBNG CP Ops Center Init Config using template bng-ops-center_init-config_cndp_aio.j2")
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/bng-ops-center_init-config_cndp_aio.j2")
    filename = 'config/bng-ops-center_init-config_cndp_aio.xml'
    content = template.render(data)

    with open(filename, mode="w") as message:
        message.write(content)

    sendConfigNetconf(data['cnbng_cp']['node']['ip'],data['cnbng_cp']['cluster']['bng_ops_center']['netconf_port'],'admin','Cisco@123',filename)

    print("\nWait for cluster to be initialized")
    print("\n\n====================================================================================")
    print("====================================================================================")
    print("Access details:")
    print("\ncnBNG CP Ops Center CLI Login: ssh admin@"+data['cnbng_cp']['node']['ip']+" -p "+str(data['cnbng_cp']['cluster']['bng_ops_center']['ssh_port'])+" (pwd: Cisco@123)")
    print("cnBNG CP Ops Center Netconf: ssh admin@"+data['cnbng_cp']['node']['ip']+" -p "+str(data['cnbng_cp']['cluster']['bng_ops_center']['netconf_port'])+" (pwd: Cisco@123)")
    print("\nGrafana Dashboard: https://grafana."+data['cnbng_cp']['node']['ip']+".nip.io (user/pwd: admin/Cisco@123)")
    print("====================================================================================")
    print("====================================================================================")