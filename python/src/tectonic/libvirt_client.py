
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
import time
from ipaddress import ip_network, ip_address

class LibvirtClientException(Exception):
    pass


# Avoid console output.
# See https://stackoverflow.com/questions/45541725/avoiding-console-prints-by-libvirt-qemu-python-apis
def libvirt_callback(userdata, err):
    pass


class Client:
    """Class for managing libvirt connections."""
    STATES_MSG = {
        libvirt.VIR_DOMAIN_NOSTATE: "NOSTATE",
        libvirt.VIR_DOMAIN_RUNNING: "RUNNING",
        libvirt.VIR_DOMAIN_BLOCKED: "BLOCKED",
        libvirt.VIR_DOMAIN_PAUSED: "PAUSED",
        libvirt.VIR_DOMAIN_SHUTDOWN: "SHUTDOWN",
        libvirt.VIR_DOMAIN_SHUTOFF: "SHUTOFF",
        libvirt.VIR_DOMAIN_CRASHED: "CRASHED",
        libvirt.VIR_DOMAIN_PMSUSPENDED: "SUSPENDED",
    }

    def __init__(self, description):
        self.description = description
        self.uri = description.libvirt_uri
        libvirt.registerErrorHandler(f=libvirt_callback, ctx=None)
        try:
            self.conn = libvirt.open(self.uri)
        except:
            self.conn = None
            raise LibvirtClientException(f"Cannot connect to libvirt server at {self.uri}")

    def __del__(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except:
                pass

    def wait_for_agent(self, domain, sleep=5, max_tries = 10):
        tries = 1
        agent_ready = False
        while not agent_ready and tries < max_tries:
            try:
                libvirt_qemu.qemuAgentCommand(
                    domain, '{"execute": "guest-ping"}', 10, 0
                )
                agent_ready = True
            except libvirt.libvirtError:
                tries += 1
                time.sleep(sleep)

        if not agent_ready:
            raise LibvirtClientException("Cannot connect to QEMU agent.")

    def get_machine_private_ip(self, name):
        """Returns the private IP address of a domain.

           If the domain has more than one IP address, the first
           address inside network_cidr_block is returned.

        """
        try:
            domain = self.conn.lookupByName(name)
        except libvirt.libvirtError:
            return None
        self.wait_for_agent(domain)

        lab_network = ip_network(self.description.network_cidr_block)
        services_network = ip_network(self.description.services_network)
        services_list = []
        for service in self.description.get_services_to_deploy():
            services_list.append(self.description.get_service_name(service))
        interfaces = domain.interfaceAddresses(
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0
        )
        
        for interface_name, val in interfaces.items():
            if interface_name != "lo" and val["addrs"]:
                for ipaddr in val["addrs"]:
                    if name in services_list:
                        if ip_address(ipaddr["addr"]) in services_network:
                            return ipaddr["addr"]
                    else:
                        if ip_address(ipaddr["addr"]) in lab_network:
                            return ipaddr["addr"]
        return None

    def get_machine_public_ip(self, name):
        """
        Get a machine public IP

        Parameters:
            name (string): complete name of the machine

        Returns:
            None: this method is not implemented for libvirt
        """
        return None



    def delete_image(self, pool_name, image_name):
        try:
            pool = self.conn.storagePoolLookupByName(pool_name)
        except libvirt.libvirtError:
            raise LibvirtClientException(f"Failed to locate {pool_name} storage pool.")

        vol = None
        try:
            vol = pool.storageVolLookupByName(image_name)
        except libvirt.libvirtError:
            pass
        if vol:
            vol.delete()

    def get_instance_status(self, instance_name):
        try:
            dom = self.conn.lookupByName(instance_name)
        except libvirt.libvirtError:
            return "NOT FOUND"

        state, _ = dom.state()
        return self.STATES_MSG.get(state, "UNKNOWN")

    def start_instance(self, instance_name):
        """Starts a stopped instance."""
        try:
            dom = self.conn.lookupByName(instance_name)
        except libvirt.libvirtError as e:
            raise LibvirtClientException(f"Domain {instance_name} not found.")

        state, _ = dom.state()
        if state != libvirt.VIR_DOMAIN_RUNNING:
            dom.create()

    def stop_instance(self, instance_name):
        """Stops a running instance."""
        try:
            dom = self.conn.lookupByName(instance_name)
        except libvirt.libvirtError as e:
            raise LibvirtClientException(f"Domain {instance_name} not found.")
        state, _ = dom.state()
        if state != libvirt.VIR_DOMAIN_SHUTOFF:
            dom.shutdown()

    def reboot_instance(self, instance_name):
        """Reboots a running instance."""
        try:
            dom = self.conn.lookupByName(instance_name)
        except libvirt.libvirtError as e:
            raise LibvirtClientException(f"Domain {instance_name} not found.")

        state, _ = dom.state()
        if state == libvirt.VIR_DOMAIN_RUNNING:
            dom.reboot()
        elif state == libvirt.VIR_DOMAIN_SHUTOFF:
            dom.create()       
