# Copyright 2016 Packet Host, Inc
# See LICENSE file for details.

from flocker.node import BackendDescription, DeployerType
from packet_flocker_plugin.packet_blockdevice import packet_from_configuration


def api_factory(cluster_id, **kwargs):
    return packet_from_configuration(cluster_id=cluster_id,
                                     api_key=kwargs[u'api_key'],
                                     project_id=kwargs[u'project_id'])


FLOCKER_BACKEND = BackendDescription(
    name=u"packet_flocker_plugin",
    needs_reactor=False, needs_cluster_id=True,
    required_config={u"api_key", u"project_id"},
    api_factory=api_factory, deployer_type=DeployerType.block)
