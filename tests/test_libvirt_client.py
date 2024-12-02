
# Tectonic - An academic Cyber Range
# Copyright (C) 2024 Grupo de Seguridad Informática, Universidad de la República,
# Uruguay
#
# This file is part of Tectonic.
#
# Tectonic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tectonic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tectonic.  If not, see <http://www.gnu.org/licenses/>.

import libvirt
import libvirt_qemu
import pytest
from libvirt import libvirtError

from tectonic.libvirt_client import LibvirtClientException, Client as LibvirtClient

def test_libvirt_client_constructor(description):
    """Test libvirt client creation and destruction."""

    original_uri = description.libvirt_uri
    description.libvirt_uri = "/invalid/"
    with pytest.raises(LibvirtClientException) as exception:
        LibvirtClient(description)
    assert "Cannot connect to libvirt server" in str(exception.value)

    description.libvirt_uri = original_uri
    LibvirtClient(description)


def test_wait_for_agent(mocker, libvirt_client):
    """ Test wait_for_agent when there is an agent in the domain, and when there is not."""
    with pytest.raises(libvirtError) as excinfo:
        not_found = libvirt_client.conn.lookupByName("not found")
    assert "Domain not found" in str(excinfo.value)

    domain = libvirt_client.conn.lookupByName("test")
    with pytest.raises(LibvirtClientException) as excinfo:
        libvirt_client.wait_for_agent(domain, sleep=1, max_tries=2)
    assert "Cannot connect to QEMU agent." in str(excinfo.value)

    # Application of the patch to replace libvirt_qemu.qemuAgentCommand
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    assert libvirt_client.wait_for_agent(domain) is None

def test_get_machine_private_ip_address(mocker, libvirt_client):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    ipaddr = libvirt_client.get_machine_private_ip("test")
    assert ipaddr == "10.0.1.5"

    ipaddr = libvirt_client.get_machine_private_ip("notfound")
    assert ipaddr is None

    ipaddr = libvirt_client.get_machine_private_ip("no_net")
    assert ipaddr is None

    ipaddr = libvirt_client.get_machine_private_ip("lo_net")
    assert ipaddr is None


def test_get_machine_public_ip_address(libvirt_client):
    ipaddr = libvirt_client.get_machine_public_ip("test")
    assert ipaddr is None

def test_delete_image(libvirt_client):
    with (pytest.raises(LibvirtClientException) as exception):
        libvirt_client.delete_image("tectonic", "test")
    assert "Failed to locate tectonic storage pool." in str(exception.value)

    libvirt_client.delete_image("pool-dir", "notfound")
    assert True                 # Does nothing if volume does not exist

    libvirt_client.delete_image("pool-dir", "test")
    pool = libvirt_client.conn.storagePoolLookupByName("pool-dir")
    with pytest.raises(libvirtError):
        vol = pool.storageVolLookupByName("test")


def test_get_instance_status(libvirt_client):
    state = libvirt_client.get_instance_status("test")
    assert state == "RUNNING"
    state = libvirt_client.get_instance_status("notfound")
    assert state == "NOT FOUND"


def test_start_instance(libvirt_client):
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    # Test starting a RUNNING instance
    libvirt_client.start_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Stop the domain
    libvirt_client.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]

    # Test starting a SHUTOFF instance
    libvirt_client.start_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Test a non-existent domain
    with pytest.raises(LibvirtClientException) as exception:
        libvirt_client.start_instance("notfound")
    assert "Domain notfound not found." in str(exception.value)


def test_stop_instance(libvirt_client):
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    libvirt_client.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    libvirt_client.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]

    # Test a non-existent domain
    with pytest.raises(LibvirtClientException) as exception:
        libvirt_client.stop_instance("notfound")
    assert "Domain notfound not found." in str(exception.value)

def test_reboot_instance(libvirt_client):
    # Restart a RUNNING domain
    libvirt_client.start_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    libvirt_client.reboot_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Restart a SHUTOFF domain
    libvirt_client.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    libvirt_client.reboot_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Restart a PAUSED domain
    dom = libvirt_client.conn.lookupByName('test')
    dom.suspend()
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_PAUSED]
    libvirt_client.reboot_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_PAUSED]
    dom.resume()
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Test a non-existent domain
    with pytest.raises(LibvirtClientException) as exception:
        libvirt_client.reboot_instance("notfound")
    assert "Domain notfound not found." in str(exception.value)
