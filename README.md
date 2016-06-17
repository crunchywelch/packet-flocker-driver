Packet Flocker Plugin
======================


## Installation

- Install ClusterHQ/Flocker
      

             Refer to install notes :
                    https://docs.clusterhq.com/en/latest/docker-integration/install-node.html

- Install Packet Plugin

Flocker comes with its own Python context.
Flocker also depends on the ClusterHQ forked repository of 'testtools'
You must install the plugin and Packet Python SDK within the Flocker Python context.
You CANNOT use the default Python command.

```bash
    git clone https://github.com/packet/python-sdk
    cd python-sdk
    sudo /opt/flocker/bin/python2.7 setup.py install
    cd ..
    git clone https://github.com/packet/packet-flocker-driver
    cd packet-flocker-driver
    sudo /opt/flocker/bin/pip install --upgrade --process-dependency-links .[dev] \
           git+https://github.com/ClusterHQ/testtools@clusterhq-fork#egg=testtools-1.8.2chq2
    sudo /opt/flocker/bin/python2.7 setup.py install
```

## Usage Instructions
To start the plugin on a node, a configuration file must exist on the node at /etc/flocker/agent.yml. This should be as follows, replacing __${packet_ip}__,   __${packet_user}__ and __${packet_password}__ with the ip/hostname, username and password of Packet Mgmt IP port:
```bash
version: 1
control-service:
   hostname: ${FLOCKER_CONTROL_NODE}
dataset:
   backend: packet_flocker_plugin
   mgmt_addr: ${packet_ip}
   user: ${packet_user}
   password: ${packet_password}
   cluster_id: "flocker-"
```

## Running Tests

To verify the packet-flocker-plugin, setup the config file (edit values for your environment)
```bash
export PACKET_FLOCKER_CFG=/etc/flocker/packet.yml
vi $PACKET_FLOCKER_CFG
packet:
  user: ${Packet_USERNAME}
  password: ${Packet_PASSWORD}
  mgmt_addr: ${Packet_MGMT_IP}
  cluster_id: "flocker-"
```
Run the tests
```bash
cd packet_flocker_plugin
/opt/flocker/bin/trial packet_flocker_plugin.test_packet
```
You should see below if all was succesfull

PASSED (successes=27)


## Future

## Contribution
Create a fork of the project into your own reposity. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

## Licensing
**Packet will not provide legal guidance on which open source license should be used in projects. We do expect that all projects and contributions will have a valid open source license, or align to the appropriate license for the project/contribution**

Copyright [2015] [Packet Host Inc]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Support
Please file bugs and issues at the Github issues page. For more general discussions you can contact the Flocker team at <a href="https://groups.google.com/forum/#!forum/flocker-users">Google Groups</a> or tagged with **Packet** on <a href="https://stackoverflow.com">Stackoverflow.com</a>. The code and documentation are released with no warranties or SLAs and are intended to be supported through a community driven process.
