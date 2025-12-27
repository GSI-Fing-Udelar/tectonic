
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

import invoke
import fabric.testing.fixtures

from tectonic.ssh import ssh_version, interactive_shell


def test_ssh_version():
    version = ssh_version("/usr/bin/ssh")
    assert version is not None
    assert isinstance(version, int)
    assert version >= 0


def test_not_found_ssh_version():
    version = ssh_version("/usr/bin/ssh-not-found")
    assert version is None

def test_wrong_ssh_version():
    version = ssh_version("/usr/bin/true")
    assert version is None


def test_interactive_shell_no_gateway(monkeypatch):
    def fabric_shell(connection, **kwargs):
        """ Mocks fabric.Connection.shell()."""
        assert connection.original_host == "localhost"
        assert connection.user == "root"
        assert connection.gateway is None
    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    interactive_shell("localhost", "root")

def test_interactive_shell_gateway(monkeypatch):
    def fabric_shell(connection, **kwargs):
        """ Mocks fabric.Connection.shell()."""
        assert connection.original_host == "localhost"
        assert connection.user == "root"
        assert connection.gateway == "bastion"
    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    interactive_shell("localhost", "root", "bastion")

def test_interactive_shell_gateway_and_user(monkeypatch):
    def fabric_shell(connection, **kwargs):
        """ Mocks fabric.Connection.shell()."""
        assert connection.original_host == "localhost"
        assert connection.user == "root"
        assert isinstance(connection.gateway, fabric.Connection)
        assert connection.gateway.original_host == "bastion"
        assert connection.gateway.user == "ubuntu"

        return invoke.runners.Result()

    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    interactive_shell("localhost", "root", [("bastion", "ubuntu")])