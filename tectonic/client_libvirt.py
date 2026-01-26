
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

from tectonic.client import Client, ClientException
from tectonic.ssh import interactive_shell

import libvirt
import libvirt_qemu
import time
from ipaddress import ip_network, ip_address
import xml.etree.ElementTree as ET
import uuid

class ClientLibvirtException(ClientException):
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
            domain = self.connection.lookupByName(machine_name)
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
                            if ip_address(ipaddr["addr"]) in ip_network(self.config.network_cidr_block) and not ip_address(ipaddr["addr"]) in ip_network(self.config.services_network_cidr_block):
                                return ipaddr["addr"]
                return None
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
        
    def get_machine_ip_in_services_network(self, machine_name):
        try:
            domain = self.connection.lookupByName(machine_name)
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
                            if ip_address(ipaddr["addr"]) in ip_network(self.config.services_network_cidr_block):
                                return ipaddr["addr"]
                return None
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception
                 
    def is_image_in_use(self, image_name):
        try:
            domains = self.connection.listAllDomains()
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
            if self.is_image_in_use(image_name):
                raise ClientLibvirtException(f"Error deleting image {image_name}: in use")
            pool = self.connection.storagePoolLookupByName(self.config.libvirt.storage_pool)
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
            domain = self.connection.lookupByName(machine_name)
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
            domain = self.connection.lookupByName(machine_name)
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
            domain = self.connection.lookupByName(machine_name)
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

    def _add_rule_to_nwfilter(self, parent, protocol, src_cidr, dest_ip, from_port, to_port, priority, direction, action, state):
        rule_elem = ET.SubElement(parent, "rule")
        rule_elem.set("direction", direction)
        rule_elem.set("priority", str(priority))
        rule_elem.set("action", action)
        traffic_elem = ET.SubElement(rule_elem, protocol)
        if state != None:
            traffic_elem.set("state", state)
        if protocol in ["tcp", "udp"]:
            traffic_elem.set("dstportstart", from_port)
            traffic_elem.set("dstportend", to_port)
        if direction == "in":
            if src_cidr != None:
                traffic_elem.set("srcipaddr", src_cidr.split("/")[0])
                traffic_elem.set("srcipmask", src_cidr.split("/")[1])
            if dest_ip != None:
                traffic_elem.set("dstipaddr", dest_ip)
                traffic_elem.set("dstipmask", "32")

    def create_nwfilter(self, nwfilter_name, interface_ip, rules):
        try:
            root = ET.Element('filter', name=nwfilter_name, chain='root')
            ET.SubElement(root, 'uuid').text = str(uuid.uuid5(uuid.NAMESPACE_URL, nwfilter_name))
            filterref_elem = ET.SubElement(root, "filterref")
            filterref_elem.set("filter", "qemu-announce-self") #Necessary to assign IP address to vms
            self._add_rule_to_nwfilter(root, "all", None, None, None, None, 100, "out", "accept", None) #Allow all outbound traffic
            priority = 500
            # Inblund rules
            for rule in rules:
                self._add_rule_to_nwfilter(root, rule.protocol, rule.source_cidr, interface_ip, rule.from_port, rule.to_port, priority, "in", "accept", None)
                priority = priority + 1
            self._add_rule_to_nwfilter(root, "all", None, None, None, None, 1000, "in", "drop", None) #Drop all other inbound traffic
            self.connection.nwfilterDefineXML(ET.tostring(root, encoding='unicode'))
        except Exception as exception:
            raise ClientLibvirtException(f"{exception}") from exception

    def destroy_nwfilter(self, nwfilter_name):
        try:
            nwfilter = self.connection.nwfilterLookupByName(nwfilter_name)
            nwfilter.undefine()
        except Exception as exception:
            if "Network filter not found" not in str(exception):
                raise ClientLibvirtException(f"{exception}") from exception
        
