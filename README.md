# Tectonic - An Academic Cyber Range
[![Regression Tests](https://github.com/GSI-Fing-Udelar/tectonic/actions/workflows/test.yml/badge.svg)](https://github.com/GSI-Fing-Udelar/tectonic/actions/workflows/test.yml)

## Overview
Tectonic is a cyber range designed to provide realistic cybersecurity
scenarios for education and training through the deployment of
networks, systems and applications that can be used to train users on
cybersecurity topics. Key functionalities include customizable network
configurations, real-time monitoring and automated attack simulations.

It incorporates existing tools from the infrastructure as code (IaC)
approach, which allows for the specification of all the components of
a cybersecurity scenario in a declarative manner. This specification
is made in a high-level language that can be interpreted and allows
for the automatic generation of scenarios on the laboratory underlying
platform. Declarative descriptions of the scenarios make them easily
versioned, maintained, and shared, facilitating collaboration with
other institutions and laboratories of this type.

The following figure illustrates various components of the cyber range
solution, the technologies used in the implementation, and the
different use cases carried out by student users and instructors. The
components are organized in five layers, each fulfilling a particular
function in the platform's operation.

<p align="center">
    <img src="https://raw.githubusercontent.com/GSI-Fing-Udelar/tectonic/refs/heads/main/docs/architecture.png" width="500">
</p>

The underlying infrastructure constitutes the real-world
infrastructure on which the systems and networks that form the basis
of a particular scenario are deployed. Currently deployments on the
AWS cloud or on-premises using Libvirt are supported, with more
planned.

To achieve the deployment of the infrastructure in an automated
manner, \textit{Infrastructrue as Code} (IaC) tools are used, such as
Packer, Terraform and Ansible. These tools manage the resources to be
deployed and the configurations to be applied to them. Ansible
playbooks, in particular, are extensively used for configuration.

A Python component orchestrates these tools and manages the life cycle
of the scenarios, including their deployment, elimination, powering
on, powering off, and listing information. The scenarios themselves
are described by a specification that allows users to declare various
aspects, such as the machines to be deployed, the networks used to
connect them, and the configurations to be applied to the machines,
among others.

## Installation Instructions
The following are the requirements to run Tectonic:

- Linux, Mac OS or WSL
- Python 3.10 or newer
- Poetry
- Terraform 1.6
- Packer 1.9
- Docker
- Libvirt
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) 

Please see the [detailed instructions](https://github.com/GSI-Fing-Udelar/tectonic/blob/main/docs/installation.md) for more
information.

### Terraform state syncronization
Terraform states are stored locally by default. It is possible to
store them in a gitlab repo (see `gitlab_backend_url` option in the
[ini file configuration](https://github.com/GSI-Fing-Udelar/tectonic/blob/main/docs/ini_config.md)). It is necessary to have
Maintainer privileges on this repo and a GitLab access token. There
are two types of access token: personal or project-based. If the
latter is used, it must be associated with the project where the
states are stored.

### Python environment setup

You can install this module using the following command:

```bash
python3 -m pip install poetry
poetry install
```


## Tectonic Configuration File
Tectonic behaviour can be configured using an ini file with a
`config` section. You can find an example configuration file with the
default values [here](https://github.com/GSI-Fing-Udelar/tectonic/blob/main/tectonic.ini). Please see the [ini
file documentation](docs/ini_config.md) for details on the available
options.


## Lab Configuration
The lab configuration is divided in two: a **scenario specification**
that holds a static description of the lab that can be shared and
reused, and information specific to a particular **lab edition** that
defines things such as number of instances to deploy, public SSH keys
for the teachers, etc.

The scenario specification consists of the following resources:

* A scenario description file in YAML syntax (required).
* Ansible playbooks for *base image* installation and *after-clone*
  configurations, and optional files in the `ansible` directory.
* Elastic and kibana policies and resources, in the `elastic`
  directory, if using elastic for evaluation.
* SSH public keys for admin access to the machines in the `ssh`
  directory.

The lab edition file 

Please check the [description documentation](https://github.com/GSI-Fing-Udelar/tectonic/blob/main/docs/description.md) for
more details. The [examples](https://github.com/GSI-Fing-Udelar/tectonic/blob/main/examples/) directory contains some
example scenarios.

## Running Tectonic

To deploy a scenario run:
```
tectonic -c <ini_conf_file> <lab_edition_file> deploy
```

To destroy a scenario use the `destroy` command. 

See `tectonic --help` for a full list of options, and `tectonic
<command> -h` for help on individual commands.

## Disclaimer About Platforms

Tectonic provides support for scenario deployments using Docker as the base platform. However, it is important to note that using Docker as base platform in production environments is not recommended since Tectonic deploys containers in privileged mode. This means that when a user has root access within a container, they can also gain root access to the host system, which can create significant security issues. Therefore, caution is crucial when using Docker as a base platform, especially in scenarios involving attacks. It is advisable to utilize Docker primarily for the generation and testing of new scenarios. For production environments, we recommend to utilize Libvirt or AWS as base platform, both of which are fully supported by Tectonic.

## Authors

Tectonic was created by [Grupo de Seguridad
Informática](https://www.fing.edu.uy/inco/grupos/gsi) of [Universidad
de la República Uruguay](https://udelar.edu.uy/).

Please contact us at <tectonic@fing.edu.uy>.

## License

Tectonic is licensed under the GNU General Public License v3.0 or
later. See LICENSE to see the full text.






