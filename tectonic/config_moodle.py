
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

import tectonic.validate as validate

class TectonicConfigMoodle(object):
    """Class to store Tectonic Moodle configuration."""

    def __init__(self):
        self.version = "5.1.1"
        self.internal_port = 443
        self.external_port = 8080
        self.site_fullname = "Tectonic Moodle"
        self.site_shortname = "Tectonic"
        self.admin_email = "admin@tectonic.local"

    @property
    def version(self):
        return self._version
    
    @property
    def internal_port(self):
        return self._internal_port
    
    @property
    def external_port(self):
        return self._external_port
    
    @property
    def site_fullname(self):
        return self._site_fullname
    
    @property
    def site_shortname(self):
        return self._site_shortname
    
    @property
    def admin_email(self):
        return self._admin_email
    
    @version.setter
    def version(self, value):
        if value != 'latest':
            validate.version_number("moodle version", value)
            value = f"v{value}"
        if value == "latest":
            value = "main"
        self._version = value

    @internal_port.setter
    def internal_port(self, value):
        validate.number("Moodle internal port", value)
        self._internal_port = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Moodle external port", value)
        self._external_port = value
    
    @site_fullname.setter
    def site_fullname(self, value):
        self._site_fullname = value
    
    @site_shortname.setter
    def site_shortname(self, value):
        self._site_shortname = value
    
    @admin_email.setter
    def admin_email(self, value):
        self._admin_email = value

    def to_dict(self):
        return {
            "version": self.version,
            "internal_port": self.internal_port,
            "external_port": self.external_port,
            "site_fullname": self.site_fullname,
            "site_shortname": self.site_shortname,
            "admin_email": self.admin_email,
        }
