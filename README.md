# cnBNG Control Plane Day0 Deployment

This repository contains Python automation to generate cnBNG Control Plane deployment XML from YAML input files and Jinja2 templates. The generated XML is used with SMI Cluster Deployer and, after the cluster is ready, with BNG Ops Center for initial control-plane configuration.

The automation does not discover topology, validate cabling, or calculate IP addressing. The selected YAML file must already contain the correct image URLs, IP addresses, VLANs, CIMC details, credentials, deployment environment, and deployment type.

## Repository Layout

| Path | Purpose |
|---|---|
| `day0-step1.py` | Renders cluster deployment XML and starts cluster deployment through SMI Cluster Deployer NETCONF |
| `day0-step2.py` | Renders cnBNG BNG Ops Center initialization XML and applies it through BNG Ops Center NETCONF |
| `day0_lib.py` | Shared Jinja2 rendering, NETCONF, and deployment functions |
| `yaml/*.yaml` | Deployment input files |
| `template/*.j2` | XML templates rendered by the scripts |
| `config/*.xml` | Generated XML payloads |
| `host_profile/` | Baremetal host profile artifacts referenced by YAML |
| `docs/` | Manual deployment and topology references |

## Prerequisites

- Python 3.
- Python packages: `pyyaml`, `jinja2`, and `ncclient`.
- SMI Cluster Deployer reachable from the script host on NETCONF port `830`.
- BNG Ops Center reachable from the script host on the NETCONF port configured in YAML before running Step 2.
- Web server hosting the images and host profile artifacts referenced in YAML.
- For CNDP baremetal deployments, upload `host_profile/ht.tgz` to the web server and reference that URL in the YAML.

Install Python dependencies:

```bash
python3 -m pip install pyyaml jinja2 ncclient
```

Run all commands from the repository root because template paths are loaded relative to `./`.

## Common Workflow

1. Choose the YAML file for the deployment type.
2. Update the YAML with lab-specific values: SMI Deployer, images, CIMC, management networks, service networks, VLANs, BNG Ops Center, and credentials.
3. Run Step 1 to render and apply the cluster deployment XML.
4. Monitor cluster sync from SMI Cluster Deployer.
5. After the cluster and BNG Ops Center are reachable, run Step 2 to initialize BNG Ops Center.

Step 1 command format:

```bash
python3 day0-step1.py <input-yaml>
```

Step 2 command format:

```bash
python3 day0-step2.py <input-yaml>
```

Monitor deployment from SMI Cluster Deployer:

```text
ssh admin@<smi-deployer-ip> -p 2022
monitor sync-logs <cluster-name>
```

Expected successful sync indication:

```text
Cluster sync successful
```

## Supported Deployment Types

The script path is selected from this YAML structure:

```yaml
cnbng_cp:
  cluster:
    environment: ...
    type: ...
```

| Deployment | YAML | Environment | Type | Step 1 | Step 2 |
|---|---|---|---|---|---|
| VMware AIO | `yaml/vmware_aio_inputs.yaml` | `vmware` | `aio` | Supported | Supported |
| CNDP baremetal AIO | `yaml/cndp_aio_inputs_non_gr.yaml` | `baremetal` | `aio` | Supported | Supported |
| CNDP baremetal AIO geo-red | `yaml/cndp_aio_inputs_gr.yaml` | `baremetal` | `aio_geo-red` | Supported for both UCS clusters | Supported for both UCS clusters |
| CNDP baremetal 3-server geo-red | `yaml/cndp_3server_inputs_cluster1_gr.yaml` | `baremetal` | `3server_geo-red` | Render only in current code | Not implemented |

## VMware AIO Deployment

Use this option for an all-in-one cnBNG Control Plane deployment on VMware.

Input YAML:

```text
yaml/vmware_aio_inputs.yaml
```

Step 1:

```bash
python3 day0-step1.py yaml/vmware_aio_inputs.yaml
```

Step 2:

```bash
python3 day0-step2.py yaml/vmware_aio_inputs.yaml
```

Generated files:

| Purpose | File |
|---|---|
| Cluster deployment XML | `config/cluster-config_vmware_aio.xml` |
| BNG Ops Center initialization XML | `config/bng-ops-center_init-config_vmware_aio.xml` |

Notes:

- Step 1 calls `deploy_vmware_aio`.
- Step 2 calls `init_vmware_aio`.
- Step 2 connects to the BNG Ops Center IP from `cnbng_cp.node_vm.ip`.

## CNDP Baremetal AIO Deployment

Use this option for a single-server baremetal CNDP all-in-one cnBNG Control Plane deployment.

Input YAML:

```text
yaml/cndp_aio_inputs_non_gr.yaml
```

Step 1:

```bash
python3 day0-step1.py yaml/cndp_aio_inputs_non_gr.yaml
```

Step 2:

```bash
python3 day0-step2.py yaml/cndp_aio_inputs_non_gr.yaml
```

Generated files:

| Purpose | File |
|---|---|
| Cluster deployment XML | `config/cluster-config_cndp_aio.xml` |
| BNG Ops Center initialization XML | `config/bng-ops-center_init-config_cndp_aio.xml` |

Notes:

- Step 1 calls `deploy_cndp_aio`.
- Step 2 calls `init_cndp_aio`.
- Step 2 connects to the BNG Ops Center IP from `cnbng_cp.node.ip`.
- The baremetal host profile URL must be valid and reachable from SMI Cluster Deployer.

## CNDP Baremetal AIO Geo-Red Deployment

Use this option for two independent single-server CNDP AIO clusters used as a geo-redundant control-plane pair. The deployment has two UCS servers, UCS1 and UCS2.

The canonical input is now one consolidated YAML file:

```text
yaml/cndp_aio_inputs_gr.yaml
```

This file keeps shared values once and defines the per-UCS values under `cnbng_cp.clusters`. Shared values include images, host profile, SMI Deployer, management gateway, DNS, domain, BNG/CEE Ops Center ports, NTP, service VIPs, and the default `bd1` bond mapping. The per-UCS values make each AIO cluster unique:

| Area | UCS1 Example | UCS2 Example |
|---|---|---|
| Cluster name | `cnbng-cluster-1` | `cnbng-cluster-2` |
| Cluster ID / remote ID | `id: 1`, `remote_id: 2` | `id: 2`, `remote_id: 1` |
| Management IP | `192.168.107.214/25` | `192.168.107.215/25` |
| CIMC IP | `192.168.107.168` | `192.168.107.170` |
| Service VLAN | `101` | `102` |
| Service IP | `172.101.101.101/24` | `172.102.102.102/24` |
| Remote service IP | `172.102.102.102` | `172.101.101.101` |
| Route to peer service network | `172.102.102.0/24 via 172.101.101.4` | `172.101.101.0/24 via 172.102.102.4` |
| BGP ASN / neighbor | `65151` / `172.101.101.4` | `65152` / `172.102.102.4` |

Step 1 expands both `clusters` entries in memory, renders one cluster XML per UCS, and applies both payloads to SMI Cluster Deployer:

```bash
python3 day0-step1.py yaml/cndp_aio_inputs_gr.yaml
```

After both clusters sync successfully and both BNG Ops Centers are reachable, run Step 2 once. It expands the same YAML and initializes both BNG Ops Centers:

```bash
python3 day0-step2.py yaml/cndp_aio_inputs_gr.yaml
```

Generated files:

| Cluster | Cluster deployment XML | BNG Ops Center initialization XML |
|---|---|---|
| UCS1 / `cnbng-cluster-1` | `config/cluster-config_cndp_aio_gr_cnbng-cluster-1.xml` | `config/bng-ops-center_init-config_cndp_aio_gr_cnbng-cluster-1.xml` |
| UCS2 / `cnbng-cluster-2` | `config/cluster-config_cndp_aio_gr_cnbng-cluster-2.xml` | `config/bng-ops-center_init-config_cndp_aio_gr_cnbng-cluster-2.xml` |

Consolidated YAML structure:

```yaml
images:
  bng: ...
  cee: ...
  host_profile: ...

smi_deployer:
  ip: 192.168.107.175
  user: admin
  password: Cisco@123

cnbng_cp:
  node_defaults:
    bond_interfaces:
      bd1:
        links: [enp216s0f0, enp216s0f1]
  bgp:
    aspath_prepend: 'true'
    remote_as: 100
  cluster:
    environment: baremetal
    type: aio_geo-red
    ntp: 72.163.32.44
    istio: 'false'
    cee_ops_center: ...
    bng_ops_center: ...
    networks:
      management: ...
      service: ...
  node:
    name: aio
    networks:
      service:
        mask: 24
        db_port: 8882
        kafka_port: 10001
        remote_db_port: 8882
        remote_kafka_port: 10001
  clusters:
    - site: ucs1
      bgp: ...
      cluster: ...
      node: ...
      cimc: ...
    - site: ucs2
      bgp: ...
      cluster: ...
      node: ...
      cimc: ...
```

Notes:

- Step 1 calls `deploy_cndp_aio_gr`.
- Step 2 calls `init_cndp_aio_gr`.
- The consolidated YAML path generates unique XML filenames using the cluster name.
- Legacy per-UCS YAML files are still supported: `yaml/cndp_aio_inputs_ucs1_gr.yaml` and `yaml/cndp_aio_inputs_ucs2_gr.yaml`.
- Step 2 connects to each BNG Ops Center IP from that cluster entry's `cnbng_cp.node.networks.management.ip`.
- Manual deployment and topology references are available in:
  - `docs/cndp-aio-geored-manual-deployment.md`
  - `docs/cndp-aio-geored-two-ucs-topology.md`

## CNDP Baremetal 3-Server Geo-Red Deployment

Use this option for the 3-server CNDP geo-redundant control-plane design.

Input YAML:

```text
yaml/cndp_3server_inputs_cluster1_gr.yaml
```

Step 1:

```bash
python3 day0-step1.py yaml/cndp_3server_inputs_cluster1_gr.yaml
```

Generated files:

| Purpose | File |
|---|---|
| Cluster deployment XML | `config/cluster-config_cndp_3server_geo-red.xml` |
| BNG Ops Center initialization XML | Not implemented |

Important current-code behavior:

- `day0-step1.py` supports `baremetal` + `3server_geo-red`.
- The `deploy_cndp_3server` function renders `config/cluster-config_cndp_3server_geo-red.xml`.
- The NETCONF push to SMI Cluster Deployer is commented out in `deploy_cndp_3server`, so this path is render-only unless the code is changed.
- `day0-step2.py` has no `3server_geo-red` initialization path.

Before applying 3-server XML, inspect the generated payload and verify it against the intended networking and IP plan. The background reference is:

```text
https://xrdocs.io/cnbng/tutorials/understanding-3-ucs-server-geo-red-control-plane-deployment/
```

## Generated XML Behavior

Output filenames are fixed per deployment type. Re-running a deployment type overwrites the previous generated XML file.

| Deployment | Cluster XML | Init XML |
|---|---|---|
| VMware AIO | `config/cluster-config_vmware_aio.xml` | `config/bng-ops-center_init-config_vmware_aio.xml` |
| CNDP baremetal AIO | `config/cluster-config_cndp_aio.xml` | `config/bng-ops-center_init-config_cndp_aio.xml` |
| CNDP baremetal AIO geo-red consolidated YAML | `config/cluster-config_cndp_aio_gr_<cluster-name>.xml` | `config/bng-ops-center_init-config_cndp_aio_gr_<cluster-name>.xml` |
| CNDP baremetal AIO geo-red legacy per-UCS YAML | `config/cluster-config_cndp_aio_gr.xml` | `config/bng-ops-center_init-config_cndp_aio_gr.xml` |
| CNDP baremetal 3-server geo-red | `config/cluster-config_cndp_3server_geo-red.xml` | Not implemented |

## Operational Notes

- `sendConfigNetconf` connects with `ncclient`, sends `edit-config` to the candidate datastore, and commits.
- Step 1 uses SMI Deployer credentials from the YAML under `smi_deployer`.
- Step 2 uses hard-coded BNG Ops Center credentials `admin` / `Cisco@123` in `day0_lib.py`.
- The scripts do not validate IP reachability, VLAN correctness, image checksums, or CIMC credentials before applying XML.
- There is no dry-run flag for supported NETCONF push paths.
- Some YAML examples contain lab IP addresses and lab credentials. Replace them before using the workflow in another environment.

## Default Login Credentials

| Component | Username | Password |
|---|---|---|
| cnBNG CP Ops Center | `admin` | `Cisco@123` |
| CEE Ops Center | `admin` | `Cisco@123` |
| VMware K8s master node | `cisco` | `Cisco@123` |
| CNDP baremetal K8s master node | `cloud-user` | `Cisco@123` |

Private-key login can also be used for the K8s master node when configured.

## Troubleshooting

| Symptom | Check |
|---|---|
| `IndexError` at startup | Confirm the YAML path was passed as `sys.argv[1]` |
| `KeyError` for `cnbng_cp` or `cluster` | Confirm the YAML structure matches the selected deployment type |
| Consolidated geo-red YAML only renders one cluster | Confirm both UCS entries are listed under `cnbng_cp.clusters` |
| No matching deployment path | Check `cnbng_cp.cluster.environment` and `cnbng_cp.cluster.type` |
| Template not found | Run the command from the repository root |
| NETCONF connection failure | Verify IP, port, username, password, routing, firewall, and service readiness |
| Generated XML overwritten | Save a copy before running the same deployment type for another cluster |
