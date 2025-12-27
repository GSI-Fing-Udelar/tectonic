
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

import subprocess
import re
import fabric
from paramiko import proxy
import logging

def ssh_version(path="/usr/bin/ssh"):
    """
    Return ssh client version.

    Parameters:
        path (str): path to ssh client binary.

    Returns:
        int: ssh client version.
    """
    try:
        p = subprocess.run([path, "-V"], check=False, capture_output=True)
        m = re.search(r"^OpenSSH_(\d+).\d+[^,]*,", p.stderr.decode())
        if m:
            return int(m.group(1))
        else:
            return None
    except FileNotFoundError:
        return None


def interactive_shell(
    hostname,
    username,
    gateway=None,
):
    """
    Interactively connects to a host.

    Parameters:
        hostname (str): The name target host to connect to.
        username (str): The user on the target host to use for the connection.
        gateway (str, [tuple], None):  Can be a string to use as proxy, or a list of tuples of the form: (proxy_hostname, proxy_user), or None.
    """
    gateway_connection = None
    if isinstance(gateway, str):
        gateway_connection = gateway
    elif isinstance(gateway, list):
        if len(gateway) == 2:
            gateway_connection_jump = fabric.Connection(host=gateway[0][0], user=gateway[0][1])
            gateway_connection = fabric.Connection(host=gateway[1][0], user=gateway[1][1], gateway=gateway_connection_jump)
        elif len(gateway) == 1:
            gateway_connection = fabric.Connection(host=gateway[0][0], user=gateway[0][1])
        
    connection = fabric.Connection(host=hostname, user=username, gateway=gateway_connection)
    connection.shell()