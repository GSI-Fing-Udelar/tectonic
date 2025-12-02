
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

from bs4 import BeautifulSoup
import requests
import re

import tectonic.validate as validate

class TectonicConfigElastic(object):
    """Class to store Tectonic elastic configuration."""

    def __init__(self):
        self.elastic_stack_version = "8.18.0"
        self.packetbeat_policy_name = "Packetbeat"
        self.endpoint_policy_name = "Endpoint"
        self.user_install_packetbeat = "tectonic"
        self._internal_port = 5601
        self._external_port = 5601


    #----------- Getters ----------
    @property
    def elastic_stack_version(self):
        return self._elastic_stack_version

    @property
    def packetbeat_policy_name(self):
        return self._packetbeat_policy_name

    @property
    def endpoint_policy_name(self):
        return self._endpoint_policy_name

    @property
    def user_install_packetbeat(self):
        return self._user_install_packetbeat
    
    @property
    def internal_port(self):
        return self._internal_port
    
    @property
    def external_port(self):
        return self._external_port


    #----------- Setters ----------
    @elastic_stack_version.setter
    def elastic_stack_version(self, value):
        validate.version_number("elastic_stack_version", value)
        if value == "latest":
            value = self._get_elastic_latest_version()
        self._elastic_stack_version = value

    @packetbeat_policy_name.setter
    def packetbeat_policy_name(self, value):
        self._packetbeat_policy_name = value

    @endpoint_policy_name.setter
    def endpoint_policy_name(self, value):
        self._endpoint_policy_name = value

    @user_install_packetbeat.setter
    def user_install_packetbeat(self, value):
        self._user_install_packetbeat = value

    def _get_elastic_latest_version(self):
        """
        Return latest version of elastic stack available

        Returns:
          str: elastic stack version
        """
        elastic_url = 'https://www.elastic.co/guide/en/elasticsearch/reference/8.18/es-release-notes.html'
        html_text = requests.get(elastic_url).text
        soup = BeautifulSoup(html_text, 'html.parser')
        versions = soup.find_all('a', attrs={"title": re.compile("Elasticsearch version \\d+\\.\\d+\\.\\d+")})
        latest_version = versions[0].get("title").split(" ")[2]
        return latest_version
    
    @internal_port.setter
    def internal_port(self, value):
        validate.number("Elastic internal port", value)
        self._internal_port = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Elastic external port", value)
        self._external_port = value
