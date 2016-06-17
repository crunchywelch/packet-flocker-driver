# Copyright 2016 Packet Host, Inc
# See LICENSE file for details.

"""
Functional tests for
``flocker.node.agents.blockdevice.PacketBlockDeviceAPI``
"""

import os
import socket
from uuid import uuid4
from twisted.trial.unittest import SynchronousTestCase, SkipTest
import functools
from flocker.node.agents.test.test_blockdevice import (
        make_iblockdeviceapi_tests
)
from testtools_packet import (
    cleanup_for_test
)


PACKET_ALLOCATION_UNIT = int(1024 * 1024 * 1024)


def packetblockdeviceapi_for_test(test_case):
    """
    Create a ``PacketBlockDeviceAPI`` instance for use in tests.
    :returns: A ``PacketBlockDeviceAPI`` instance
    """
    user_id = os.getuid()
    if user_id != 0:
        raise SkipTest(
            "``PacketBlockDeviceAPI`` queries for iSCSI initiator name \
                           which is owned by root, "
            "Required UID: 0, Found UID: {!r}".format(user_id)
        )
    dfs = cleanup_for_test(test_case)
    return dfs


class PacketBlockDeviceAPIInterfaceTests(
    make_iblockdeviceapi_tests(
        blockdevice_api_factory=functools.partial(
                 packetblockdeviceapi_for_test),
        minimum_allocatable_size=PACKET_ALLOCATION_UNIT,
        device_allocation_unit=PACKET_ALLOCATION_UNIT,
        unknown_blockdevice_id_factory=lambda test: u"vol-00000000"
    )
):

    """
      Interface adherence Tests for ``PacketBlockDeviceAPI``
    """
