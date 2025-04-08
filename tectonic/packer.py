
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

import packerpy

class PackerException(Exception):
    pass

class Packer:
    """
    Packer class.

    Description: manages interaction with Packer to build images.
    """

    def __init__(self, config, description, client):
        """
        Initialize the packer object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object
        """
        self.config = config
        self.description = description
        self.client = client

    def create_image(self, packer_module, variables):
        """
        Create images using Packer.

        Parameters:
            packer_module (str): path to the Packer module.
            variables (dict): variables of the Packer module.
        """
        p = packerpy.PackerExecutable(executable_path=self.config.packer_executable_path)
        return_code, stdout, _ = p.execute_cmd("init", str(packer_module))
        if return_code != 0:
            raise PackerException(f"Packer init returned an error:\n{stdout.decode()}")
        return_code, stdout, _ = p.build(str(packer_module), var=variables)
        if return_code != 0:
            raise PackerException(f"Packer build returned an error:\n{stdout.decode()}")

    def destroy_image(self, names):
        """
        Destroy base images.

        Parameters:
            name (list(str)): names of the machines for which to destroy images.
        """
        for guest_name in names:
            image_name = self.description.get_image_name(guest_name)
            if self.client.is_image_in_use(image_name):
                raise PackerException(f"Unable to delete image {image_name} because it is being used.")
        for guest_name in names:
            self.client.delete_image(self.description.get_image_name(guest_name))
