# Copyright 2016 Packet Host Inc
# See LICENSE file for details.

"""
Packet Test helpers for ``flocker.node.agents``.
"""

import os
import yaml
import socket

from twisted.trial.unittest import SkipTest

from packet_flocker_plugin.packet_blockdevice import (
    PacketBlockDeviceAPI,
    PacketConfiguration
)


def packet_config_from_environment():
    """
    Connect to Packet through Python SDK.
    Config file comes from environment

    :returns:PacketConfiguration Object
    """
    config_file_path = os.environ.get('PACKET_FLOCKER_CFG')
    if config_file_path is not None:
        config_file = open(config_file_path)
    else:
        raise SkipTest(
            'Supply the path to config file '
            'using the PACKET_FLOCKER_CFG environment variable. '
            'See: '
            'https://docs.clusterhq.com/en/latest/gettinginvolved/acceptance-testing.html '  # noqa
            'for details of the expected format.'
        )
    config = yaml.load(config_file.read())
    packet_config = config['packet']
    packet_api_key = packet_config['api_key']
    packet_project_id = packet_config['project_id']
    packet_cluster_id = packet_config['cluster_id']

    return PacketConfiguration(packet_cluster_id,
                               packet_api_key,
                               packet_project_id)


def detach_destroy_volumes(api):
    """
    Detach and destroy all volumes known to this API.
    :param : api object
    """
    volumes = api.list_volumes()

    for volume in volumes:
        if volume.attached_to is not None:
            api.detach_volume(volume.blockdevice_id)
        api.destroy_volume(volume.blockdevice_id)


def cleanup_for_test(test_case):
    """
    Return a ``Packet Client`and register a ``test_case``
    cleanup callback to remove any volumes that are created during each test.
    :param test_case object
    """
    config = packet_config_from_environment()
    packet = PacketBlockDeviceAPI(
        cluster_id=config.cluster_id,
        config=config,
        compute_instance_id=unicode(socket.gethostname()),
        allocation_unit=None)
    test_case.addCleanup(detach_destroy_volumes, packet)

    return packet
