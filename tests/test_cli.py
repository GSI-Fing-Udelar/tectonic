
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

import pytest
import io
import responses
import click
from click.testing import CliRunner
import ansible_runner
import libvirt_qemu
from configparser import ConfigParser
import packerpy
import fabric
import invoke
import socket

import tectonic.cli
from tectonic.cli import tectonic as tectonic_cli
from tectonic.aws import Client as AWSClient
from tectonic.deployment import Deployment
from tectonic.libvirt_client import Client as LibvirtClient
from tectonic.deployment_libvirt import LibvirtDeployment

def test_tectonic_help(tectonic_config):
    runner = CliRunner()
    result = runner.invoke(tectonic_cli, ['--config', tectonic_config, '--help'])
    assert result.exception is None
    assert result.exit_code == 0
    assert "Usage: tectonic [OPTIONS] LAB_EDITION_FILE COMMAND [ARGS]..." in result.output

@responses.activate
def test_tectonic_deploy(mocker, monkeypatch,
                           base_tectonic_path, ansible_path, labs_path,
                           tectonic_config,
                           lab_edition_file,
                           ec2_client,
                           aws_secrets):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]
    extravars={"ansible_no_target_syslog" : cfg["config"]["keep_ansible_logs"] == "no" }
    monitor_type = open(lab_edition_file,"r").readlines()[2].split("-")[1].rstrip()  

    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets

    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(Deployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(Deployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_terraform = mocker.patch.object(tectonic.deployment.Deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'deploy', '--force'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )
    if platform == "aws":
        assert result.exception is None
        assert result.exit_code == 0
        assert mock_terraform.call_count == 2
        mock_terraform.assert_has_calls([
            mocker.call(f"{base_tectonic_path}/terraform/modules/gsi-lab-aws",
                        variables=mocker.ANY,
                        resources=None),
            mocker.call(f"{base_tectonic_path}/services/terraform/services-aws",
                        variables=mocker.ANY,
                        resources=None),
        ])
        if monitor_type == "traffic": 
            assert len(mock_ansible.mock_calls) == 7
            mock_ansible.assert_has_calls([
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars, 
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/ansible/configure_services.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/elastic/agent_manage.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/trainees.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{labs_path}/test-{monitor_type}/ansible/after_clone.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
            ])
            assert ("Deploying Cyber Range instances...\n"
                    "Deploying Cyber Range services...\n"
                    "Waiting for services to boot up...\n"
                    "Configuring services...\n"
                    "Waiting for machines to boot up...\n"
                    "Configuring student access...\n"
                    "Running after-clone configuration...\n"
                    "Getting Cyber Range information...\n"
                ) in result.output
        elif monitor_type == "endpoint":
            assert len(mock_ansible.mock_calls) == 7
            mock_ansible.assert_has_calls([
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/ansible/configure_services.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/trainees.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{labs_path}/test-{monitor_type}/ansible/after_clone.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/elastic/endpoint_install.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
            ])
            assert ("Deploying Cyber Range instances...\n"
                    "Deploying Cyber Range services...\n"
                    "Waiting for services to boot up...\n"
                    "Configuring services...\n"
                    "Waiting for machines to boot up...\n"
                    "Configuring student access...\n"
                    "Running after-clone configuration...\n"
                    "Configuring elastic agents...\n"
                    "Getting Cyber Range information...\n"
                ) in result.output
        assert "┌──────────────────────────────────┬────────────────────────┐" in result.output
        assert "│               Name               │         Value          │" in result.output
        assert "├──────────────────────────────────┼────────────────────────┤" in result.output
        assert "│        Student Access IP         │     " in result.output
        assert "│        Teacher Access IP         │     " in result.output
        assert "│            Kibana URL            │ https://10.0.0.31:5601 │" in result.output
        assert "│ Kibana user (username: password) │   elastic: password    │" in result.output
        assert "└──────────────────────────────────┴────────────────────────┘" in result.output
        
    elif platform == "libvirt":
        assert result.exception is None
        assert result.exit_code == 0
        assert mock_terraform.call_count == 2
        mock_terraform.assert_has_calls([
            mocker.call(f"{base_tectonic_path}/services/terraform/services-libvirt",
                    variables=mocker.ANY,
                    resources=None),
            mocker.call(f"{base_tectonic_path}/terraform/modules/gsi-lab-libvirt",
                        variables=mocker.ANY,
                        resources=None),
        ])
        if monitor_type == "traffic":
            assert len(mock_ansible.mock_calls) == 7
            mock_ansible.assert_has_calls([
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/ansible/configure_services.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/elastic/agent_manage.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/trainees.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{labs_path}/test-{monitor_type}/ansible/after_clone.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
            ])
            assert ("Deploying Cyber Range services...\n"
                "Waiting for services to boot up...\n"
                "Configuring services...\n"
                "Deploying Cyber Range instances...\n"
                "Waiting for machines to boot up...\n"
                "Configuring student access...\n"
                "Running after-clone configuration...\n"
                "Getting Cyber Range information...\n"
            ) in result.output
        elif monitor_type == "endpoint":
            assert len(mock_ansible.mock_calls) == 7
            mock_ansible.assert_has_calls([
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/ansible/configure_services.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/trainees.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{labs_path}/test-{monitor_type}/ansible/after_clone.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{ansible_path}/wait_for_connection.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/elastic/endpoint_install.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
            ])
            assert ("Deploying Cyber Range services...\n"
                "Waiting for services to boot up...\n"
                "Configuring services...\n"
                "Deploying Cyber Range instances...\n"
                "Waiting for machines to boot up...\n"
                "Configuring student access...\n"
                "Running after-clone configuration...\n"
                "Configuring elastic agents...\n"
                "Getting Cyber Range information...\n"
            ) in result.output
        assert "┌──────────────────────────────────┬─────────────────────────┐" in result.output
        assert "│               Name               │          Value          │" in result.output
        assert "├──────────────────────────────────┼─────────────────────────┤" in result.output
        assert "│            Kibana URL            │ https://10.0.0.130:5601 │" in result.output
        assert "│ Kibana user (username: password) │    elastic: password    │" in result.output
        assert "└──────────────────────────────────┴─────────────────────────┘" in result.output
    assert "Student users:" in result.output
    assert "┌───────────┬──────────────┐" in result.output
    assert "│  Username │   Password   │" in result.output
    assert "├───────────┼──────────────┤" in result.output
    assert "│ trainee01 │ p5bABWxM6xMm │" in result.output
    assert "└───────────┴──────────────┘" in result.output

@responses.activate
def test_tectonic_destroy(mocker, monkeypatch,
                            base_tectonic_path, ansible_path, labs_path,
                            tectonic_config,
                            lab_edition_file,
                            ec2_client,
                            aws_secrets):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]
    extravars={"ansible_no_target_syslog" : cfg["config"]["keep_ansible_logs"] == "no" }
    monitor_type = open(lab_edition_file,"r").readlines()[2].split("-")[1].rstrip()  

    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)

    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(Deployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(Deployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    mock_terraform = mocker.patch.object(tectonic.deployment.Deployment, "terraform_destroy")

    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=[ '--config', tectonic_config, lab_edition_file,
                                 'destroy', '--force'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )
    assert result.exception is None
    assert result.exit_code == 0

    assert mock_terraform.call_count == 2
    if platform == "aws":
        mock_terraform.assert_has_calls([
            mocker.call(f"{base_tectonic_path}/services/terraform/services-aws",
                        variables=mocker.ANY,
                        resources=None),
            mocker.call(f"{base_tectonic_path}/terraform/modules/gsi-lab-aws",
                        variables=mocker.ANY,
                        resources=None),
        ])
        mock_ansible.assert_not_called()
        assert ("Destroying Cyber Range services...\n"
            "Destroying Cyber Range instances...\n") == result.output
    elif platform == "libvirt":
        mock_terraform.assert_has_calls([
            mocker.call(f"{base_tectonic_path}/terraform/modules/gsi-lab-libvirt",
                variables=mocker.ANY,
                resources=None),
            mocker.call(f"{base_tectonic_path}/services/terraform/services-libvirt",
                        variables=mocker.ANY,
                        resources=None),
        ])
        if monitor_type == "traffic":
            assert len(mock_ansible.mock_calls) == 1
            mock_ansible.assert_has_calls([
                mocker.call(inventory=mocker.ANY,
                    playbook=f"{base_tectonic_path}/services/elastic/agent_manage.yml",
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars=extravars,
                ),
            ])
        assert ("Destroying Cyber Range instances...\n"
            "Destroying Cyber Range services...\n") == result.output
    print(result.output)


@responses.activate
def test_tectonic_create_images(mocker,
                                  monkeypatch,
                                  base_tectonic_path,
                                  tectonic_config,
                                  lab_edition_file,
                                  ec2_client,
                                  aws_secrets):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]

    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )

    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)

    mock_packer_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_packer_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'create-images', '--packetbeat', '--elastic'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0

    cr_packer_file=f"{base_tectonic_path}/image_generation/create_image.pkr.hcl"
    services_packer_file=f"{base_tectonic_path}/services/image_generation/create_image.pkr.hcl"
    assert mock_packer_cmd.call_count == 2
    mock_packer_cmd.assert_has_calls([
        mocker.call("init", services_packer_file),
        mocker.call("init", cr_packer_file),
    ])
    assert mock_packer_build.call_count == 2
    mock_packer_build.assert_has_calls([
        mocker.call(services_packer_file, var=mocker.ANY),
        mocker.call(cr_packer_file, var=mocker.ANY),
    ])
    assert ("Creating services images ...\n"
            "Creating base images...\n") in result.output


@responses.activate
def test_tectonic_list(mocker,
                         monkeypatch,
                         base_tectonic_path,
                         tectonic_config,
                         lab_edition_file,
                         ec2_client,
                         aws_secrets):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]
    monitor_type = open(lab_edition_file,"r").readlines()[2].split("-")[1].rstrip() 

    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"_manage_packetbeat",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(Deployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(Deployment,"_get_service_info",return_value=[{"agents_status": {"online": 2,"error": 0,"inactive": 0,"offline": 0,"updating": 0,"unenrolled": 0,"degraded": 0,"enrolling": 0,"unenrolling": 0 }}])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)

    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'list'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0
    assert "Getting Cyber Range status..." in result.output
    if platform == "aws":
        assert "┌─────────────────────────────┬─────────┐" in result.output
        assert "│             Name            │  Status │" in result.output
        assert "├─────────────────────────────┼─────────┤" in result.output
        assert "│   udelar-lab01-1-attacker   │ RUNNING │" in result.output
        assert "│   udelar-lab01-1-victim-1   │ RUNNING │" in result.output
        assert "│   udelar-lab01-1-victim-2   │ RUNNING │" in result.output
        assert "│    udelar-lab01-1-server    │ RUNNING │" in result.output
        assert "│ udelar-lab01-student_access │ RUNNING │" in result.output
        assert "│ udelar-lab01-teacher_access │ RUNNING │" in result.output
        assert "└─────────────────────────────┴─────────┘" in result.output
    elif platform == "libvirt":
        assert "┌─────────────────────────┬─────────┐" in result.output
        assert "│           Name          │  Status │" in result.output
        assert "├─────────────────────────┼─────────┤" in result.output
        assert "│ udelar-lab01-1-attacker │ RUNNING │" in result.output
        assert "│ udelar-lab01-1-victim-1 │ RUNNING │" in result.output
        assert "│ udelar-lab01-1-victim-2 │ RUNNING │" in result.output
        assert "│  udelar-lab01-1-server  │ RUNNING │" in result.output
        assert "└─────────────────────────┴─────────┘" in result.output
    assert "Getting Services status..." in result.output
    if monitor_type == "traffic":
        assert "┌─────────────────────────┬─────────┐" in result.output
        assert "│           Name          │  Status │" in result.output
        assert "├─────────────────────────┼─────────┤" in result.output
        assert "│   udelar-lab01-elastic  │ RUNNING │" in result.output
        assert "│ udelar-lab01-packetbeat │ RUNNING │" in result.output
        assert "└─────────────────────────┴─────────┘" in result.output
    elif monitor_type == "endpoint":
        assert "┌────────────────────────────┬─────────┐" in result.output
        assert "│            Name            │  Status │" in result.output
        assert "├────────────────────────────┼─────────┤" in result.output
        assert "│    udelar-lab01-elastic    │ RUNNING │" in result.output
        assert "│   elastic-agents-online    │    2    │" in result.output
        assert "│    elastic-agents-error    │    0    │" in result.output
        assert "│  elastic-agents-inactive   │    0    │" in result.output
        assert "│   elastic-agents-offline   │    0    │" in result.output
        assert "│  elastic-agents-updating   │    0    │" in result.output
        assert "│ elastic-agents-unenrolled  │    0    │" in result.output
        assert "│  elastic-agents-degraded   │    0    │" in result.output
        assert "│  elastic-agents-enrolling  │    0    │" in result.output
        assert "│ elastic-agents-unenrolling │    0    │" in result.output
        assert "└────────────────────────────┴─────────┘" in result.output

@responses.activate
def test_tectonic_start(monkeypatch,
                          tectonic_config,
                          lab_edition_file,
                          ec2_client,
                          aws_secrets,
                          libvirt_client):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]

    responses.add(responses.GET,
        'https://api.elastic-cloud.com/api/v1/regions/us-east-1/stack/versions?show_deleted=false',
        json={"stacks": [{"version": "8.10.4", "template": {
            "template_version": "8.10.4-0000001236"}},
                        {"version": "7.17.16", "template": {
                            "template_version": "7.17.16-0000001285"}}]},
        status=200
    )
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )

    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)


    instance_name="udelar-lab01-1-attacker"
    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'start',  '--force', '-i', '1', '-g', 'attacker'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0

    if platform == "aws":
        instance = ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [instance_name]}])["Reservations"][0][
            "Instances"][0]
        assert instance["State"]["Name"] == "running"

        # Attacker machine was stopped in aws, shut it down
        instance_id = ec2_client.describe_instances(
            Filters=[{"Name": "tag:Name", "Values": [instance_name]}])["Reservations"][0][
                "Instances"][0]["InstanceId"]
        ec2_client.stop_instances(InstanceIds=[instance_id])
    else:
        # TODO: Cannot check libvirt domain status with a new instance
        # of libvirt client
        pass

    assert result.output == "Booting up instance udelar-lab01-1-attacker...\n"


@responses.activate
def test_tectonic_shutdown(monkeypatch,
                             tectonic_config,
                             lab_edition_file,
                             ec2_client,
                             aws_secrets,
                             libvirt_client):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]

    responses.add(responses.GET,
        'https://api.elastic-cloud.com/api/v1/regions/us-east-1/stack/versions?show_deleted=false',
        json={"stacks": [{"version": "8.10.4", "template": {
            "template_version": "8.10.4-0000001236"}},
                        {"version": "7.17.16", "template": {
                            "template_version": "7.17.16-0000001285"}}]},
        status=200
    )
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )

    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)


    instance_name="udelar-lab01-1-attacker"
    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'shutdown',  '--force', '-i', '1', '-g', 'attacker'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0

    if platform == "aws":
        instance = ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [instance_name]}])["Reservations"][0][
            "Instances"][0]
        assert instance["State"]["Name"] == "stopped"
    else:
        # TODO: Cannot check libvirt domain status with a new instance
        # of libvirt client
        pass

    assert result.output == "Shutting down instance udelar-lab01-1-attacker...\n"


@responses.activate
def test_tectonic_reboot(monkeypatch,
                           tectonic_config,
                           lab_edition_file,
                           ec2_client,
                           aws_secrets,
                           libvirt_client):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]

    responses.add(responses.GET,
        'https://api.elastic-cloud.com/api/v1/regions/us-east-1/stack/versions?show_deleted=false',
        json={"stacks": [{"version": "8.10.4", "template": {
            "template_version": "8.10.4-0000001236"}},
                        {"version": "7.17.16", "template": {
                            "template_version": "7.17.16-0000001285"}}]},
        status=200
    )
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )

    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)

    instance_name="udelar-lab01-1-attacker"
    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'reboot',  '--force', '-i', '1', '-g', 'attacker'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0

    if platform == "aws":
        # TODO: Find a better way of testing that the machine actually rebooted
        instance = ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [instance_name]}])["Reservations"][0][
            "Instances"][0]
        assert instance["State"]["Name"] == "running"
    else:
        # TODO: Cannot check libvirt domain status with a new instance
        # of libvirt client
        pass

    assert result.output == "Rebooting instance udelar-lab01-1-attacker...\n"



@responses.activate
def test_tectonic_console(mocker,
                            monkeypatch,
                            tectonic_config,
                            lab_edition_file,
                            ec2_client,
                            aws_secrets):
    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]

    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    def fabric_shell_aws(connection, **kwargs):
        """ Mocks fabric.Connection.shell()."""
        assert connection.original_host == "10.0.0.28"
        assert connection.user == "ubuntu"
        assert isinstance(connection.gateway, fabric.Connection)
        # This raises an exception if the original_host is not an ipaddr:
        socket.inet_aton(connection.gateway.original_host)
        assert connection.gateway.user == "ubuntu"
        return invoke.runners.Result()
    def fabric_shell_libvirt(connection, **kwargs):
        """ Mocks fabric.Connection.shell()."""
        assert connection.original_host == "10.0.1.25"
        assert connection.user == "ubuntu"
        assert connection.gateway is None
        return invoke.runners.Result()

    if platform == "aws":
        monkeypatch.setattr(fabric.Connection, "shell", fabric_shell_aws)
    else:
        monkeypatch.setattr(fabric.Connection, "shell", fabric_shell_libvirt)

    spy = mocker.spy(fabric.Connection, "shell")

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'console', '-i', '1', '-g', 'attacker'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0

    spy.assert_called_once()
    assert result.output == "Connecting to machine udelar-lab01-1-attacker...\n"

@responses.activate
def test_tectonic_run_ansible(mocker,
                                test_data_path,
                                tectonic_config,
                                lab_edition_file):
    responses.add(responses.GET,
        'https://api.elastic-cloud.com/api/v1/regions/us-east-1/stack/versions?show_deleted=false',
        json={"stacks": [{"version": "8.10.4", "template": {
            "template_version": "8.10.4-0000001236"}},
                        {"version": "7.17.16", "template": {
                            "template_version": "7.17.16-0000001285"}}]},
        status=200
    )
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )

    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    monitor_type = open(lab_edition_file,"r").readlines()[2].split("-")[1].rstrip() 

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'run-ansible', '--force'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    extravars={"ansible_no_target_syslog" : cfg["config"]["keep_ansible_logs"] == "no" }

    assert result.exception is None
    assert result.exit_code == 0
    mock.assert_called_once_with(inventory=mocker.ANY,
                                 playbook=f"{test_data_path}/labs/test-{monitor_type}/ansible/after_clone.yml",
                                 quiet=False,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars=extravars,
                                )


@responses.activate
def test_tectonic_student_access(mocker,
                                   ansible_path,
                                   tectonic_config,
                                   lab_edition_file):
    responses.add(responses.GET,
        'https://api.elastic-cloud.com/api/v1/regions/us-east-1/stack/versions?show_deleted=false',
        json={"stacks": [{"version": "8.10.4", "template": {
            "template_version": "8.10.4-0000001236"}},
                        {"version": "7.17.16", "template": {
                            "template_version": "7.17.16-0000001285"}}]},
        status=200
    )
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )

    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'student-access', '--force'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    cfg = ConfigParser()
    cfg.read(tectonic_config)
    extravars={"ansible_no_target_syslog" : cfg["config"]["keep_ansible_logs"] == "no" }

    assert result.exception is None
    assert result.exit_code == 0
    mock.assert_called_once_with(inventory=mocker.ANY,
                                 playbook=f"{ansible_path}/trainees.yml",
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars=extravars,
                                )
    assert (result.output == (
        "Configuring student access...\n\n"
        "Student users:\n"
        "┌───────────┬──────────────┐\n"
        "│  Username │   Password   │\n"
        "├───────────┼──────────────┤\n"
        "│ trainee01 │ p5bABWxM6xMm │\n"
        "└───────────┴──────────────┘\n"
    ))


@responses.activate
def test_tectonic_recreate(mocker, monkeypatch,
                             base_tectonic_path, ansible_path, labs_path,
                             tectonic_config,
                             lab_edition_file,
                             ec2_client,
                             aws_secrets):

    # Get the platform from the config file
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    extravars={"ansible_no_target_syslog" : cfg["config"]["keep_ansible_logs"] == "no" }
    monitor_type = open(lab_edition_file,"r").readlines()[2].split("-")[1].rstrip() 
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(Deployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(Deployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_terraform = mocker.patch.object(tectonic.deployment.Deployment, "terraform_recreate")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--config', tectonic_config, lab_edition_file,
                                 'recreate', '--force', '-i', '1', '-g', 'victim', '-c', '2'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )
    assert result.exception is None
    assert result.exit_code == 0

    mock_terraform.assert_called_once_with(mocker.ANY)

    if monitor_type == "endpoint":
        assert len(mock_ansible.mock_calls) == 5
        mock_ansible.assert_has_calls([
            mocker.call(inventory=mocker.ANY,
                playbook=f"{ansible_path}/wait_for_connection.yml",
                quiet=True,
                verbosity=0,
                event_handler=mocker.ANY,
                extravars=extravars,
            ),
            mocker.call(inventory=mocker.ANY,
                playbook=f"{ansible_path}/trainees.yml",
                quiet=True,
                verbosity=0,
                event_handler=mocker.ANY,
                extravars=extravars,
            ),
            mocker.call(inventory=mocker.ANY,
                playbook=f"{labs_path}/test-{monitor_type}/ansible/after_clone.yml",
                quiet=True,
                verbosity=0,
                event_handler=mocker.ANY,
                extravars=extravars,
            ),
            mocker.call(inventory=mocker.ANY,
                playbook=f"{ansible_path}/wait_for_connection.yml",
                quiet=True,
                verbosity=0,
                event_handler=mocker.ANY,
                extravars=extravars,
            ),
            mocker.call(inventory=mocker.ANY,
                playbook=f"{base_tectonic_path}/services/elastic/endpoint_install.yml",
                quiet=True,
                verbosity=0,
                event_handler=mocker.ANY,
                extravars=extravars,
            ),
        ])
        assert (result.output == (
            "Recreating machines...\n"
            "Waiting for machines to boot up...\n"
            "Configuring student access...\n"
            "Running after-clone configuration...\n"
            "Configuring elastic agents...\n"
        ))
    else:
        assert len(mock_ansible.mock_calls) == 3
        mock_ansible.assert_has_calls([
            mocker.call(inventory=mocker.ANY,
                        playbook=f"{ansible_path}/wait_for_connection.yml",
                        quiet=True,
                        verbosity=0,
                        event_handler=mocker.ANY,
                        extravars=extravars,
                        ),
            mocker.call(inventory=mocker.ANY,
                        playbook=f"{ansible_path}/trainees.yml",
                        quiet=True,
                        verbosity=0,
                        event_handler=mocker.ANY,
                        extravars=extravars,
                        ),
            mocker.call(inventory=mocker.ANY,
                        playbook=f"{labs_path}/test-{monitor_type}/ansible/after_clone.yml",
                        quiet=True,
                        verbosity=0,
                        event_handler=mocker.ANY,
                        extravars=extravars,
                        ),
        ])
        assert (result.output == (
            "Recreating machines...\n"
            "Waiting for machines to boot up...\n"
            "Configuring student access...\n"
            "Running after-clone configuration...\n"
        ))


@responses.activate
def test_tectonic_info(mocker, monkeypatch,
                         tectonic_config,
                         lab_edition_file,
                         ec2_client,
                         aws_secrets):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(Deployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(Deployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    cfg = ConfigParser()
    cfg.read(tectonic_config)
    platform = cfg["config"]["platform"]
    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--debug', '--config', tectonic_config, lab_edition_file,
                                 'info'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert result.exit_code == 0
    assert "Getting Cyber Range information..." in result.output
    if platform == "aws":
        assert "┌──────────────────────────────────┬────────────────────────┐" in result.output
        assert "│               Name               │         Value          │" in result.output
        assert "├──────────────────────────────────┼────────────────────────┤" in result.output
        assert "│        Student Access IP         │     " in result.output
        assert "│        Teacher Access IP         │     " in result.output
        assert "│                                  │                        │" in result.output
        assert "│            Kibana URL            │ https://10.0.0.31:5601 │" in result.output
        assert "│ Kibana user (username: password) │   elastic: password    │" in result.output
        assert "└──────────────────────────────────┴────────────────────────┘" in result.output
    elif platform == "libvirt":
        assert "┌──────────────────────────────────┬─────────────────────────┐" in result.output
        assert "│               Name               │          Value          │" in result.output
        assert "├──────────────────────────────────┼─────────────────────────┤" in result.output
        assert "│            Kibana URL            │ https://10.0.0.130:5601 │" in result.output
        assert "│ Kibana user (username: password) │    elastic: password    │" in result.output
        assert "└──────────────────────────────────┴─────────────────────────┘" in result.output
    assert "Student users:" in result.output
    assert "┌───────────┬──────────────┐" in result.output
    assert "│  Username │   Password   │" in result.output
    assert "├───────────┼──────────────┤" in result.output
    assert "│ trainee01 │ p5bABWxM6xMm │" in result.output
    assert "└───────────┴──────────────┘" in result.output

def test_instance_range_parsing():
    parser = tectonic.cli.NumberRangeParamType()
    assert parser.convert("1", "-i", None) == [1]
    assert parser.convert([5,1,2], "-i", None) == [1,2,5]
    assert parser.convert("1,8,3-6", "-i", None) == [1,3,4,5,6,8]
    assert parser.convert("1,,3", "-i", None) == [1,3]

    with pytest.raises(click.BadParameter) as exception:
        parser.convert("1,a", "-i", None)
    assert "Cannot parse a" in str(exception.value)


def test_range_to_str():
    assert tectonic.cli.range_to_str(None) == ""
    assert tectonic.cli.range_to_str([1]) == "1"
    assert tectonic.cli.range_to_str([1,3,4]) == "1, 3, and 4"
    assert tectonic.cli.range_to_str([1,3,4,5,7]) == "1, from 3 to 5, and 7"
    assert tectonic.cli.range_to_str([1,2,3,4,5,6,7]) == "from 1 to 7"


def test_confirm_machines(monkeypatch, capsys, description):
    ctx = click.Context(click.Command('tectonic'), 
                        obj={'description': description})

    # Use more instances and copies, so we can test more conditions
    ctx.obj["description"].instance_number = 5
    ctx.obj["description"].guest_settings["victim"]["copies"] = 4

    test_cases = [
        { "expected": "Testing all machines, on all instances.",
        },
        { "instances": [10,11,12],
          "expected": "Testing all machines, on all instances.",
        },
        { "instances": [1,2,3,6],
          "guests": ("attacker",),
          "expected": "Testing the attacker, on instances from 1 to 3.",
        },
        { "guests": ("teacher_access", "student_access", "packetbeat"),
          "expected": "Testing the teacher access, the student access and the packetbeat.",
        },
        { "instances": [1],
          "guests": ("victim",),
          "expected": "Testing all copies of the victim, on instance 1.",
        },
        { "guests": ("attacker", "victim", "server"),
          "expected": "Testing the attacker, all copies of the victim and the server, on all instances.",
        },
        { "guests": ("attacker", "victim"),
          "copies": [2],
          "expected": "Testing copy 2 of the victim, on all instances.",
        },
        { "guests": ("attacker", "victim"),
          "copies": [2,3,4],
          "expected": "Testing copies from 2 to 4 of the victim, on all instances.",
        },
    ]

    for test in test_cases:
        monkeypatch.setattr('sys.stdin', io.StringIO("y"))
        tectonic.cli.confirm_machines(ctx,
                                        test.get("instances"),
                                        test.get("guests"),
                                        test.get("copies"),
                                        "Testing")
        captured = capsys.readouterr()
        assert test.get("expected", "") in captured.out

    monkeypatch.setattr('sys.stdin', io.StringIO("y"))
    tectonic.cli.confirm_machines(ctx, None, ("attacker",), [2], "Testing")
    captured = capsys.readouterr()
    assert captured.out == ""

    # Restore description values
    ctx.obj["description"].instance_number = 2
    ctx.obj["description"].guest_settings["victim"]["copies"] = 2

@responses.activate
def test_get_parameters(mocker, monkeypatch,
                         tectonic_config,
                         lab_edition_file,
                         ec2_client,
                         aws_secrets):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(Deployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(Deployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    responses.add(responses.GET,
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html",
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    runner = CliRunner()
    result = runner.invoke(cli=tectonic_cli,
                           args=['--debug', '--config', tectonic_config, lab_edition_file,
                                 'show-parameters'],
                           env={'GITLAB_USERNAME': 'test', 'GITLAB_ACCESS_TOKEN': '1234'}
                           )

    assert result.exception is None
    assert "┌──────────┬─────────────────────┐" in result.output
    assert "│ Instance │      Parameters     │" in result.output
    assert "├──────────┼─────────────────────┤" in result.output
    assert "│    1     │ {'flags': 'Flag 2'} │" in result.output
    assert "└──────────┴─────────────────────┘" in result.output 
