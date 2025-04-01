
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

from urllib.parse import urlparse
import ipaddress
from pathlib import Path
import re


def supported_value(name, value, supported_values, case_sensitive=True):
    """Validates that the value named name is one of the supported_values. 
    
    If case_sensitive is false, checks string equality case insentively.
    """
    if ((case_sensitive and value not in supported_values) or
        (not case_sensitive and value.lower() not in [x.lower() for x in supported_values])
        ):
        raise ValueError(f"Invalid {name} {value}. Must be one of {supported_values}.")

def regex(name, value, pattern, case_sensitive=True):
    """Validates that the value named name matches the given regex"""
    if case_sensitive:
        flag = 0
    else:
        flag = re.IGNORECASE
    if not re.match(pattern, value, flag):
        raise ValueError(f"Invalid {name} {value}. Must match the regular expression {pattern}.")

def boolean(name, value):
    """Validates that the value named name is boolean."""
    if not isinstance(value, bool):
        raise ValueError(f"Invalid {name} {value}. Must be a boolean value.")

def number(name, value, min_value=None, max_value=None):
    try:
        value = int(value)
        if min_value is not None and value < min_value:
            raise ValueError()
        if max_value is not None and value > max_value:
            raise ValueError()
    except ValueError:
        error_msg = f"Invalid {name} {value}. Must be a number"
        if min_value:
            if max_value:
                error_msg += f" between {min_value} and {max_value}"
            else:
                error_msg += f" greater than {min_value}"
        elif max_value:
            error_msg += f" less than {max_value}"
        error_msg += "."
        raise ValueError(error_msg)

def version_number(name, value, allow_latest=True):
    rx = r"(\d+.)*\d+"
    try:
        if allow_latest:
            rx = r"^(latest|" + rx + r")$"
        else:
            rx = r"^" + rx + r"$"
        if not re.match(rx, value):
            raise ValueError()
    except:
        msg = f"Invalid {name} {value}. Must be a valid version number"
        if allow_latest:
            msg += " or 'latest'"
        msg += "."
        raise ValueError(msg)

def path_to_file(name, value):
    """Validates that the value named name is a valid path to a file.
    """
    try:
        if not Path(value).is_file():
            raise ValueError()
    except:
        raise ValueError(f"Invalid {name} {value}. Must be a path to a file.")

def path_to_dir(name, value, base_dir="/", expand_user=True):
    """Validates that the value named name is a valid path to a file.

    Concat to base_dir if value is a relative path. Expands ~/ to
    the current user homedir if expand_user is True.
    """
    try:
        if not Path(value).is_dir():
            raise ValueError()
    except:
        raise ValueError(f"Invalid {name} {value}. Must be a path to a directory.")
    
def url(name, value):
    """Validates that the value named name is a valid url with at least scheme and host."""
    try:
        result = urlparse(value)
        if not all([result.scheme, result.netloc]):
            raise ValueError
    except:
        raise ValueError(f"Invalid {name} {value}. Must be a valid url.")

def ip_address(name, value):
    """Validates that the value named name is a valid IP network"""
    try:
        if not isinstance(value, str):
            raise ValueError
        ipaddress.ip_address(value)
    except ValueError:
        raise ValueError(f"Invalid {name} {value}. Must be a valid IP address.")


def ip_network(name, value):
    """Validates that the value named name is a valid IP network"""
    try:
        if not isinstance(value, str):
            raise ValueError
        network = ipaddress.ip_network(value)
        if ((network.version == 4 and network.prefixlen == 32) or
            (network.version == 6 and network.prefixlen == 128)):
            raise ValueError
    except:
        raise ValueError(f"Invalid {name} {value}. Must be a valid IP network.")
    

def hostname(name, value):
    """Validates that the value named name is a hostname."""
    try:
        if value[-1] == ".":
            # strip exactly one dot from the right, if present
            value = value[:-1]
        if len(value) > 253:
            raise ValueError()
        labels = value.split(".")

        # the TLD must be not all-numeric
        if re.match(r"[0-9]+$", labels[-1]):
            raise ValueError()
        allowed = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
        if not all(allowed.match(label) for label in labels):
            raise ValueError()
    except:
        raise ValueError(f"Invalid {name} {value}. Must be a valid hostname.")
    

def ip_address_or_hostname(name, value):
    """Validates that the value named name is a hostname or IP address."""
    try:
        ip_address(name, value)
    except:
        try:
            hostname(name, value)
        except:
            raise ValueError(f"Invalid {name} {value}. Must be a valid hostname or IP address.")
    
