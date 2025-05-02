
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

from tectonic.client import Client
from tectonic.ssh import interactive_shell

import libvirt
import libvirt_qemu
import time
from ipaddress import ip_network, ip_address
import xml.etree.ElementTree as ET

class ClientLibvirtException(Exception):
    pass

# Avoid console output.
# See https://stackoverflow.com/questions/45541725/avoiding-console-prints-by-libvirt-qemu-python-apis
def libvirt_callback(userdata, err):
    pass

class ClientLibvirt(Client):
    """
    ClientLibvirt class.

    Description: Implement Client for Libvirt.
    """

    STATE_MSG = {
        libvirt.VIR_DOMAIN_NOSTATE: "NOSTATE",
        libvirt.VIR_DOMAIN_RUNNING: "RUNNING",
        libvirt.VIR_DOMAIN_BLOCKED: "BLOCKED",
        libvirt.VIR_DOMAIN_PAUSED: "PAUSED",
        libvirt.VIR_DOMAIN_SHUTDOWN: "SHUTDOWN",
        libvirt.VIR_DOMAIN_SHUTOFF: "STOPPED",
        libvirt.VIR_DOMAIN_CRASHED: "CRASHED",
        libvirt.VIR_DOMAIN_PMSUSPENDED: "SUSPENDED",
    }

    def __init__(self, config, description):
        """
        Init method.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
        """
        super().__init__(config, description)
        libvirt.registerErrorHandler(f=libvirt_callback, ctx=None)
        try:
            self.connection = libvirt.open(config.libvirt.uri)
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception

    def _wait_for_agent(self, domain, sleep=5, max_tries = 10):
        """
        Connect to QEMU agent of an machine.

        Parameters:
            domain (LibvirtDomain): Libvirt domain
            sleep (int): number of seconds to wait between retries Default: 5
            max_tries (int): max number of tries. Default: 10
        """
        tries = 1
        agent_ready = False
        while not agent_ready and tries < max_tries:
            try:
                libvirt_qemu.qemuAgentCommand(domain, '{"execute": "guest-ping"}', 10, 0)
                agent_ready = True
            except libvirt.libvirtError:
                tries += 1
                time.sleep(sleep)
        if not agent_ready:
            raise ClientLibvirtException("Cannot connect to QEMU agent.")
        
    def get_machine_status(self, machine_name):
        try:
            domain = self.connection.lookupByName(machine_name)
        except libvirt.libvirtError:
            return "NOT FOUND"
        try:
            state, _ = domain.state()
            return self.STATE_MSG.get(state, "NOT FOUND")
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
        
    def get_machine_private_ip(self, machine_name):
        try:
            domain = self.conn.lookupByName(machine_name)
        except libvirt.libvirtError:
            return None
        try:
            self._wait_for_agent(domain)
            if machine_name in self.description.services_guests.keys():
                return self.description.services_guests[machine_name].service_ip
            else:
                interfaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)
                for interface_name, val in interfaces.items():
                    if interface_name != "lo" and val["addrs"]:
                        for ipaddr in val["addrs"]:
                            if ip_address(ipaddr["addr"]) in ip_network(self.config.network_cidr_block):
                                return ipaddr["addr"]
                return None
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
        
    def get_image_id(self, image_name):
        try:
            pool = self.conn.storagePoolLookupByName(self.config.libvirt_pool_name)
        except libvirt.libvirtError:
            raise ClientLibvirtException(f"Failed to locate {self.config.libvirt_pool_name} storage pool.")
        try:
            vol = pool.storageVolLookupByName(image_name)
            return vol.getName()
        except libvirt.libvirtError:
            return None
                 
    def is_image_in_use(self, image_name):
        try:
            domains = self.conn.listAllDomains()
            for domain in domains:
                xml_desc = domain.XMLDesc()
                root = ET.fromstring(xml_desc)
                for backingStore in root.findall(".//devices/disk/backingStore"): #Check backing stores
                    source = backingStore.find("source")
                    if source is not None:
                        image_path = source.get("file")
                        if image_path is not None:
                            image_used = image_path.split("/")[-1]
                            if image_used == image_name:
                                return True
                for disk in root.findall(".//devices/disk"): #Check disks
                    source = disk.find("source")
                    if source is not None:
                        image_path = source.get("file")
                        if image_path is not None:
                            image_used = image_path.split("/")[-1]
                            if image_used == image_name:
                                return True
                return False
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}")
        
    def delete_image(self, image_name):
        try:
            pool = self.conn.storagePoolLookupByName(self.config.libvirt.storage_pool)
        except libvirt.libvirtError:
            raise ClientLibvirtException(f"Failed to locate {self.config.libvirt.storage_pool} storage pool.")
        vol = None
        try:
            vol = pool.storageVolLookupByName(image_name)
        except libvirt.libvirtError:
            pass
        if vol:
            vol.delete()
        
    def start_machine(self, machine_name):
        try:
            domain = self.conn.lookupByName(machine_name)
        except libvirt.libvirtError:
            raise ClientLibvirtException(f"Domain {machine_name} not found.")
        try:
            state, _ = domain.state()
            if state != libvirt.VIR_DOMAIN_RUNNING:
                domain.create()
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
        
    def stop_machine(self, machine_name):
        try:
            domain = self.conn.lookupByName(machine_name)
        except libvirt.libvirtError:
            raise ClientLibvirtException(f"Domain {machine_name} not found.")
        try:
            state, _ = domain.state()
            if state != libvirt.VIR_DOMAIN_SHUTOFF:
                domain.shutdown()
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
        
    def restart_machine(self, machine_name):
        try:
            domain = self.conn.lookupByName(machine_name)
        except libvirt.libvirtError:
            raise ClientLibvirtException(f"Domain {machine_name} not found.")
        try:
            state, _ = domain.state()
            if state == libvirt.VIR_DOMAIN_RUNNING:
                domain.reboot()
            elif state == libvirt.VIR_DOMAIN_SHUTOFF:
                domain.create()
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
        
    def console(self, machine_name, username):
        """
        Connect to a specific scenario machine.

        Parameters:
            machine_name (str): name of the machine.
            username (str): username to use. Default: None
        """
        hostname = self.get_machine_private_ip(machine_name)
        if not hostname:
            raise ClientLibvirtException(f"Instance {machine_name} not found.")
        interactive_shell(hostname, username)
        