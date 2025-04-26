
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

from tectonic.client import Client
from tectonic.ssh import interactive_shell
from tectonic.constants import OS_DATA

import boto3

class ClientAWSException(Exception):
    pass

class ClientAWS(Client):
    """
    ClientAWS class.

    Description: Implement Client for AWS.
    """
    INSTANCE_STATE_NAME_FILTER = {
        "Name": "machine-state-name",
        "Values": [
            "pending",
            "running",
            "shutting-down",
            "stopping",
            "stopped",
        ],
    }
    STATE_MSG = {
        "pending": "PENDING",
        "running": "RUNNING",
        "shutting-down": "SHUTTING DOWN",
        "stopping": "STOPPING",
        "stopped": "STOPPED",
        "terminated": "NOT FOUND",
    }
    EIC_ENDPOINT_SSH_PROXY = "aws ec2-instance-connect open-tunnel --instance-id %h"

    def __init__(self, config, description):
        """
        Init method.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
        """
        super().__init__(config, description)
        try:
            self.connection = boto3.client("ec2", config.aws.region)
        except Exception as exception:
            raise ClientAWSException(f"{exception}")

    def _get_machine_property(self, machine_name, property):
        """
        Return a property of an machine.

        Parameters:
            machine_name (str): name of the machine.
            property (str): name of the property.

        Return:
            str: property og the machine.
        """
        try:
            response = self.connection.describe_machines(
                Filters=[
                    {"Name": "tag:Name", "Values": [machine_name]},
                    self.INSTANCE_STATE_NAME_FILTER,
                ],
                DryRun=False,
            )
            if (len(response["Reservations"]) > 0 and len(response["Reservations"][0]["Instances"]) == 1):
                return response["Reservations"][0]["Instances"][0].get(property)
            else:
                return None
        except Exception as exception:
            raise ClientAWSException(f"{exception}") 

    def _get_image_snapshots(self, image_name):
        """
        Return snapshot image identifier for an image.

        Parameters:
            image_name (str): name of the image.

        Returns:
            str: the identifier of the snapshot if it was found or None otherwise.
        """
        try:
            response = self.connection.describe_images(Filters=[{"Name": "tag:Name", "Values": [image_name]}], DryRun=False)
            if len(response["Images"]) == 1:
                return response["Images"][0]["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]
            else:
                return None
        except Exception as exception:
            raise ClientAWSException(f"{exception}")  

    def _delete_security_groups(self, description):
        """
        Delete security groups given a description.

        Parameters:
            description (str): description of the security groups to delete.
        """
        try:
            response = self.connection.describe_security_groups(Filters=[{"Name": "description", "Values": [description]}], DryRun=False)
            for security_group in response["SecurityGroups"]:
                self.connection.delete_security_group(GroupId=security_group["GroupId"], DryRun=False)   
        except Exception as exception:
            raise ClientAWSException(f"{exception}")  
        
    def get_machine_status(self, machine_name):
        try:
            machine_id = self._get_machine_property(machine_name, "InstanceId")
            if machine_id is not None:
                response = self.connection.describe_machine_status(InstanceIds=[machine_id], DryRun=False, IncludeAllInstances=True)
                return self.STATE_MSG.get(response["InstanceStatuses"][0]["InstanceState"]["Name"], "NOT FOUND")
            else:
                return "NOT FOUND"
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def get_machine_private_ip(self, machine_name):
        try:
            return self._get_machine_property(machine_name, "PrivateIpAddress")
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def get_machine_public_ip(self, name):
        try:
            return self._get_machine_property(name, "PublicIpAddress")
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def get_image_id(self, image_name):
        try:
            response = self.connection.describe_images(Filters=[{"Name": "tag:Name", "Values": [image_name]}], DryRun=False)
            if len(response["Images"]) == 1:
                return response["Images"][0]["ImageId"]
            else:
                return None
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
                 
    def is_image_in_use(self, image_name):
        try:
            image_id = self.get_image(image_name)
            first_request = True
            next_token = ""
            while next_token is not None:
                if first_request:
                    response = self.connection.describe_machines(Filters=[self.INSTANCE_STATE_NAME_FILTER], DryRun=False, MaxResults=50)
                else:
                    response = self.connection.describe_machines(Filters=[self.INSTANCE_STATE_NAME_FILTER], DryRun=False, MaxResults=50, NextToken=next_token)
                next_token = response.get("NextToken", None)
                first_request = False
                if image_id in response["Reservations"]:
                    return True
            return False
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def delete_image(self, image_name):
        try:
            image_id = self.get_image(image_name)
            snapshot_id = self._get_image_snapshots(image_name)
            if image_id is not None:
                self.connection.deregister_image(ImageId=image_id, DryRun=False)
            if snapshot_id is not None:
                self.connection.delete_snapshot(SnapshotId=snapshot_id, DryRun=False)
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def start_machine(self, machine_name):
        try:
            machine_id = self.get_machine_property(machine_name, "InstanceId")
            if machine_id is None:
                raise ClientAWSException(f"Instance {machine_name} not found.")
            self.connection.start_machines(InstanceIds=[machine_id], DryRun=False)
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def stop_machine(self, machine_name):
        try:
            machine_id = self.get_machine_property(machine_name, "InstanceId")
            if machine_id is None:
                raise ClientAWSException(f"Instance {machine_name} not found.")
            self.connection.stop_machines(InstanceIds=[machine_id], DryRun=False)
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def restart_machine(self, machine_name):
        try:
            machine_id = self.get_machine_property(machine_name, "InstanceId")
            if machine_id is None:
                raise ClientAWSException(f"Instance {machine_name} not found.")
            self.connection.reboot_machines(InstanceIds=[machine_id], DryRun=False)
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def get_machine_id(self, machine_name):
        """
        Return machine identifier.

        Parameters:
            macine_name (str): name of the machine.

        Returns:
            str: machine identifier.
        """
        try:
            return self.get_machine_property(machine_name, "InstanceId")
        except Exception as exception:
            raise ClientAWSException(f"{exception}")
        
    def console(self, machine_name, username):
        """
        Connect to a specific scenario machine.

        Parameters:
            machine_name (str): name of the machine.
            username (str): username to use. Default: None
        """
        if machine_name == self.description.get_teacher_access_name():
            interactive_shell(self._get_teacher_access_ip(), self._get_teacher_access_username())
        else:
            hostname = self.get_ssh_hostname(machine_name)
            username = username or self.description.get_guest_username(self.description.get_base_name(machine_name))
            if self.description.teacher_access == "host":
                gateway = (self._get_teacher_access_ip(), self._get_teacher_access_username())
            else:
                gateway = self.EIC_ENDPOINT_SSH_PROXY
            if not hostname:
                raise ClientAWSException(f"Instance {machine_name} not found.")
            interactive_shell(hostname, username, gateway)

    def get_ssh_proxy_command(self):
        """
        Returns the appropriate SSH proxy configuration to access guest machines.

        Return:
            str: ssh proxy command to use.
        """
        if self.description.teacher_access == "endpoint":
            proxy_command = self.EIC_ENDPOINT_SSH_PROXY
        else:
            access_ip = self._get_teacher_access_ip()
            username = self._get_teacher_access_username()
            connection_string = f"{username}@{access_ip}"
            proxy_command = f"ssh {self.description.ansible_ssh_common_args} -W %h:%p {connection_string}"
        return proxy_command
    
    def get_ssh_hostname(self, machine):
        """
        Returns the hostname to use for ssh connection to the machine.

        Parameters:
            machine (str): machine name.

        Return:
            str: ssh hostname to use.
        """
        if self.description.teacher_access == "endpoint":
            return self._get_machine_property(machine, "InstanceId")
        else:
            return self.get_machine_private_ip(machine)
        
    def _get_teacher_access_username(self):
        """
        Returns username for connection to teacher access host.

        Return:
            str: username to use.
        """
        return OS_DATA[self.description.default_os]["username"]
    
    def _get_teacher_access_ip(self):
        """
        Returns the public IP assigned to the teacher access host.

        Return:
            str: public IP for teacher access.
        """
        if self.description.teacher_access == "host":
            return self.get_machine_public_ip(self.description.get_teacher_access_name())
        return None