
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

import pytest
from pathlib import Path

from tectonic.validate import *
import re

def test_supported_value():
    test_data = ["data1", "data2", "data3"]

    supported_value("test", "data3", test_data)
    supported_value("test", "DATA2", test_data, case_sensitive=False)

    with pytest.raises(ValueError) as exception:
        supported_value("test", "data4", test_data)
    with pytest.raises(ValueError) as exception:
        supported_value("test", "DATA3", test_data)

def test_regex():
    regex("test", "aaabbb", r"^a+b+$")
    regex("test", "AaabbbBBB", r"^a+b+$", case_sensitive=False)
    with pytest.raises(ValueError) as exception:
        regex("test", "AaabbbBBB", r"^a+b+$")
    with pytest.raises(ValueError) as exception:
        regex("test", "abcdedcba", r"^[abcd]+$")

def test_boolean():
    boolean("test", True)
    with pytest.raises(ValueError) as exception:
        boolean("test", "error")

def test_number():
    number("test", 2)
    number("test", 3, min_value=2)
    number("test", 30, max_value=50)
    number("test", 3, min_value=1, max_value=5)

    
    with pytest.raises(ValueError) as exception:
        number("test", -1, min_value=1, max_value=5)
    with pytest.raises(ValueError) as exception:
        number("test", 6, max_value=5)
    with pytest.raises(ValueError) as exception:
        number("test", 1, min_value=2)
    with pytest.raises(ValueError) as exception:
        number("test", "error")


def test_version_number():
    version_number("test", "2")
    version_number("test", "2.0.2")
    version_number("test", "2.0.2.3.1.3.34", allow_latest=False)
    version_number("test", "latest")

    
    with pytest.raises(ValueError) as exception:
        version_number("test", True)
    with pytest.raises(ValueError) as exception:
        version_number("test", "invalidversion-number")
    with pytest.raises(ValueError) as exception:
        version_number("test", "latest", allow_latest=False)

def test_path_to_file(test_data_path):
    path_to_file("test", str(Path(test_data_path).joinpath("labs/test.ctf")))
    with pytest.raises(ValueError) as exception:
        path_to_file("test", str(Path(test_data_path).joinpath("labs/invalid.ctf")))
    with pytest.raises(ValueError) as exception:
        path_to_file("test", test_data_path)
    with pytest.raises(ValueError) as exception:
        path_to_file("test", False)

def test_path_to_dir(test_data_path):
    path_to_dir("test", test_data_path)

    with pytest.raises(ValueError) as exception:
        path_to_dir("test", str(Path(test_data_path).joinpath("invalid")))
    with pytest.raises(ValueError) as exception:
        path_to_dir("test", str(Path(test_data_path).joinpath("labs/test.ctf")))
    with pytest.raises(ValueError) as exception:
        path_to_dir("test", False)

    
def test_url():
    url("test", "http://example.com")
    url("test", "https://user@example.com:8080")

    with pytest.raises(ValueError) as exception:
        url("test", "http::::")
    with pytest.raises(ValueError) as exception:
        url("test", False)


def test_ip_address():
    ip_address("test", "127.0.0.1")
    ip_address("test", "2001:0db8:85a3:0000:0000:8a2e:0370:7334")

    with pytest.raises(ValueError) as exception:
        ip_address("test", "1.2.3.4.5.")
    with pytest.raises(ValueError) as exception:
        ip_address("test", "")
    with pytest.raises(ValueError) as exception:
        ip_address("test", False)



def test_ip_network():
    ip_network("test", "164.73.32.0/25")
    ip_network("test", "2001:0db8:1234:5678::/64")

    with pytest.raises(ValueError) as exception:
        ip_network("test", "127.0.0.1")
    with pytest.raises(ValueError) as exception:
        ip_network("test", "2001:0db8:85a3:0000:0000:8a2e:0370:7334")
    with pytest.raises(ValueError) as exception:
        ip_network("test", "")
    with pytest.raises(ValueError) as exception:
        ip_network("test", False)

def test_hostname():
    hostname("test", "dns.google.")
    hostname("test", "WWW.EXAMPLE.COM")

    with pytest.raises(ValueError) as exception:
        hostname("test", "dns.google."*100)
    with pytest.raises(ValueError) as exception:
        hostname("test", "8.8.8.8")
    with pytest.raises(ValueError) as exception:
        hostname("test", "www.example.com:8080")
    with pytest.raises(ValueError) as exception:
        hostname("test", "http://example.com")
    with pytest.raises(ValueError) as exception:
        hostname("test", "")
    with pytest.raises(ValueError) as exception:
        hostname("test", False)
    

def test_ip_address_or_hostname():
    ip_address_or_hostname("test", "8.8.8.8")
    ip_address_or_hostname("test", "www.example.com")

    with pytest.raises(ValueError) as exception:
        ip_address_or_hostname("test", "www.example.com:8080")
    with pytest.raises(ValueError) as exception:
        ip_address_or_hostname("test", "http://example.com")
    with pytest.raises(ValueError) as exception:
        ip_address_or_hostname("test", "")
    with pytest.raises(ValueError) as exception:
        ip_address_or_hostname("test", False)
    
