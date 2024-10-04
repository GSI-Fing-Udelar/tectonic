
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

import socket

import pytest


from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS

def test_instance_type():
    instance_type = InstanceType()
    assert instance_type.get_guest_instance_type(1024, 1, False, False, "traffic") is None

    instance_type = InstanceType("some_instance_type")
    assert instance_type.get_guest_instance_type(1024, 1, False, False, "traffic") == "some_instance_type"

def test_instance_type_aws():
    instance_type = InstanceTypeAWS("t2.micro")
    assert instance_type.get_guest_instance_type(None, 2, False, False, "traffic") == "t2.medium"
    assert instance_type.get_guest_instance_type(1024, 2, False, True, "traffic") == "t3.micro"
    assert instance_type.get_guest_instance_type(1024, 2, False, True, "endpoint") == "t2.medium"
    assert instance_type.get_guest_instance_type(None, None, False, False, "traffic") == "t2.micro"
    assert instance_type.get_guest_instance_type(None, None, False, True, "traffic") == "t3.micro"
    assert instance_type.get_guest_instance_type(None, None, False, True, "endpoint") == "t2.micro"
    assert instance_type.get_guest_instance_type(50000, None, False, False, "traffic") == "t2.2xlarge"
    
    assert instance_type.get_guest_instance_type(1024, 2, True, True, "endpoint") == "g4dn.xlarge"
