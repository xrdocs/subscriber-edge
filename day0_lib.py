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
from copy import deepcopy
import re

def bannerText(text):
    print("="*100)
    print(text)
    print("="*100)

def deepMerge(base, override):
    result = deepcopy(base) if isinstance(base, dict) else {}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deepMerge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result

def getDeploymentEnvironmentType(data):
    cluster = data.get('cnbng_cp', {}).get('cluster', {})
    cluster_defaults = data.get('cnbng_cp', {}).get('cluster_defaults', {})
    environment = cluster.get('environment', cluster_defaults.get('environment'))
    deployment_type = cluster.get('type', cluster_defaults.get('type'))
    return environment, deployment_type

def isConsolidatedCndpAioGeoRed(data):
    environment, deployment_type = getDeploymentEnvironmentType(data)
    clusters = data.get('cnbng_cp', {}).get('clusters')
    return (
        environment == "baremetal"
        and deployment_type == "aio_geo-red"
        and isinstance(clusters, list)
        and len(clusters) > 0
    )

def applyFlattenedGeoRedClusterFields(cluster_data, cluster_entry):
    cp = cluster_data['cnbng_cp']

    for key in ['name', 'id', 'remote_id']:
        if key in cluster_entry:
            cp.setdefault('cluster', {})[key] = cluster_entry[key]

    if 'cimc_ip' in cluster_entry:
        cluster_data.setdefault('cimc', {})['ip'] = cluster_entry['cimc_ip']

    if 'management_ip' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('management', {})['ip'] = cluster_entry['management_ip']
    if 'management_mask' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('management', {})['mask'] = cluster_entry['management_mask']

    if 'service_vlan' in cluster_entry:
        cp.setdefault('cluster', {}).setdefault('networks', {}).setdefault('service', {})['id'] = cluster_entry['service_vlan']
    if 'service_ip' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('service', {})['ip'] = cluster_entry['service_ip']
    if 'service_mask' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('service', {})['mask'] = cluster_entry['service_mask']
    if 'remote_service_ip' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('service', {})['remote_ip'] = cluster_entry['remote_service_ip']
    if 'route_to_remote' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('service', {}).setdefault('route', {})['to'] = cluster_entry['route_to_remote']
    if 'route_via' in cluster_entry:
        cp.setdefault('node', {}).setdefault('networks', {}).setdefault('service', {}).setdefault('route', {})['via'] = cluster_entry['route_via']

    if 'bgp_asn' in cluster_entry:
        cp.setdefault('bgp', {})['asn'] = cluster_entry['bgp_asn']
    if 'bgp_neighbor' in cluster_entry:
        cp.setdefault('bgp', {})['neighbor'] = cluster_entry['bgp_neighbor']
    if 'bgp_remote_as' in cluster_entry:
        cp.setdefault('bgp', {})['remote_as'] = cluster_entry['bgp_remote_as']

def expandCndpAioGeoRedClusters(data):
    if not isConsolidatedCndpAioGeoRed(data):
        return [data]

    base_data = deepcopy(data)
    cluster_entries = base_data['cnbng_cp'].pop('clusters')
    cp = base_data['cnbng_cp']

    if 'cluster_defaults' in cp:
        cp['cluster'] = deepMerge(cp.get('cluster_defaults', {}), cp.get('cluster', {}))
        del cp['cluster_defaults']

    cluster_payloads = []
    for cluster_entry in cluster_entries:
        cluster_data = deepcopy(base_data)
        cluster_cp = cluster_data['cnbng_cp']

        for section in ['bgp', 'cluster', 'node', 'node_defaults']:
            if section in cluster_entry:
                cluster_cp[section] = deepMerge(cluster_cp.get(section, {}), cluster_entry[section])

        if 'cimc' in cluster_entry:
            cluster_data['cimc'] = deepMerge(cluster_data.get('cimc', {}), cluster_entry['cimc'])

        applyFlattenedGeoRedClusterFields(cluster_data, cluster_entry)
        cluster_payloads.append(cluster_data)

    return cluster_payloads

def getMonitorTargets(data):
    targets = []
    for cluster_data in expandCndpAioGeoRedClusters(data):
        targets.append({
            'smi_ip': cluster_data['smi_deployer']['ip'],
            'cluster_name': cluster_data['cnbng_cp']['cluster']['name']
        })
    return targets

def clusterFilenameSuffix(data):
    cluster_name = data['cnbng_cp']['cluster'].get('name', 'cluster')
    suffix = re.sub(r'[^A-Za-z0-9_.-]+', '-', cluster_name).strip('-')
    return suffix or 'cluster'

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

def deploy_cndp_aio_gr(data):
    if isConsolidatedCndpAioGeoRed(data):
        bannerText("Deploy consolidated cnBNG CP AIO geo-red clusters")
        for cluster_data in expandCndpAioGeoRedClusters(data):
            suffix = clusterFilenameSuffix(cluster_data)
            filename = 'config/cluster-config_cndp_aio_gr_' + suffix + '.xml'
            deploy_cndp_aio_gr_single(cluster_data, filename)
        return

    deploy_cndp_aio_gr_single(data, 'config/cluster-config_cndp_aio_gr.xml')

def deploy_cndp_aio_gr_single(data, filename):
    bannerText("Create XML Config files from templates for cnBNG CP GR cluster deployment")
    # Create cluster-config_vmware.xml file for SMI Deployer
    print("1. Creating "+filename)
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/cluster-config_cndp_aio_gr.j2")
    content = template.render(data)
    
    with open(filename, mode="w") as message:
        message.write(content)
    
    print("\n")
    bannerText("Start cnBNG CP Cluster Deployment by applying config to SMI Deployer using netconf")
    
    # Apply configurations to SMI Deployer
    print("1. Pushing cnBNG CP Cluster Config XML to SMI Deployer")
    sendConfigNetconf(data['smi_deployer']['ip'],830,data['smi_deployer']['user'],data['smi_deployer']['password'],filename)

def deploy_cndp_3server(data):
    bannerText("Create XML Config files from templates for cnBNG CP cluster deployment")
    # Create cluster-config_vmware.xml file for SMI Deployer
    print("1. Creating cluster-config_cndp_3server_geo-red.xml")
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/cluster-config_cndp_3server_geo-red.j2")
    filename = 'config/cluster-config_cndp_3server_geo-red.xml'
    content = template.render(data)
    
    with open(filename, mode="w") as message:
        message.write(content)
    
    print("\n")
    bannerText("Start cnBNG CP Cluster Deployment by applying config to SMI Deployer using netconf")
    
    # Apply configurations to SMI Deployer
    print("1. Pushing cnBNG CP Cluster Config XML to SMI Deployer")
    #sendConfigNetconf(data['smi_deployer']['ip'],830,data['smi_deployer']['user'],data['smi_deployer']['password'],filename)

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

def init_cndp_aio_gr(data):
    if isConsolidatedCndpAioGeoRed(data):
        bannerText("Initialize consolidated cnBNG CP AIO geo-red clusters")
        for cluster_data in expandCndpAioGeoRedClusters(data):
            suffix = clusterFilenameSuffix(cluster_data)
            filename = 'config/bng-ops-center_init-config_cndp_aio_gr_' + suffix + '.xml'
            init_cndp_aio_gr_single(cluster_data, filename)
        return

    init_cndp_aio_gr_single(data, 'config/bng-ops-center_init-config_cndp_aio_gr.xml')

def init_cndp_aio_gr_single(data, filename):
    # Create and apply init configuration to BNG Ops Center
    bannerText("Applying cnBNG CP Ops Center Init Config using template bng-ops-center_init-config_cndp_aio_gr.j2")
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("template/bng-ops-center_init-config_cndp_aio_gr.j2")
    content = template.render(data)

    with open(filename, mode="w") as message:
        message.write(content)

    sendConfigNetconf(data['cnbng_cp']['node']['networks']['management']['ip'],data['cnbng_cp']['cluster']['bng_ops_center']['netconf_port'],'admin','Cisco@123',filename)

    print("\nWait for cluster to be initialized")
    print("\n\n====================================================================================")
    print("====================================================================================")
    print("Access details:")
    print("\ncnBNG CP Ops Center CLI Login: ssh admin@"+data['cnbng_cp']['node']['networks']['management']['ip']+" -p "+str(data['cnbng_cp']['cluster']['bng_ops_center']['ssh_port'])+" (pwd: Cisco@123)")
    print("cnBNG CP Ops Center Netconf: ssh admin@"+data['cnbng_cp']['node']['networks']['management']['ip']+" -p "+str(data['cnbng_cp']['cluster']['bng_ops_center']['netconf_port'])+" (pwd: Cisco@123)")
    print("\nGrafana Dashboard: https://grafana."+data['cnbng_cp']['node']['networks']['management']['ip']+".nip.io (user/pwd: admin/Cisco@123)")
    print("====================================================================================")
    print("====================================================================================")
