# Copyright 2016 Packet Host Inc
# See LICENSE file for details..

import os
import time
import re
import socket
import platform
import glob
import requests
import packet
from uuid import UUID
from eliot import Message, Logger
from bitmath import Byte, GiB, KiB
from zope.interface import implementer
from twisted.python.filepath import FilePath
from twisted.python.constants import Values, ValueConstant

from flocker.node.agents.blockdevice import (
    IBlockDeviceAPI, IProfiledBlockDeviceAPI, BlockDeviceVolume, UnknownVolume,
    VolumeException, AlreadyAttachedVolume, UnattachedVolume, UnknownInstanceID,
    MandatoryProfiles,
)

MULTIPATH_TIME_DELAY = 10
CLUSTER_DATASET_ID_DELIMITER = "::"

_logger = Logger()


class DeviceException(Exception):
    """
    A base class for exceptions raised by  ``IBlockDeviceAPI`` operations.
    Due to backend device configuration
    """


class DeviceExceptionAPIError(Exception):
    """
    Error on API call
    """


class VolumeAttached(VolumeException):
    """
    Attempting to destroy an attached volume
    """


class ListVolumesFailure(Exception):
    """
    list volumes failed
    """


class VolumeProfiles(Values):
    """
    :ivar GOLD: The profile for fast storage.
    :ivar SILVER: The profile for intermediate/default storage.
    :ivar BRONZE: The profile for cheap storage.
    :ivar DEFAULT: The default profile if none is specified.
    """
    GOLD = 'storage_2'
    SILVER = 'storage_1'
    BRONZE = 'storage_1'
    DEFAULT = BRONZE


@implementer(IBlockDeviceAPI)
@implementer(IProfiledBlockDeviceAPI)
class PacketBlockDeviceAPI(object):
    """
    A simulated ``IBlockDeviceAPI`` which manages volumes (devices) with Packet
    """

    VERSION = '1.0'
    driver_name = 'Packet'
    consumer_token = 'CWx407aeugZDPNlZz9YT0hU56jQIlSFrV8TaZ2RWyuCgH4fLobLDUd02f3VKAxNH'

    def __init__(self, cluster_id,
                 project_id, api_key):
        """
        :param configuration:
        """
        self._cluster_id = cluster_id
        Message.new(
            Info='cluster id is: '+ str(self._cluster_id)).write(_logger)

        self._project_id = project_id

        self._api = packet.Manager(auth_token=api_key,
                              consumer_token=self.consumer_token)
        if self._api:
            Message.new(
                Info='Connected to Packet API').write(_logger)
        else:
            Message.new(
                Info='Cannot connect to the Packet API').write(_logger)
            raise DeviceExceptionAPIError
    
        data = self._get_metadata()
        self._compute_instance_id = data['id']
        Message.new(
            Info='packet instance id is: '+ str(self._compute_instance_id)).write(_logger)
        self._facility = data['facility']
        Message.new(
            Info='packet facility id is: '+ self._facility).write(_logger)

    def _get_metadata(self):
        r = requests.get('https://metadata.packet.net/metadata')
        if not r.status_code == requests.codes.ok:
            Message.new(
                Error='Call to metadata.packet.net failed, cannot retrieve instance ID', statuscode=r.status_code).write(_logger)
            raise DeviceExceptionAPIError
        Message.new(
            Debug='Call to metadata.packet.net success: ' + r.text).write(_logger)
        return r.json()

    def _get_packet_volume(self, blockdevice_id):
        Message.new(Info='packet _get_packet_volume called', id=str(blockdevice_id)).write(_logger)
        v = self._api.get_volume(blockdevice_id)
        if not v:
            raise UnknownVolume(blockdevice_id)
        return v

    def _blockdevicevolume_from_packet_volume(self, packet_volume):
        dataset_id = packet_volume.description.replace(str(self._cluster_id) + CLUSTER_DATASET_ID_DELIMITER, "", 1)
        Message.new(Info='_blockdevicevolume_from_packet_volume called', clusterid=str(self._cluster_id), dataset=str(dataset_id)).write(_logger)

        attached_to = None
        if packet_volume.attached_to is not None:
            attached_to = unicode(packet_volume.attached_to)

        return BlockDeviceVolume(
            blockdevice_id=unicode(packet_volume.id),
            size=int(GiB(packet_volume.size).to_Byte().value),
            attached_to=attached_to,
            dataset_id=UUID(dataset_id)
        )

    def compute_instance_id(self):
        """
        :return: Compute instance id
        """
        return self._compute_instance_id

    def allocation_unit(self):
        """
        Return int: 10 GB
        """
        return int(GiB(10).to_Byte().value)

    def create_volume(self, dataset_id, size):
        Message.new(Info='packet create_volume', id=str(dataset_id)).write(_logger)
        return self.create_volume_with_profile(
            dataset_id, size, VolumeProfiles.DEFAULT)

    def create_volume_with_profile(self, dataset_id, size, profile_name):
        """
        Create a volume on Packet. Store Flocker-specific
        (cluster id, dataset id) for the volume in description
        """
        try:
            if (profile_name.lower() == 'gold'):
                profile = VolumeProfiles.GOLD
            elif (profile_name.lower() == 'silver'):
                profile = VolumeProfiles.SILVER
            elif (profile_name.lower() == 'bronze'):
                profile = VolumeProfiles.BRONZE
            else:
                profile = VolumeProfiles.DEFAULT

            description = str(self._cluster_id) + CLUSTER_DATASET_ID_DELIMITER + str(dataset_id)
            volsize = ((size / self.allocation_unit()) + 9) // 10 * 10

            Message.new(
                Info='packet creating volume: ' + str(dataset_id), project=self._project_id, profile=profile, allocation=self.allocation_unit(), size=volsize, description=description, facility=self._facility
            ).write(_logger)
            
            v = self._api.create_volume(self._project_id, description, profile, volsize, self._facility)

            Message.new(
                Info='packet volume created: ',
                description=v.description, dataset=str(dataset_id),
                volsize=volsize, size=v.size, profile_name=v.plan, facility=v.facility).write(_logger)

            volume = self._blockdevicevolume_from_packet_volume(v)
            Message.new(
                Info='packet created volume for ' + str(dataset_id)).write(_logger)
        except Exception as ex:
            Message.new(
                Info='packet ERROR creating volume for ' + str(dataset_id),
                resp=ex.message).write(_logger)
            volume = None
            raise DeviceExceptionAPIError

        return volume

    def destroy_volume(self, blockdevice_id):
        """
        Destroy the storage for the given unattached volume.
        :param: blockdevice_id - the volume id
        :raise: UnknownVolume is not found
        """
        Message.new(Info='packet delete called', id=str(blockdevice_id)).write(_logger)
        v = self._get_packet_volume(blockdevice_id)
        v.delete()

    def attach_volume(self, blockdevice_id, attach_to):
        """
        1)  Add initiator to storage instance
        2)  Login
        """

        Message.new(Info='packet attach called', id=str(blockdevice_id), target=str(attach_to)).write(_logger)
        v = self._get_packet_volume(blockdevice_id)

        if v.attached_to == attach_to:
            raise AlreadyAttachedVolume(blockdevice_id)

        if attach_to != self._compute_instance_id:
            raise AttachUnexpectedInstance(
                blockdevice_id, attach_to, self.compute_instance_id)

        # make sure the device is "attached" in the api
        v.attach(attach_to)
        time.sleep(3)

        # attach the lun and setup multipath
        c = "packet-block-storage-attach {} > /dev/null 2>&1"
        cmd = c.format(v.name)
        os.system(cmd)
        # Need to let multipath do its thing before moving on
        time.sleep(MULTIPATH_TIME_DELAY)

        volume = self._blockdevicevolume_from_packet_volume(v)
        Message.new(
            Info='packet attach_volume', vol=blockdevice_id,
            attached_to=attach_to).write(_logger)
        return volume

    def detach_volume(self, blockdevice_id):
        """
        :param: volume id = blockdevice_id
        :raises: unknownvolume exception if not found

        """

        Message.new(Info='packet detach called', id=str(blockdevice_id)).write(_logger)
        v = self._get_packet_volume(blockdevice_id)

        # detach the lun and remove from multipath
        c = "packet-block-storage-detach {} > /dev/null 2>&1"
        cmd = c.format(v.name)
        os.system(cmd)

        # detach in the api
        x = 0
        while x <= 12:
            try:
                x+=1
                time.sleep(5)
                v.detach()
                break
            except:
                Message.new(Info='packet detach() failed with exception').write(_logger)
                pass

        Message.new(
            Info='packet detach_volume', vol=blockdevice_id).write(_logger)

    def list_volumes(self):
        """
        Return ``BlockDeviceVolume`` instances for all the volumes
        available to the project, regardless of attachment state

        See ``IBlockDeviceAPI.list_volumes`` for parameter and return type
        documentation.
        """
        Message.new(
            Info='packet list_volumes called: '+ str(self._cluster_id)).write(_logger)
        volumes = []

        try:
            vs = self._api.list_volumes(self._project_id)
            for v in vs:
                if _is_cluster_volume(self._cluster_id, v):
                    volumes.append(
                        self._blockdevicevolume_from_packet_volume(v)
                    )
        except Exception as e:
            Message.new(
                Info='packet list_volumes exception: '+ e.message).write(_logger)
            raise ListVolumesFailure(e)
        Message.new(Info="packet volume list",
            volume_ids=list(volume.blockdevice_id for volume in volumes),
        ).write()

        return volumes


    def get_device_path(self, blockdevice_id):
        """
        :param blockdevice_id:
        :return:the device path
        """

        Message.new(Info='packet get_device_path called', id=str(blockdevice_id)).write(_logger)
        v = self._get_packet_volume(blockdevice_id)

        mpath = '/dev/mapper/'+ v.name
        if os.path.exists(mpath):
            return FilePath(mpath)
        else:
            Message.new(
                Info='FAIL block device file path not found : ' + str(mpath)).write(_logger)
        raise UnattachedVolume(blockdevice_id)


def packet_from_configuration(cluster_id, project_id, api_key):
    """
    :param cluster_id:
    :param project_id:
    :param api_key:
    :return:PacketBlockDeviceAPI object
    """
    return PacketBlockDeviceAPI(
        cluster_id=cluster_id,
        project_id=project_id,
        api_key=api_key
    )


def _is_cluster_volume(cluster_id, packet_volume):
    """
    Helper function to check if given volume belongs to
    given cluster.
    :param UUID cluster_id: UUID of Flocker cluster to check for
        membership.
    :param packet.Volume packet_volume: Packet volume to check
        for input cluster membership.
    :return bool: True if input volume belongs to input
        Flocker cluster. False otherwise.
    """
    if packet_volume.description is not None and packet_volume.description.startswith(str(cluster_id)):
        return True
    return False
