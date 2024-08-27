
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


from tectonic.aws import Client, AWSClientException

def test_constructor(description, ec2_client, aws_secrets):
    c = Client(description=description, connection=ec2_client, secrets_manager=aws_secrets)
    assert c.ec2_client == ec2_client

    Client(description)


def test_get_instance_property(mocker, aws_client, aws_instance_name):

    instances = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}]
    )["Reservations"][0]["Instances"]
    assert len(instances) == 1

    image_id = instances[0]["ImageId"]

    example_property = aws_client.get_instance_property(
        instance_name=aws_instance_name,
        prop="ImageId"
    )
    assert example_property == image_id

    example_property = aws_client.get_instance_property(
        instance_name="notfound",
        prop="ImageId"
    )
    assert example_property is None

    # Make the call to the aws api fail
    mocker.patch.object(aws_client.ec2_client, "describe_instances", side_effect=Exception("Connection refused"))
    with pytest.raises(AWSClientException):
        example_property = aws_client.get_instance_property("test", "invalid")


def test_start_instance_not_found(aws_client, unexpected_instance_name):
    with pytest.raises(AWSClientException) as exception:
        aws_client.start_instance(instance_name=unexpected_instance_name)
    assert f"Instance {unexpected_instance_name} not found" in str(exception.value)

def test_start_existing_instance(aws_client, aws_instance_name):
    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}])["Reservations"][0][
        "Instances"][0]

    assert instance["State"]["Name"] == "stopped"

    aws_client.start_instance(instance_name=aws_instance_name)

    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}])["Reservations"][0][
        "Instances"][0]
    assert instance["State"]["Name"] == "running"
    # Restore instance status
    aws_client.stop_instance(instance_name=aws_instance_name)

def test_stop_instance_not_found(aws_client, unexpected_instance_name):
    with pytest.raises(AWSClientException) as exception:
        aws_client.stop_instance(instance_name=unexpected_instance_name)
    assert f"Instance {unexpected_instance_name} not found" in str(exception.value)


def test_stop_existing_instance(aws_client, aws_instance_name):
    
    aws_client.stop_instance(instance_name=aws_instance_name)
    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}]
    )["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "stopped"


def test_reboot_instance_not_found(aws_client, unexpected_instance_name):
    with pytest.raises(AWSClientException) as exception:
        aws_client.reboot_instance(instance_name=unexpected_instance_name)
    assert f"Instance {unexpected_instance_name} not found" in str(exception.value)


def test_reboot_existing_instance(aws_client, aws_instance_name):

    aws_client.start_instance(instance_name=aws_instance_name)
    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}])["Reservations"][0][
        "Instances"][0]
    assert instance["State"]["Name"] == "running"
    aws_client.reboot_instance(instance_name=aws_instance_name)
    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}])["Reservations"][0][
        "Instances"][0]
    assert instance["State"]["Name"] == "running"
    # Restore instance status
    aws_client.stop_instance(instance_name=aws_instance_name)


def test_get_instance_status(aws_client, aws_instance_name, unexpected_instance_name):
    aws_client.start_instance(instance_name=aws_instance_name)
    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}])["Reservations"][0][
        "Instances"][0]
    assert instance["State"]["Name"] == "running"

    status = aws_client.get_instance_status(instance_name=aws_instance_name)
    assert status == "RUNNING"

    status = aws_client.get_instance_status(instance_name=unexpected_instance_name)
    assert status == "NOT FOUND"
    
    # Restore instance status
    aws_client.stop_instance(instance_name=aws_instance_name)


def test_get_image(aws_client):
    images = aws_client.ec2_client.describe_images(
        Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-attacker"]}]
    )["Images"]

    response = aws_client.get_image("udelar-lab01-attacker")
    assert response[0] == images[0]["ImageId"]
    assert response[1] == images[0]["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]

    response = aws_client.get_image("notfound")
    assert response is None


def test_delete_image(aws_client, aws_instance_name):
    instance = aws_client.ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}])["Reservations"][0][
        "Instances"][0]

    tags_name = [{"Key": "Name", "Value": "deleteme"}]
    image = aws_client.ec2_client.create_image(
        Name="deleteme",
        TagSpecifications=[{"ResourceType": "image", "Tags": tags_name}],
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sdh',
                'Ebs': {
                    'VolumeSize': 100,
                },
            },
            {
                'DeviceName': '/dev/sdc',
                'VirtualName': 'ephemeral1',
            },
        ],
        InstanceId=instance["InstanceId"],
        Description='image to delete',
        NoReboot=True
    )
    aws_client.delete_image("deleteme")
    images = aws_client.ec2_client.describe_images(
        Filters=[{"Name": "tag:Name", "Values": ["deleteme"]}]
    )["Images"]
    assert len(images) == 0

    aws_client.delete_image("notfound")
    assert True

def test_get_machine_public_ip(aws_client, aws_instance_name, unexpected_instance_name):
    aws_client.start_instance(instance_name=aws_instance_name)
    ipaddr = aws_client.get_machine_public_ip(aws_instance_name)
    socket.inet_aton(ipaddr)    # This raises an exception if ipaddr is not valid
    assert True

    ipaddr = aws_client.get_machine_public_ip(unexpected_instance_name)
    assert ipaddr == None
    # Restore instance status
    aws_client.stop_instance(instance_name=aws_instance_name)

def test_get_machine_private_ip(aws_client, aws_instance_name):
    ipaddr = aws_client.get_machine_private_ip(aws_instance_name)
    socket.inet_aton(ipaddr)    # This raises an exception if ipaddr is not valid
    assert True

def test_get_security_group_id(aws_client):
    real_sg = aws_client.ec2_client.describe_security_groups(
        Filters=[{"Name": "description", "Values": ["Public Security Group"]}],
        DryRun=False,
    )["SecurityGroups"][0]

    sg = aws_client.get_security_group_id("Public Security Group")
    assert sg == [real_sg["GroupId"], ]

    sg = aws_client.get_security_group_id("not found")
    assert sg == []


def test_delete_security_groups(aws_client):
    vpc_id = aws_client.ec2_client.describe_vpcs()["Vpcs"][0]["VpcId"]
    # Create a security group on some VPC (the first)
    aws_client.ec2_client.create_security_group(
        GroupName="test_sg_1",
        Description="Delete Me",
        VpcId=vpc_id
    )
    aws_client.ec2_client.create_security_group(
        GroupName="test_sg_2",
        Description="Delete Me",
        VpcId=vpc_id
    )

    aws_client.delete_security_groups("Delete Me")

    assert len(aws_client.ec2_client.describe_security_groups(
        Filters=[{"Name": "description", "Values": ["Delete Me"]}],
        DryRun=False,
    )["SecurityGroups"]) == 0


def test_get_machines_imageid(mocker, aws_client):

    # This should return the phony image id used in conftest, repeated
    # a bunch of times.
    ids = aws_client.get_machines_imageid()
    assert len(ids) > 1
    assert set(ids) == set(["ami-03cf127a"])

    ids_paginated = aws_client.get_machines_imageid(2)
    assert set(ids_paginated) == set(ids)

    mocker.patch.object(aws_client.ec2_client, "describe_instances", side_effect=Exception("Connection refused"))
    with pytest.raises(AWSClientException):
        ids = aws_client.get_machines_imageid()
