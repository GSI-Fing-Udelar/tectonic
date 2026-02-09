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
import sys
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

logger = logging.getLogger()


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

            max_instances = ctx.obj["description"].instance_number
            if max(values or [], default=0) > max_instances:
                if max_instances > 1:
                    self.fail(f"Instances must be in the range from 1 to {max_instances}.")
                else:
                    self.fail("Scenario has only one instance.")
            return sorted(set(values))
        except Exception as e:
            self.fail(f"{value!r}. {e}", param, ctx)

def split_and_validate_list_of_options(ctx, param, value, allowed):
    """Validate a list of strings and split them by commas."""
    if len(value) == 0:
        return None
    values = []
    for item in value:
        values.extend(v.strip().lower() for v in item.split(",") if v.strip())

    if set(values) & {'all', 'none'}:
        if len(values) > 1:
            raise click.BadParameter(
                "'all' or 'none' cannot be combined with other names."
            )
        return allowed if 'all' in values else []
        
    invalid = sorted(set(values) - set(allowed))
    if invalid:
        raise click.BadParameter(
            f"{', '.join(invalid)}. Allowed values are: {allowed}"
        )

    # Preserve order, remove duplicates
    seen = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen

def split_guests(ctx, param, value):
    allowed_guests = []
    for _, guest in ctx.obj["description"].base_guests.items():
        allowed_guests.append(guest.base_name)
    for _, service in ctx.obj["description"].services_guests.items():
        allowed_guests.append(service.base_name)
    return split_and_validate_list_of_options(ctx, param, value, allowed_guests)

def split_services(ctx, param, value):
    allowed_services = []
    for _, service in ctx.obj["description"].services_guests.items():
        allowed_services.append(service.base_name)
    return split_and_validate_list_of_options(ctx, param, value, allowed_services)


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


def confirm_machines(ctx, instances, guest_names, copies, action, print_instances=True):
    """Prompt the user for confirmation to perform ACTION to machines."""
    # if instances:
    #     instances = list(
    #         filter(lambda i: i <= ctx.obj["description"].instance_number, instances)
    #     )

    if not instances or set(instances) == set(range(1, ctx.obj["description"].instance_number+1)):
        instances_msg = "all instances"
    elif len(instances) == 1:
        instances_msg = f"instance {instances[0]}"
    else:
        instances_msg = f"instances {range_to_str(instances)}"

    if not guest_names:
        machines_msg = "all scenario machines"
        spec_guests = False
    else:
        machines = []
        spec_guests = True

        # Remove duplicates
        guest_names = list(OrderedDict.fromkeys(guest_names))
        if "elastic" in guest_names:
            machines += ["the elastic server"]
            guest_names.remove("elastic")
        if "packetbeat" in guest_names:
            machines += ["the packetbeat"]
            guest_names.remove("packetbeat")
        if "caldera" in guest_names:
            machines += ["the caldera server"]
            guest_names.remove("caldera")
        if "guacamole" in guest_names:
            machines += ["the guacamole server"]
            guest_names.remove("guacamole")
        if "moodle" in guest_names:
            machines += ["the moodle server"]
            guest_names.remove("moodle")
        if "teacher_access" in guest_names:
            machines += ["the teacher access"]
            guest_names.remove("teacher_access")

        if not guest_names:
            print_instances = False

        guests = [guest for _, guest in ctx.obj["description"].base_guests.items() if not spec_guests or guest.base_name in guest_names]
        if len(guests) == len(ctx.obj["description"].base_guests) and copies is None:
            machines += ["all scenario machines"]
        else:
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
        logger.info(f"{action} {machines_msg} on {instances_msg}.")
    else:
        logger.info(f"{action} {machines_msg}.")
    if not click.confirm("Continue?"):
        logger.debug("Aborted!")
        raise click.Abort()


class ClickEchoHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)

            if record.levelno >= logging.ERROR:
                click.secho(msg, err=True, fg='red')
            elif record.levelno >= logging.INFO:
                click.secho(msg, err=True, fg='blue')
            else:
                click.echo(msg)

        except Exception:
            self.handleError(record)

def init_logging(logfile, loglevel):
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s]: %(message)s"
    )

    console_handler = ClickEchoHandler()
    console_handler.setLevel(loglevel)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="Read tectonic configuration from specified INI file.",
    required=True,
)
@click.option(
    "--debug/--no-debug", default=None, help="Show debug messages during execution."
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
    help="SSH pubkey to be used to connect to machines for configuration. [default: ~/.ssh/id_rsa.pub]",
)
@click.option(
    "--configure_dns",
    help="Configure internal DNS for instances. [default: False]",
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
)
@click.option(
    "--libvirt_uri",
    help="URI to connect to server, if using libvirt. [default: qemu:///system]",
)
@click.option(
    "--proxy",
    help="Guest machines proxy configuration URI for libvirt.",
)
@click.option(
    "--keep_ansible_logs/--no-keep_ansible_logs",
    help="Keep Ansible logs on managed hosts. [default: False]",
)
@click.option(
    "--docker_uri",
    help="URI to connect to server, if using docker. [default: unix:///var/run/docker.sock]",
)
@click.option(
    "--docker_dns",
    help="DNS to use for internet networks on Docker.",
)
@click.option(
    "--ansible_forks",
    help="Number of parallel connection for Ansible.",
)
@click.option(
    "--ansible_pipelining/--no-ansible_pipelining",
    help="Enable pipelining for Ansible",
)
@click.option(
    "--ansible_timeout",
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
    init_logging(logfile, loglevel)

    ctx.ensure_object(dict)
    config = TectonicConfig.load(config)
    if debug is not None:
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

    if config.ssh_public_key_file is None:
        raise ValueError("Invalid ssh_public_key_file ~/.ssh/id_rsa.pub. Must be a path to a file.")

    ctx.obj["config"] = config
    ctx.obj["description"] = Description(config, lab_edition_file)
    ctx.obj["core"] = Core(ctx.obj["description"])

@tectonic.command()
@click.pass_context
@click.option(
    "--guest_images/--no-guest_images",
    default=False,
    show_default=True,
    help="Whether to create base images for the scenario guests.",
)
@click.option(
    "--instances", "-i", help="Range of instances to deploy.", type=NUMBER_RANGE
)
@click.option(
    "--service_image_list",
    multiple=True,
    default=['none'],
    callback=split_services,
    type=click.STRING,
    help="List of service base images to create. Use 'all' for all services, or 'none' for no machines. [default: none]",
)
@click.option(
    "--force",
    "-f",
    help="Force the deployment of instances without a confirmation prompt.",
    is_flag=True,
)
def deploy(ctx, guest_images, instances, service_image_list, force):
    """Deploy the cyber range."""
    if not force:
        confirm_machines(ctx, instances, guest_names=None, copies=None, action="Deploying")

    ctx.obj["core"].deploy(instances, guest_images, service_image_list)
    _info(ctx)


@tectonic.command()
@click.pass_context
@click.option(
    "--images/--no-images",
    default=False,
    show_default=True,
    help="Whether to destroy the base images of guests and services in the lab.",
)
@click.option(
    "--services/--no-services",
    default=None,
    help="Whether to also destroy the services. [default: True if no instance is specified, False otherwise]",
)
@click.option(
    "--service_image_list",
    multiple=True,
    default=['none'],
    callback=split_services,
    type=click.STRING,
    help="List of service base images to destroy. Use 'all' for all services, or 'none' for no machines. [default: none]",
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
def destroy(ctx, images, services, service_image_list, instances, force):
    """Delete and destroy resources in the cyber range. 

    If instances are specified only destroys running guests for those
    instances.

    If no instances are specified, destroys all running guests (and
    optionally the corresponding base images), plus all services if
    the --services option is set.

    Since service images can be shared between scenarios, they are
    only removed if --images and --services is true, and explicitly
    set with --service_image_list.
    """

    if services is None:
        # default: True if no instance is specified, False otherwise
        services = not instances
        
    if instances:
        if images or services or len(service_image_list) > 0:
            raise click.BadParameter("Only running scenario guests can be destroyed when specifiying a list of instances.")
    else:
        if len(service_image_list) > 0 and (not services or not images):
            raise click.BadParameter("Please make sure services and images are set to be destroyed, if specifying a list of service images to delete.")

    if not force:
        if instances:
            confirm_machines(ctx, instances, guest_names=None, copies=None, action="Destroying")
        else:
            message = "Destroying all machines on all instances"
            if images:
                message += " (and their base images)"
            if services:
                message += ", plus all running services"
            if len(service_image_list) > 0:
                message += f". Also, the following service images will be deleted: {", ".join(service_image_list)}"
            message += "."
            logger.info(message)
            click.confirm("Continue?", abort=True)
                            
    ctx.obj["core"].destroy(instances, images, services, service_image_list)

@tectonic.command()
@click.pass_context
@click.option(
    "--guests",
    "-g",
    multiple=True,
    type=click.STRING,
    callback=split_guests,
    help="Guest or service names (repeatable or comma-separated) for which to create their base images. Use 'all' for all guests and services or 'none' for no machines. [default: only scenario guests]",
)
@click.option(
    "--force",
    "-f",
    help="Force the destruction of instances without a confirmation prompt.",
    is_flag=True,
)
def create_images(ctx, guests, force):
    """Create lab base images.

    Note that existing images will be destroyed. No guests using these
    images can be running.

    """
    if guests is not None:
        services = [service.base_name for _, service in ctx.obj["description"].services_guests.items() if service.base_name in guests]
    else:
        # Default is to not create service images
        services = []

    scenario_guests = [guest.base_name for _, guest in ctx.obj["description"].scenario_guests.items() if guests is None or guest.base_name in guests]

    if not force:
        confirm_machines(ctx, instances=None, guest_names=guests, copies=None, action="Creating images for", print_instances=False)

    ctx.obj["core"].create_services_images(services)
    ctx.obj["core"].create_instances_images(scenario_guests)


@tectonic.command(name="list")
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to list.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    multiple=True,
    default=["all"],
    type=click.STRING,
    callback=split_guests,
    help="Guest or service names (repeatable or comma-separated) to list. Use 'all' for all guests and services or 'none' for no machines. [default: all]",
)
@click.option("--copies", "-c", help="Number of copy to list.", type=NUMBER_RANGE)
def list_instances(ctx, instances, guests, copies):
    """Print information and state of the cyber range resources."""
    logger.info("Getting Cyber Range status...")
    result = ctx.obj["core"].list_instances(instances, guests, copies)

    if result.get("instances_info"):
        headers = ["Name", "IP", "Status"]
        rows = []
        for machine, info in result.get("instances_info", []).items():
            rows.append([machine, info[0], info[1]])
        logger.info(utils.create_table(headers,rows))

    if result.get("services_status"):
        headers = ["Name", "Status"]
        rows = []
        for machine, status in result.get("services_status", []).items():
            rows.append([machine, status])
        logger.info(utils.create_table(headers,rows))
        
@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to start.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    multiple=True,
    type=click.STRING,
    callback=split_guests,
    help="Guest or service names (repeatable or comma-separated) to start. Use 'all' for all guests and services or 'none' for no machines. [default: all scenario guests]",
)
@click.option("--copies", "-c", help="Number of copy to start.", type=NUMBER_RANGE)
@click.option(
    "--force",
    "-f",
    help="Force the start of instances without a confirmation prompt.",
    is_flag=True,
)
def start(ctx, instances, guests, copies, force):
    """Start (boot up) machines in the cyber range."""
    if guests is None:
        guests = [guest.base_name for _, guest in ctx.obj["description"].scenario_guests.items()]

    if not force:
        confirm_machines(ctx, instances, guests, copies, "Starting")
    ctx.obj["core"].start(instances, guests, copies)


@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to shutdown.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    multiple=True,
    type=click.STRING,
    callback=split_guests,
    help="Guest or service names (repeatable or comma-separated) to shutdown. Use 'all' for all guests and services or 'none' for no machines. [default: all]",
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
def shutdown(ctx, instances, guests, copies, force):
    """Shutdown machines in the cyber range."""
    if guests is None:
        guests = [guest.base_name for _, guest in ctx.obj["description"].scenario_guests.items()]

    if not force:
        confirm_machines(ctx, instances, guests, copies, "Shuting down")
    ctx.obj["core"].stop(instances, guests, copies)

@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to reboot.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    multiple=True,
    type=click.STRING,
    callback=split_guests,
    help="Guest or service names (repeatable or comma-separated) to reboot. Use 'all' for all guests and services or 'none' for no machines. [default: all scenario guests]",
)
@click.option("--copies", "-c", help="Number of copy to reboot.", type=NUMBER_RANGE)
@click.option(
    "--force",
    "-f",
    help="Force the reboot of instances without a confirmation prompt.",
    is_flag=True,
)
def reboot(ctx, instances, guests, copies, force):
    """Reboot machines in the cyber range."""
    if guests is None:
        guests = [guest.base_name for _, guest in ctx.obj["description"].scenario_guests.items()]

    if not force:
        confirm_machines(ctx, instances, guests, copies, "Rebooting")
    ctx.obj["core"].restart(instances, guests, copies)


@tectonic.command()
@click.pass_context
@click.option(
    "--instance", "-i", help="Number of instance to connect.", type=NUMBER_RANGE
)
@click.option(
    "--guest", "-g", help="Name of guest to connect.", type=click.STRING
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
    if guest is not None:
        guest = [guest]
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
    multiple=True,
    type=click.STRING,
    callback=split_guests,
    help="Guest or service names (repeatable or comma-separated) to run ansible on. Use 'all' for all guests and services or 'none' for no machines. [default: all scenario guests]",
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
    """Run an ansible playbook in the selected machines."""

    if guests is None:
        guests = [guest.base_name for _, guest in ctx.obj["description"].scenario_guests.items()]

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
    """Create users for access
    Students users are created on all entry points (and the student access
    host, if appropriate). Credentials can be public SSH keys and/or autogenerated passwords.

    Trainers users are created on all machines.
    """
    logger.info("Configuring student access...")
    users = ctx.obj["core"].configure_access(instances)

    rows = []
    headers = ["Username", "Password"]
    for username, users in users.items():
        rows.append([username, users['password']])
    logger.info(utils.create_table(headers,rows))

@tectonic.command()
@click.pass_context
def info(ctx):
    """Show cyber range information."""
    _info(ctx)

def _info(ctx):
    logger.info("Getting Cyber Range information...")
    result = ctx.obj["core"].info()

    if result.get("instances_info"):
        headers = ["Description", "Info"]
        rows = []
        for key, value in result.get("instances_info", []).items():
            rows.append([key, value])
        logger.info(utils.create_table(headers,rows))

    if result.get("services_info"):
        headers = ["Description", "Info"]
        rows = []
        for service, service_value in result.get("services_info", []).items():
            for key, value in service_value.items():
                if key == "Credentials" and value:
                    for creds_key, creds_value in value.items():
                        rows.append([f"{service.capitalize()} {key}", f"{creds_key} {creds_value}"])
                else:
                    rows.append([f"{service.capitalize()} {key}", value])
        logger.info(utils.create_table(headers,rows))
    if result.get("student_access_password"):
        headers = ["Username", "Password"]
        rows = []
        for key, value in result.get("student_access_password", {}).items():
            rows.append([key, value])
        logger.info(utils.create_table(headers,rows))

@tectonic.command()
@click.pass_context
@click.option(
    "--instances", "-i", help="Range of instances to recreate.", type=NUMBER_RANGE
)
@click.option(
    "--guests",
    "-g",
    multiple=True,
    type=click.STRING,
    callback=split_guests,
    help="Guest names (repeatable or comma-separated) to recreate. Use 'all' for all guests (but no services) or 'none' for no machines. [default: all scenario guests]",
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
    if guests is None:
        guests = [guest.base_name for _, guest in ctx.obj["description"].scenario_guests.items()]
    if set(guests) & set([service.base_name for _, service in ctx.obj["description"].services_guests.items()]):
        raise click.BadParameter("Services cannot be recreated.")
    
    if not force:
        confirm_machines(ctx, instances, guests, copies, "Recreating")
    ctx.obj["core"].recreate(instances, guests, copies)


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
    logger.info("Getting parameters...")
    parameters = ctx.obj["core"].get_parameters(instances, directory)
    if directory:
        logger.info(parameters)
    else:
        rows = []
        headers = ["Instances", "Parameters"]
        for instance, parameter in parameters.items():
            rows.append([instance, parameter])
        logger.info(utils.create_table(headers, rows))
        

def main():
    obj = {}
    try:
        tectonic.main(obj=obj)
    except Exception as e:
        logger.debug(traceback.format_exc())
        if obj.get("config") and obj.get("config").debug:
            raise
        else:
            click.echo(str(e))
        
