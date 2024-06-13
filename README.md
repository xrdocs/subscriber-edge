This repo is to deploy cnBNG Control Plane in AIO (All-In-One) form, which is a single node kubernetes cluster deployment of cnBNG CP. This utility generates SMI Deployer configuration and pushes it to the SMI deployer using netconf to start deployment of cnBNG CP Ops Center. Once cnBNG CP Ops Center is deployed, same tool can be leveraged to push desired initial configuration for the Control Plane which sets CDL and the POD deployment schema. 

# Prerequisites
- SMI Deployer (Inception)
- Web Server to host images

Note: For CNDP/ Baremetal deployment host profile is needed. Please copy host_profile/ht.tgz to web server and provide location to it in the yaml file.

# Steps to follow
- Update required yaml file depending on the deployment
  - VMWare VCenter: yaml/vmware_aio_inputs.yaml
  - CNDP Baremetal Single Server: yaml/cndp_aio_inputs.yaml

- Run Step-1 of deployment which will deploy SMI and cnBNG CP Ops Center
```
python3 day0-step1.py yaml/vmware_aio_inputs.yaml
```

- Monitor the deployment of cluster on SMI Deployer:
```
monitor sync-logs <cluster name>
```

- Following log can be seen in monitor sync-logs on successful deployment of the cluster:
```
2024-05-17 08:02:10.239 DEBUG cluster_sync.cnbng-tme-lab-2024: Cluster sync successful
```

# Default Login Credentials (user/ password)
- cnBNG CP Ops Center: admin/ Cisco@123
- CEE Ops Center: admin/ Cisco@123
- K8s Master Node: 
  - VMWare: cisco/ Cisco@123 (or use private-key to login)
  - CNDP/ Baremetal: cloud-user/ Cisco@123 (or use private-key to login)
