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


"""Tectonic: An academic Cyber Range."""

import re
import logging
import traceback
from pathlib import Path
from collections import OrderedDict

import click

import tectonic.utils as utils
from tectonic.config import TectonicConfig
from tectonic.description import Description
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS
from tectonic.core import Core

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

        guests = [guest for _, guest in ctx.obj["description"].base_guests.items() if not guest_names or guest.base_name in guest_names]
        for guest in guests:
            if guest.copies == 1:
                if not copies or 1 in copies:
                    machines += [f"the {guest.base_name}"]
            else:
                if not copies:
                    machines += [f"all copies of the {guest.base_name}"]
                else:
                    guest_copies = list(
                        filter(
                            lambda c: c
                            <= guest.copies,
                            copies,
                        )
                    )
                    if len(guest_copies) == 1:
                        machines += [f"copy {guest_copies[0]} of the {guest.base_name}"]
                    else:
                        machines += [
                            f"copies {range_to_str(guest_copies)} of the {guest.base_name}"
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
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="Read tectonic configuration from specified INI file.",
    required=True,
)
@click.option(
    "--debug/--no-debug", default=False, help="Show debug messages during execution."
)
@click.option(
    "--lab_repo_uri",
    "-u",
    help="URI to a lab repository. Labs to deploy will be searched in this repo.",
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
    "--configure_dns",
    default=True,
    show_default=True,
    help="Configure internal DNS for instances.",
)
@click.option(
    "--gitlab_backend_url",
    help="Gitlab terraform state url",
)
@click.option(
    "--gitlab_backend_username",
    envvar="GITLAB_USERNAME",
    help="Gitlab Username",
)
@click.option(
    "--gitlab_backend_access_token",
    envvar="GITLAB_ACCESS_TOKEN",
    help="Gitlab Access Token",
)
@click.option(
    "--packer_executable_path",
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
    "--proxy",
    help="Guest machines proxy configuration URI for libvirt.",
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
    "--docker_dns",
    default="8.8.8.8",
    required=False,
    help="DNS to use for internet networks on Docker",
)
@click.option(
    "--ansible_forks",
    default="10",
    required=False,
    help="Number of parallel connection for Ansible",
)
@click.option(
    "--ansible_pipelining/--no-ansible_pipelining",
    default="False",
    help="Enable pipelining for Ansible",
)
@click.option(
    "--ansible_timeout",
    default="10",
    required=False,
    help="Timeout for Ansible connection.",
)
@click.argument("lab_edition_file", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def tectonic(
        ctx,
        config,
        debug,
        lab_repo_uri,
        ssh_public_key_file,
        configure_dns,
        gitlab_backend_url,
        gitlab_backend_username,
        gitlab_backend_access_token,
        packer_executable_path,
        libvirt_uri,
        proxy,
        keep_ansible_logs,
        docker_uri,
        docker_dns,
        ansible_forks,
        ansible_pipelining,
        ansible_timeout,
        lab_edition_file):
    """Deploy or manage a cyber range according to LAB_EDITION_FILE."""
    logfile = Path(lab_edition_file).parent / "tectonic.log"
    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(filename=logfile, encoding="utf-8", level=loglevel)

    ctx.ensure_object(dict)

    config = TectonicConfig.load(config)
    if debug:
        config.debug = debug
    if lab_repo_uri:
        config.lab_repo_uri = lab_repo_uri
    if ssh_public_key_file:
        config.ssh_public_key_file = ssh_public_key_file
    if configure_dns:
        config.configure_dns = configure_dns
    if gitlab_backend_url:
        config.gitlab_backend_url = gitlab_backend_url
    if gitlab_backend_username:
        config.gitlab_backend_username = gitlab_backend_username
    if gitlab_backend_access_token:
        config.gitlab_backend_access_token = gitlab_backend_access_token
    if packer_executable_path:
        config.packer_executable_path = packer_executable_path
    if packer_executable_path:
        config.packer_executable_path = packer_executable_path
    if libvirt_uri:
        config.libvirt.uri = libvirt_uri
    if proxy:
        config.proxy = proxy
    if keep_ansible_logs:
        config.ansible.keep_logs = keep_ansible_logs
    if docker_uri:
        config.docker.uri = docker_uri
    if docker_dns:
        config.docker.dns = docker_dns
    if ansible_forks:
        config.ansible.forks = ansible_forks
    if ansible_pipelining:
        config.ansible.pipelining = ansible_pipelining
    if ansible_timeout:
        config.ansible.timeout = ansible_timeout

    ctx.obj["config"] = config
    if config.platform == "aws":
        instance_type = InstanceTypeAWS()
    else:
        instance_type = InstanceType()
    ctx.obj["description"] = Description(config, instance_type, lab_edition_file)
    ctx.obj["core"] = Core(ctx.obj["config"], ctx.obj["description"])


    # TODO: Do this somewhere else
    # if elastic_stack_version == "latest":
    #     ctx.obj["description"].set_elastic_stack_version(ctx.obj["deployment"].get_elastic_latest_version())
    # if caldera_version == "latest":
    #     ctx.obj["description"].set_caldera_version("master")

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

    ctx.obj["core"].deploy(instances, images, False) # TODO: Do the right thing for services

    _info(ctx)


@tectonic.command()
@click.pass_context
@click.option(
    "--machines/--no-machines",
    default=True,
    show_default=True,
    help="Whether to destroy running guests in the lab.",
)
@click.option(
    "--images/--no-images",
    default=False,
    show_default=True,
    help="Whether to destroy the base images of guests and services in the lab.",
)
@click.option(
    "--packetbeat/--no-packetbeat",
    default=False,
    show_default=True,
    help="Whether to destroy the packetbeat service machine.",
)
@click.option(
    "--elastic/--no-elastic",
    default=False,
    show_default=True,
    help="Whether to destroy the ELK service machine.",
)
@click.option(
    "--caldera/--no-caldera",
    default=False,
    show_default=True,
    help="Whether to destroy the base image for Caldera.",
)
@click.option(
    "--instances", "-i", help="Range of instances to destroy.", type=NUMBER_RANGE
)
@click.option(
    "--force",
    "-f",
    help="Force the destruction of instances without a confirmation prompt.",
    is_flag=True,
)
def destroy(ctx, machines, images, instances, packetbeat, elastic, caldera, force):
    """Delete and destroy all resources of the cyber range. 

    If instances are specified only destroys running guests for those
    instances. Otherwise, destroys all running guests (if
    machines is true), and each specified service.
    """

    if not force:
        confirm_machines(
            ctx, instances, guest_names=None, copies=None, action="Destroying"
        )

    if (instances and not machines):
        raise TectonicException("If you specify a list of instances, machines must be true.")
    if (instances and (images or caldera or elastic or packetbeat)):
        raise TectonicException("You cannot specify a list of instances and image or service destruction at the same time.")

    services = []
    if packetbeat:
        services.append("packetbeat")
    if elastic:
        services.append("elastic")
    if caldera:
        services.append("caldera")

    ctx.obj["core"].destroy(instances, machines, services, images)


@tectonic.command()
@click.pass_context
@click.option(
    "--packetbeat/--no-packetbeat",
    default=True,
    show_default=True,
    help="Whether to create the base image for packetbeat.",
)
@click.option(
    "--elastic/--no-elastic",
    default=True,
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
    default=True,
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
    ctx.obj["description"].parse_machines(instances=None, guests=guests, copies=None, only_instances=True)
    _create_images(ctx, packetbeat, elastic, caldera, machines, guests)


def _create_images(ctx, packetbeat, elastic, caldera, machines, guests=None):
    services = []
    if elastic:
        services.append("elastic")
    if packetbeat:
        services.append("packetbeat")
    if caldera:
        services.append("caldera")
    if services:
        click.echo("Creating services images ...")
        ctx.obj["core"].create_services_images(services)

    if machines:
        click.echo("Creating base images...")
        ctx.obj["core"].create_cr_images(guests)


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
    result = ctx.obj["core"].list(instances, guests, copies)

    if result.get("instances_status"):
        headers = ["Name", "Status"]
        rows = []
        for machine, status in result.get("instances_status", []).items():
            rows.append([machine, status])
        click.echo(utils.create_table(headers,rows))

    if result.get("services_status"):
        headers = ["Name", "Status"]
        rows = []
        for machine, status in result.get("services_status", []).items():
            rows.append([machine, status])
        click.echo(utils.create_table(headers,rows))

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
    ctx.obj["core"].start(instances, guests, copies, services)


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
    ctx.obj["core"].stop(instances, guests, copies, services)

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
    ctx.obj["core"].restart(instances, guests, copies, services)


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
    ctx.obj["core"].console(instance, guest, copy, username)


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
    ctx.obj["core"].run_automation(instances, guests, copies, username, playbook)


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

    # entry_points = [ base_name for base_name, guest in ctx.obj["description"].guest_settings.items()
    #                  if guest and guest.get("entry_point") ]

    # if ctx.obj["description"].platform == "aws":
    #     entry_points += ["student_access"]

    # if not force:
    #     confirm_machines(ctx, instances, entry_points, None, "Creating credentials on")

    # click.echo("Configuring student access...")
    # ctx.obj["deployment"].student_access(instances)

    # _print_student_passwords(ctx)

    click.echo("Configuring student access...")
    users = ctx.obj["core"].configure_students_access(instances)

    rows = []
    headers = ["Username", "Password"]
    for username, users in users.items():
        rows.append([username, users['password']])
    table = utils.create_table(headers, rows)
    click.echo(table)

@tectonic.command()
@click.pass_context
def info(ctx):
    """Show cyber range information."""
    _info(ctx)

def _info(ctx):
    click.echo("Getting Cyber Range information...")
    result = ctx.obj["core"].info()

    if result.get("instances_info"):
        headers = ["Name", "Status"]
        rows = []
        for key, value in result.get("instances_info", []).items():
            rows.append([key, value])
        click.echo(utils.create_table(headers,rows))

    if result.get("services_info"):
        headers = ["Name", "Status"]
        rows = []
        for service, service_value in result.get("services_info", []).items():
            for key, value in service_value.items():
                if key == "Credentials":
                    for creds_key, creds_value in value.items():
                        rows.append([f"{service.capitalize()} {key}", f"{creds_key} {creds_value}"])
                else:
                    rows.append([f"{service.capitalize()} {key}", value])
        click.echo(utils.create_table(headers,rows))
        
    if result.get("student_access_password"):
        headers = ["Username", "Password"]
        rows = []
        for key, value in result.get("student_access_password", {}).items():
            rows.append([key, value])
        click.echo(utils.create_table(headers,rows))

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
    ctx.obj["core"].recreate(instances, guests, copies)

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
    parameters = ctx.obj["core"].get_parameters(instances, directory)
    rows = []
    headers = ["Instances", "Parameters"]
    for instance, parameter in parameters.items():
        rows.append([instance, parameter])
    table = utils.create_table(headers, rows)
    click.echo(table)

