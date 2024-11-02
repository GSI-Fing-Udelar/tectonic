#!/usr/bin/env python3

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

# -*- coding: utf-8 -*-

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


"""Tectonic: An academic Cyber Range."""

import os
import pprint
import re
import logging
from configparser import ConfigParser
import traceback
from pathlib import Path, PurePosixPath
from collections import OrderedDict

import click

from tectonic.deployment_aws import AWSDeployment
from tectonic.deployment_libvirt import LibvirtDeployment
from tectonic.deployment_docker import DockerDeployment
from tectonic.description import Description
from tectonic.ansible import Ansible
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS
from tectonic.utils import create_table



def log(msg):
    click.echo(msg)


def debug(msg):
    if DEBUG:
        click.echo(msg)


# The instances can be specified as a list, a range, or a combination of both:
#    --instances=1,3,8
#    --instances=1-5
#    --insntaces=13,16-24,25
# A comma on its own can be used to specify an empty list of instances.
class NumberRangeParamType(click.ParamType):
    """ A parameter that works similar to :data:`click.INT`, but accepts
    ranges of integers as well.  For instance, ``1-3,5,7-10`` would result
    in a list of four integers.
    """
    name = "NUMBER_RANGE"

    def convert(self, value, param, ctx):
        if isinstance(value, list):
            return sorted(set(value))

        try:
            values = []
            for i in value.split(","):
                m = re.search(r'^\d+$', i)
                if m:
                    values += [int(m.group(0))]
                else:
                    m = re.search(r'^(\d+)(\.\.|-)(\d+)$', i)
                    if m:
                        values += list(range(int(m.group(1)), int(m.group(3)) + 1))
                    elif i == "":
                        pass
                    else:
                        self.fail(f"Cannot parse {i}.", param, ctx)
            return sorted(set(values))
        except Exception as e:
            self.fail(f"{value!r} is not a valid range. {str(e)}", param, ctx)


class TectonicException(Exception):
    pass


def load_config(ctx, param, config_file):
    if config_file is None:
        return {}
    cfg = ConfigParser()
    cfg.read(config_file)
    options = {}

    # flatten the config file
    for section in ["config", "aws", "libvirt", "elastic"]:
        try:
            options = options | dict(cfg[section])
        except KeyError:
            pass

    ctx.default_map = options


NUMBER_RANGE = NumberRangeParamType()
CONTEXT_SETTINGS = {"help_option_names": ['-h', '--help']}


def range_to_str(r):
    """Returns an appropriate text describing the range."""
    if not r:
        return ""

    s = []
    it = iter(r)
    prev = next(it)
    accum = [str(prev)]
    for n in it:
        if n == prev + 1:
            accum.append(str(n))
        else:
            if len(accum) > 2:
                s.append(f"from {accum[0]} to {accum[-1]}")
            else:
                s += accum
            accum = [str(n)]
        prev = n
    if len(accum) > 2:
        s.append(f"from {accum[0]} to {accum[-1]}")
    else:
        s += accum

    if len(s) > 1:
        return ", ".join(s[:-1]) + ", and " + s[-1]

    return s[0]


def confirm_machines(ctx, instances, guest_names, copies, action):
    """Prompt the user for confirmation to perform ACTION to machines."""
    print_instances = True

    if instances:
        instances = list(
            filter(lambda i: i <= ctx.obj["description"].instance_number, instances)
        )

    if not instances or len(instances) == ctx.obj["description"].instance_number:
        instances_msg = "all instances"
    elif len(instances) == 1:
        instances_msg = f"instance {instances[0]}"
    else:
        instances_msg = f"instances {range_to_str(instances)}"

    if not guest_names:
        machines_msg = "all machines"
    else:
        machines = []

        # Remove duplicates
        guest_names = list(OrderedDict.fromkeys(guest_names))
        if "teacher_access" in guest_names:
            machines += ["the teacher access"]
            guest_names.remove("teacher_access")
        if "student_access" in guest_names:
            machines += ["the student access"]
            guest_names.remove("student_access")
        if "packetbeat" in guest_names:
            machines += ["the packetbeat"]
            guest_names.remove("packetbeat")

        if not guest_names:
            print_instances = False

        for guest_name in guest_names:
            if ctx.obj["description"].get_guest_copies(guest_name) == 1:
                if not copies or 1 in copies:
                    machines += [f"the {guest_name}"]
            else:
                if not copies:
                    machines += [f"all copies of the {guest_name}"]
                else:
                    guest_copies = list(
                        filter(
                            lambda c: c
                            <= ctx.obj["description"].get_guest_copies(guest_name),
                            copies,
                        )
                    )
                    if len(guest_copies) == 1:
                        machines += [f"copy {guest_copies[0]} of the {guest_name}"]
                    else:
                        machines += [
                            f"copies {range_to_str(guest_copies)} of the {guest_name}"
                        ]
        if len(machines) > 1:
            machines_msg = ", ".join(machines[:-1]) + " and " + machines[-1]
        elif len(machines) == 1:
            machines_msg = machines[0]
        else:
            return

    if print_instances:
        click.echo(f"{action} {machines_msg}, on {instances_msg}.")
    else:
        click.echo(f"{action} {machines_msg}.")
    click.confirm("Continue?", abort=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    # TODO: Try to find the file in the correct locations.
    callback=load_config,
    is_eager=True,
    expose_value=False,
    help="Read option defaults from specified INI file.",
    show_default=True,
)
@click.option(
    "--debug/--no-debug", default=False, help="Show debug messages during execution."
)
@click.option(
    "--platform",
    type=click.Choice(["aws", "libvirt", "docker"], case_sensitive=False),
    default="aws",
    help="Deploy the cyber range to this platform.",
)
@click.option(
    "--lab_repo_uri",
    "-u",
    required=True,
    help="URI to a lab repository. Labs to deploy will be searched in this repo.",
)
@click.option(
    "--aws_region",
    "-r",
    default="us-east-1",
    show_default=True,
    help="AWS region to use for deployment.",
)
@click.option(
    "--aws_default_instance_type",
    "-t",
    default="t2.micro",
    show_default=True,
    help="Default EC2 instance type. Can be overwritten in CR guest configuration.",
)
@click.option(
    "--ssh_public_key_file",
    "-p",
    type=click.Path(dir_okay=False),
    default="~/.ssh/id_rsa.pub",
    show_default=True,
    help="SSH pubkey to be used to connect to machines for configuration.",
)
@click.option(
    "--ansible_ssh_common_args",
    "-s",
    default="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
    help="SSH extra connection options for connection to the CR machines.",
)  # TODO: check default value
@click.option(
    "--packetbeat_vlan_id",
    "-v",
    default="1",
    help="VLAN ID used in traffic mirrorring.",
)
@click.option(
    "--packetbeat_policy_name",
    "-n",
    default="Packetbeat",
    help="Packetbeat policy name.",
)
@click.option(
    "--network_cidr_block",
    "-b",
    default="10.0.0.0/16",
    help="CIDR block for the whole lab network.",
)
@click.option(
    "--configure_dns",
    default=True,
    show_default=True,
    help="Configure internal DNS for instances.",
)
@click.option(
    "--teacher_access",
    type=click.Choice(["host", "endpoint"], case_sensitive=False),
    default="host",
    help="Type of teacher access to configure.",
)
@click.option(
    "--elastic_stack_version",
    default="latest",
    help="Elastc version",
)
@click.option(
    "--gitlab_backend_url",
    required=False,
    help="Gitlab terraform state url",
)
@click.option(
    "--gitlab_backend_username",
    envvar="GITLAB_USERNAME",
    required=False,
    help="Gitlab Username",
)
@click.option(
    "--gitlab_backend_access_token",
    envvar="GITLAB_ACCESS_TOKEN",
    required=False,
    help="Gitlab Access Token",
)
@click.option(
    "--packer_executable_path",
    required=False,
    help="Packer executable path",
    default="packer",
)
@click.option(
    "--libvirt_uri",
    default="qemu:///system",
    show_default=True,
    help="URI to connect to server, if using libvirt",
)
@click.option(
    "--libvirt_storage_pool",
    default="default",
    help="Name of the libvirt storage pool where images will be created.",
)
@click.option(
    "--libvirt_student_access",
    type=click.Choice(["port_forwarding", "bridge"], case_sensitive=False),
    default="port_forwarding",
    help="How student access should be configured: port forwarding in the libvirt server (port_forwarding) or adding "
         "NICs to the entry points in a bridged network (bridge).",
)
@click.option(
    "--libvirt_bridge",
    help="Name of the libvirt server bridge to use for student access.",
)
@click.option(
    "--libvirt_external_network",
    default="192.168.44.0/25",
    help="CIDR block of the external bridged network, if appropriate. Static IP addresses are assigned sequentially "
         "to lab entry points.",
)
@click.option(
    "--libvirt_bridge_base_ip",
    default=10,
    help="Starting IP from which to sequentially assign the entry points IPs. With default values, the first entry "
         "point would get 192.168.44.11, and so on.",
)
@click.option(
    "--proxy",
    required=False,
    help="Guest machines proxy configuration URI for libvirt.",
)
@click.option(
    "--endpoint_policy_name",
    default="Endpoint",
    help="Agent policy name.",
)
@click.option(
    "--internet_network_cidr_block",
    default="192.168.4.0/24",
    help="CIDR internet network",
)
@click.option(
    "--services_network_cidr_block",
    default="192.168.5.0/24",
    help="CIDR services network",
)
@click.option(
    "--keep_ansible_logs/--no-keep_ansible_logs",
    default="False",
    help="Keep Ansible logs on managed hosts.",
)
@click.option(
    "--docker_uri",
    default="unix:///var/run/docker.sock",
    show_default=True,
    help="URI to connect to server, if using docker",
)
@click.option(
    "--caldera_version",
    default="latest",
    help="Caldera version.",
)
@click.argument("lab_edition_file", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def tectonic(
    ctx,
    platform,
    lab_repo_uri,
    aws_region,
    aws_default_instance_type,
    ssh_public_key_file,
    ansible_ssh_common_args,
    debug,
    packetbeat_vlan_id,
    packetbeat_policy_name,
    network_cidr_block,
    configure_dns,
    teacher_access,
    elastic_stack_version,
    gitlab_backend_url,
    gitlab_backend_username,
    gitlab_backend_access_token,
    packer_executable_path,
    libvirt_uri,
    libvirt_storage_pool,
    libvirt_student_access,
    libvirt_bridge,
    libvirt_external_network,
    libvirt_bridge_base_ip,
    proxy,
    lab_edition_file,
    endpoint_policy_name,
    internet_network_cidr_block,
    services_network_cidr_block,
    keep_ansible_logs,
    docker_uri,
    caldera_version,
):
    """Deploy or manage a cyber range according to LAB_EDITION_FILE."""
    logfile = PurePosixPath(lab_edition_file).parent.joinpath("tectonic.log")
    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(filename=logfile, encoding="utf-8", level=loglevel)

    ctx.ensure_object(dict)

    instance_type = None
    if platform == "aws":
        instance_type = InstanceTypeAWS(aws_default_instance_type)
    else:
        instance_type = InstanceType()

    ctx.obj["description"] = Description(
        lab_edition_file,
        platform,
        lab_repo_uri,
        teacher_access,
        configure_dns,
        ssh_public_key_file,
        ansible_ssh_common_args,
        aws_region,
        aws_default_instance_type,
        network_cidr_block,
        packetbeat_policy_name,
        packetbeat_vlan_id,
        elastic_stack_version,
        libvirt_uri,
        libvirt_storage_pool,
        libvirt_student_access,
        libvirt_bridge,
        libvirt_external_network,
        libvirt_bridge_base_ip,
        proxy,
        instance_type,
        endpoint_policy_name,
        internet_network_cidr_block,
        services_network_cidr_block,
        keep_ansible_logs,
        docker_uri,
        caldera_version,
    )

    if platform == "aws":
        ctx.obj["deployment"] = AWSDeployment(
            ctx.obj["description"],
            gitlab_backend_url=gitlab_backend_url,
            gitlab_backend_username=gitlab_backend_username,
            gitlab_backend_access_token=gitlab_backend_access_token,
            packer_executable_path=packer_executable_path,
        )
    elif platform == "libvirt":
        ctx.obj["deployment"] = LibvirtDeployment(
            ctx.obj["description"],
            gitlab_backend_url=gitlab_backend_url,
            gitlab_backend_username=gitlab_backend_username,
            gitlab_backend_access_token=gitlab_backend_access_token,
            packer_executable_path=packer_executable_path,
        )
    elif platform == "docker":
        ctx.obj["deployment"] = DockerDeployment(
            ctx.obj["description"],
            gitlab_backend_url=gitlab_backend_url,
            gitlab_backend_username=gitlab_backend_username,
            gitlab_backend_access_token=gitlab_backend_access_token,
            packer_executable_path=packer_executable_path,
        )
    else:
        raise Exception(f"Unsupported platform {platform}.")

    ctx.obj["ansible"] = Ansible(ctx.obj["deployment"])

    if elastic_stack_version == "latest":
        ctx.obj["description"].set_elastic_stack_version(ctx.obj["deployment"].get_elastic_latest_version())

    if caldera_version == "latest":
        ctx.obj["description"].set_caldera_version("master")


@tectonic.command()
@click.pass_context
@click.option(
    "--images/--no-images",
    default=False,
    show_default=True,
    help="Whether to create base images for each guest in the lab.",
)
@click.option(
    "--instances", "-i", help="Range of instances to list.", type=NUMBER_RANGE
)
@click.option(
    "--packetbeat_image/--no-packetbeat_image",
    default=False,
    show_default=True,
    help="Whether to create the base image for packetbeat.",
)
@click.option(
    "--elastic_image/--no-elastic_image",
    default=False,
    show_default=True,
    help="Whether to create the base image for ELK.",
)
@click.option(
    "--caldera_image/--no-caldera_image",
    default=False,
    show_default=True,
    help="Whether to create the base image for Caldera.",
)
@click.option(
    "--force",
    "-f",
    help="Force the deployment of instances without a confirmation prompt.",
    is_flag=True,
)
def deploy(ctx, images, instances, packetbeat_image, elastic_image, caldera_image, force):
    """Deploy the cyber range."""
    if not force:
        confirm_machines(ctx, instances, guest_names=None, copies=None, action="Deploying")

    if images:
        _create_images(ctx, packetbeat_image, elastic_image, caldera_image, True)

    ctx.obj["deployment"].deploy_infraestructure(instances)

    _info(ctx)


@tectonic.command()
@click.pass_context
@click.option(
    "--images/--no-images",
    default=False,
    show_default=True,
    help="Whether to destroy the base images of each guest in the lab.",
)
@click.option(
    "--packetbeat_image/--no-packetbeat_image",
    default=False,
    show_default=True,
    help="Whether to destroy the base image for packetbeat.",
)
@click.option(
    "--elastic_image/--no-elastic_image",
    default=False,
    show_default=True,
    help="Whether to destroy the base image for ELK.",
)
@click.option(
    "--caldera_image/--no-caldera_image",
    default=False,
    show_default=True,
    help="Whether to destroy the base image for Caldera.",
)
@click.option(
    "--instances", "-i", help="Range of instances to list.", type=NUMBER_RANGE
)
@click.option(
    "--force",
    "-f",
    help="Force the destruction of instances without a confirmation prompt.",
    is_flag=True,
)
def destroy(ctx, images, instances, packetbeat_image, elastic_image, caldera_image, force):
    """Delete and destroy all resources of the cyber range."""

    if not force:
        confirm_machines(
            ctx, instances, guest_names=None, copies=None, action="Destroying"
        )

    ctx.obj["deployment"].destroy_infraestructure(instances)

    if instances is None:
        if images:
            click.echo("Destroying base images...")
            ctx.obj["deployment"].delete_cr_images()

        if (packetbeat_image and ctx.obj["description"].platform == "aws")  or elastic_image or caldera_image:
            click.echo("Destroying services base image...")
            services = {
                "packetbeat": packetbeat_image and ctx.obj["description"].platform == "aws",
                "elastic": elastic_image,
                "caldera": caldera_image
            }
            ctx.obj["deployment"].delete_services_images(services)

@tectonic.command()
@click.pass_context
@click.option(
    "--packetbeat/--no-packetbeat",
    default=False,
    show_default=True,
    help="Whether to create the base image for packetbeat.",
)
@click.option(
    "--elastic/--no-elastic",
    default=False,
    show_default=True,
    help="Whether to create the base image for Elastic on-prem.",
)
@click.option(
    "--machines/--no-machines",
    default=True,
    show_default=True,
    help="Whether to create the scenario base images.",
)
@click.option(
    "--caldera/--no-caldera",
    default=False,
    show_default=True,
    help="Whether to create the base image for Caldera on-prem.",
)
@click.option(
    "--guests",
    "-g",
    multiple=True,
    type=click.STRING,
    help="Name of guests to list.",
)
def create_images(ctx, packetbeat, elastic, caldera, machines, guests):
    """Create lab base images."""
    ctx.obj["description"].parse_machines(
        instances=None, guests=guests, copies=None, only_instances=True
    )
    _create_images(ctx, packetbeat, elastic, caldera, machines, guests)


def _create_images(ctx, packetbeat, elastic, caldera, machines, guests=None):
    if (packetbeat and ctx.obj["description"].platform == "aws") or elastic or caldera:
        click.echo("Creating services images ...")
        services = {
            "packetbeat": packetbeat and ctx.obj["description"].platform == "aws",
            "elastic": elastic,
            "caldera": caldera
        }
        ctx.obj["deployment"].create_services_images(services)

    if machines:
        click.echo("Creating base images...")
        ctx.obj["deployment"].create_cr_images(guests)


@tectonic.command(name="list")
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to list.", type=NUMBER_RANGE
)
@click.option(
    "--guests", "-g", help="Name of guests to list.", multiple=True, type=click.STRING
)
@click.option("--copies", "-c", help="Number of copy to list.", type=NUMBER_RANGE)
def list_instances(ctx, instances, guests, copies):
    """Print information and state of the cyber range resources."""
    click.echo("Getting Cyber Range status...")
    result = ctx.obj["deployment"].list_instances(instances, guests, copies)
    click.echo(result)
    click.echo("Getting Services status...")
    result = ctx.obj["deployment"].get_services_status()
    click.echo(result)

@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to start.", type=NUMBER_RANGE
)
@click.option(
    "--guests", "-g", help="Name of guests to start.", multiple=True, type=click.STRING
)
@click.option("--copies", "-c", help="Number of copy to start.", type=NUMBER_RANGE)
@click.option(
    "--force",
    "-f",
    help="Force the start of instances without a confirmation prompt.",
    is_flag=True,
)
@click.option(
    "--services",
    "-s",
    help="Start services components.",
    is_flag=True,
)
def start(ctx, instances, guests, copies, force, services):
    """Start (boot up) machines in the cyber range."""
    if not force:
        confirm_machines(ctx, instances, guests, copies, "Start")
    ctx.obj["deployment"].start(instances, guests, copies, services)


@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to shutdown.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    help="Name of guests to shutdown.",
    multiple=True,
    type=click.STRING,
)
@click.option(
    "--copies", "-c", help="Number of copy to shutdown.", multiple=True, type=click.INT
)
@click.option(
    "--force",
    "-f",
    help="Force the shut down of instances without a confirmation prompt.",
    is_flag=True,
)
@click.option(
    "--services",
    "-s",
    help="Shut down services components.",
    is_flag=True,
)
def shutdown(ctx, instances, guests, copies, force, services):
    """Shutdown machines in the cyber range."""
    if not force:
        confirm_machines(ctx, instances, guests, copies, "Shut down")
    ctx.obj["deployment"].shutdown(instances, guests, copies, services)

@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to reboot.", type=NUMBER_RANGE
)
@click.option(
    "--guests", "-g", help="Name of guests to reboot.", multiple=True, type=click.STRING
)
@click.option("--copies", "-c", help="Number of copy to reboot.", type=NUMBER_RANGE)
@click.option(
    "--force",
    "-f",
    help="Force the reboot of instances without a confirmation prompt.",
    is_flag=True,
)
@click.option(
    "--services",
    "-s",
    help="Reboot services components.",
    is_flag=True,
)
def reboot(ctx, instances, guests, copies, force, services):
    """Reboot machines in the cyber range."""
    if not force:
        confirm_machines(ctx, instances, guests, copies, "Reboot")
    ctx.obj["deployment"].reboot(instances, guests, copies, services)


@tectonic.command()
@click.pass_context
@click.option(
    "--instance", "-i", help="Number of instance to connect.", type=NUMBER_RANGE
)
@click.option(
    "--guest", "-g", help="Name of guest to connect.", multiple=True, type=click.STRING
)
@click.option("--copy", "-c", help="Number of copy to connect.", type=NUMBER_RANGE)
@click.option(
    "--username",
    "-u",
    help="Username for connecting to the machine.",
    type=click.STRING,
)
def console(ctx, instance, guest, copy, username):
    """Connect to a machine in the cyber range and get a console."""
    machines_to_connect = ctx.obj["description"].parse_machines(
        instance or [], guest, copy, False
    )
    if len(machines_to_connect) > 1:
        raise TectonicException("You must specify only one machine to connect.")

    machine_to_connect = machines_to_connect[0]
    click.echo(f"Connecting to machine {machine_to_connect}...")
    ctx.obj["deployment"].connect_to_instance(machine_to_connect, username)


@tectonic.command()
@click.pass_context
@click.option(
    "--instances",
    "-i",
    help="Run ansible only on this range of instances.",
    type=NUMBER_RANGE,
)
@click.option(
    "--guests",
    "-g",
    help="Run ansible only on these guests with this base name.",
    multiple=True,
    type=click.STRING,
)
@click.option(
    "--copies",
    "-c",
    help="Run ansible only on guests with this copy number.",
    type=NUMBER_RANGE,
)
@click.option(
    "--username",
    "-u",
    help="Username for connecting to the machine.",
    type=click.STRING,
)
@click.option(
    "--playbook",
    "-p",
    help="Playbook to run. If not provided, the lab default after-clone playbook will be used.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--force",
    "-f",
    help="Run the playbook on selected instances without a confirmation prompt.",
    is_flag=True,
)
def run_ansible(ctx, instances, guests, copies, username, playbook, force):
    """Run an ansible playbook in the selected INSTANCE."""
    ctx.obj["description"].parse_machines(
        instances, guests, copies, only_instances=False
    )
    if not force:
        confirm_machines(ctx, instances, guests, copies, "Applying ansible playbook to")
    ctx.obj["ansible"].run(
        instances=instances, guests=guests, copies=copies, only_instances=False, username=username, playbook=playbook
    )


@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to configure student access credentials.", type=NUMBER_RANGE
)
@click.option(
    "--force",
    "-f",
    help="Apply the configuration to the selected machines without a confirmation prompt.",
    is_flag=True,
)
def student_access(ctx, instances, force):
    """Create users for the students.
    Users are created on all entry points (and the student access
    host, if appropriate). Credentials can be public SSH keys and/or
    autogenerated passwords.
    """

    entry_points = [ base_name for base_name, guest in ctx.obj["description"].guest_settings.items()
                     if guest and guest.get("entry_point") ]

    if ctx.obj["description"].platform == "aws":
        entry_points += ["student_access"]

    if not force:
        confirm_machines(ctx, instances, entry_points, None, "Creating credentials on")

    click.echo("Configuring student access...")
    ctx.obj["deployment"].student_access(instances)

    _print_student_passwords(ctx)

@tectonic.command()
@click.pass_context
def info(ctx):
    """Show cyber range information."""
    _info(ctx)

def _info(ctx):
    click.echo("Getting Cyber Range information...")
    result = ctx.obj["deployment"].get_cyberrange_data()
    click.echo(result)
    _print_student_passwords(ctx)
    
def _print_student_passwords(ctx):
    """Print the generated student passwords, if create_student_passwords is True.
    """
    if ctx.obj["description"].create_student_passwords:
        users = ctx.obj["deployment"].get_student_access_users()
        click.echo("\nStudent users:")
        rows = []
        headers = ["Username", "Password"]
        for username, user in users.items():
            rows.append([username, user['password']])
        table = create_table(headers, rows)
        click.echo(table)


@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to recreate.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    help="Name of guests to recreate.",
    multiple=True,
    type=click.STRING,
)
@click.option(
    "--copies",
    "-c",
    help="Number of copy to recreate.",
    type=NUMBER_RANGE,
)
@click.option(
    "--force",
    "-f",
    help="Recreate the selected machines without a confirmation prompt.",
    is_flag=True,
)
def recreate(ctx, instances, guests, copies, force):
    """Recreate instances."""
    if not force:
        confirm_machines(ctx, instances, guests, copies, "Recreate")
    ctx.obj["deployment"].recreate(instances, guests, copies)

if __name__ == "__main__":
    obj = {}
    try:
        tectonic(obj)
    except Exception as e:
        if obj["debug"]:
            traceback.print_exc()
        else:
            click.echo(f"Error: {e}")

@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to list.", type=NUMBER_RANGE
)
@click.option(
    "--directory",
    "-d",
    help="path of the directory where to create the parameters file.",
    type=click.STRING,
)
def show_parameters(ctx, instances, directory):
    """Generate parameters for instances"""
    click.echo("Getting parameters")
    ctx.obj["deployment"].get_parameters(instances, directory)
