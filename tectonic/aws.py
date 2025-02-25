
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

import json
from pprint import pprint

import boto3
from botocore.config import Config


class AWSClientException(Exception):
    pass


class Client:
    def __init__(self, description, connection=None, secrets_manager=None):
        """
        Initialize AWS client.

        Parameters:
            description (tectonic.description): the scenario description
            connection (boto3.client): boto3 client to use for AWS operations.
        """
        self.description = description
        if connection is not None:
            self.ec2_client = connection
        else:
            self.ec2_client = boto3.client("ec2", region_name=description.aws_region)
        if secrets_manager is not None:
            self.secretsmanager_client = secrets_manager
        else:
            self.secretsmanager_client = boto3.client(
                "secretsmanager", region_name=description.aws_region
            )

    def get_instance_property(self, instance_name, prop):
        """
        Get property of an instance given it's name.

        Parameters:
            instance_name (str): name of the instance (<institution>-<lab_name>-<instance_number>-<guest_name>-<copy>).
            prop (str): property of the instance.

        Returns:
            str: the value of the property for the instance if it is found or None otherwise.
        """
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [instance_name]},
                    # Filter out terminated instances
                    {
                        "Name": "instance-state-name",
                        "Values": [
                            "pending",
                            "running",
                            "shutting-down",
                            "stopping",
                            "stopped",
                        ],
                    },
                ],
                DryRun=False,
            )
            if (
                len(response["Reservations"]) > 0
                and len(response["Reservations"][0]["Instances"]) == 1
            ):
                return response["Reservations"][0]["Instances"][0].get(prop)
            return None
        except Exception as exception:
            raise AWSClientException(f"{exception}") from exception

    def start_instance(self, instance_name):
        """
        Start an instance.

        Parameters:
            instance_name (str): name of the instance (<institution>-<lab_name>-<instance_name>).
        """
        instance_id = self.get_instance_property(instance_name, "InstanceId")
        if instance_id is None:
            raise AWSClientException(f"Instance {instance_name} not found.")
        self.ec2_client.start_instances(InstanceIds=[instance_id], DryRun=False)

    def stop_instance(self, instance_name):
        """
        Stop an instance.

        Parameters:
            instance_name (str): name of the instance (<insitution>-<lab_name>-<instance_name>).
        """
        instance_id = self.get_instance_property(instance_name, "InstanceId")
        if instance_id is None:
            raise AWSClientException(f"Instance {instance_name} not found.")
        self.ec2_client.stop_instances(InstanceIds=[instance_id], DryRun=False)

    def reboot_instance(self, instance_name):
        """
        Reboot an instance.

        Parameters:
            instance_name (str): name of the instance (<institution>-<lab_name>-<instance_name>).
        """
        instance_id = self.get_instance_property(instance_name, "InstanceId")
        if instance_id is None:
            raise AWSClientException(f"Instance {instance_name} not found.")
        self.ec2_client.reboot_instances(InstanceIds=[instance_id], DryRun=False)

    def get_instance_status(self, instance_name):
        """
        Return instance status.

        Parameters:
            instance_name (str): name of the instance (<institution>-<lab_name>-<instance_name>).

        Returns:
            dict(str): dictionary with information about the state of the instance.
        """
        instance_id = self.get_instance_property(instance_name, "InstanceId")
        if instance_id is not None:
            response = self.ec2_client.describe_instance_status(
                InstanceIds=[instance_id], DryRun=False, IncludeAllInstances=True
            )
            return response["InstanceStatuses"][0]["InstanceState"]["Name"].upper()
        else:
            return "NOT FOUND"

    def get_image(self, image_name):
        """
        Get the Id of an image and its snapshot given its name.

        Parameters:
            image_name (str): name of the image (<institution>-<lab_name>-<image_name>).

        Returns:
            tuple(str): the identifier of the image an its snapshot if it was found or None otherwise.
        """
        response = self.ec2_client.describe_images(
            Filters=[{"Name": "tag:Name", "Values": [image_name]}], DryRun=False
        )
        if len(response["Images"]) == 1:
            return (
                response["Images"][0]["ImageId"],
                response["Images"][0]["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"],
            )
        return None

    def delete_image(self, image_name):
        """
        Delete image and its snapshot.

        Parameters:
            image_name (str): name of the image (<institution>-<lab_name>-<image_name>).

        """
        image = self.get_image(image_name)
        if image is not None:
            self.ec2_client.deregister_image(ImageId=image[0], DryRun=False)
            self.ec2_client.delete_snapshot(SnapshotId=image[1], DryRun=False)

    def get_machine_public_ip(self, name):
        """
        Get a machine public IP.

        Parameters:
            name (str): complete name of the machine.

        Returns:
            str: machine public IP if it was found or None otherwise.
        """
        return self.get_instance_property(name, "PublicIpAddress")

    def get_machine_private_ip(self, name):
        """
        Get a machine private IP.

        Parameters:
            name (str): complete name of the machine.

        Returns:
            str : machine private IP if it was found or None otherwise.
        """
        return self.get_instance_property(name, "PrivateIpAddress")

    def get_security_group_id(self, description):
        """
        Get the Id of a security group given its description.

        Parameters:
            description (str): description of the security group.

        Returns:
            list(str): list of the identifiers of the security groups.
        """
        response = self.ec2_client.describe_security_groups(
            Filters=[{"Name": "description", "Values": [description]}],
            DryRun=False,
        )
        ids = []
        for security_group in response["SecurityGroups"]:
            ids.append(security_group["GroupId"])
        return ids

    def delete_security_groups(self, description):
        """
        Delete security groups given its description.

        Parameters:
            description (str): description of the security groups.
        """
        for sg_id in self.get_security_group_id(description):
            self.ec2_client.delete_security_group(
                GroupId=sg_id,
                DryRun=False,
            )

    def get_machines_imageid(self, max_page_results=50):
        """
        Get machines images id.

        Parameters:
            max_page_results (int): The max number of results to query in each request.

        Returns:
            list(str) : machine image ids.
        """
        try:
            first_request = True
            next_token = ""
            images_id = []
            while next_token is not None:
                if first_request:
                    response = self.ec2_client.describe_instances(
                        Filters=[
                            {
                                "Name": "instance-state-name",
                                "Values": [
                                    "pending",
                                    "running",
                                    "shutting-down",
                                    "stopping",
                                    "stopped",
                                ],
                            },
                        ],
                        DryRun=False,
                        MaxResults=max_page_results,
                    )
                else:
                    response = self.ec2_client.describe_instances(
                        Filters=[
                            {
                                "Name": "instance-state-name",
                                "Values": [
                                    "pending",
                                    "running",
                                    "shutting-down",
                                    "stopping",
                                    "stopped",
                                ],
                            },
                        ],
                        DryRun=False,
                        MaxResults=max_page_results,
                        NextToken=next_token,
                    )
                for instance in response["Reservations"]:
                    images_id.append(instance["Instances"][0]["ImageId"])
                next_token = response.get("NextToken", None)
                first_request = False
            return images_id
        except Exception as e:
            raise AWSClientException(f"{e}") from e
        
    def is_image_in_use(self, image_name):
        """
        Returns true if the image is in use for some vm.

        Parameters:
            image_name(str): the image name to check
        """
        try:
            image = self.get_image(image_name)
            if image:
                image_id = image[0]
                instances_images_ids = self.get_machines_imageid()
                if image_id in instances_images_ids:
                    return True
            return False
        except Exception as exception:
            raise AWSClientException(f"{exception}")
