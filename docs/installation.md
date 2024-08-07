## Installation

### Requirements
- Linux or Mac OS
- Python 3.11
- Ansible 2.15
- Terraform 1.6
- Packer 1.9
- xsltproc command line tool
- Python modules (see [requirements.txt](./python/requirements.txt))
- GitLab credentials
- Optionally AWS and Elastic Cloud credentials

### Instructions
The following installation instructions are based on CentOS/RHEL distributions. Refer to each software's installation manuals for detailed instructions for your particular operating system distribution.

There are two installation methods:
- [Installation](#installation)
  - [Requirements](#requirements)
  - [Instructions](#instructions)
    - [Manual installation](#manual-installation)
    - [Installation using Ansible](#installation-using-ansible)
  - [Versions support](#versions-support)

#### Manual installation

- Install Python 3.11
  ```
  sudo dnf install -y python3.11
  ```

- Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
  ```
  sudo yum install -y yum-utils
  sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
  sudo yum -y install terraform
  ```

- Install [Packer](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli)
  ```
  sudo yum install -y yum-utils
  sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
  sudo yum -y install packer
  ```
  Note: steps 1 and 2 should not be necessary since the Hashicorp repository should already be set up if you installed Terraform following the instructions. 

- Clone or download this GitLab repository
  ```
  git clone https://gitlab.fing.edu.uy/gsi/cyberrange/tectonic.git
  ```

- Install tectonic python package:
```bash
cd python
python3 -m pip install .
```

or for a development user installation:

```bash
cd python
python3 -m pip install pipenv
pipenv install --dev -e .
```

- Configure GitLab credentials.
  - Gitlab credentials are required for terraform state syncronization.
  - In GitLab go to User Settings -> Access Tokens.
  - Add New Token. Define name, expiration date and select api scope. See [official documentation](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) for detailed instructions.
  - Set `GITLAB_USERNAME` and `GITLAB_ACCESS_TOKEN` environment variables to the value of your GitLab username and the newly created token: 
    ```
    echo "export GITLAB_USERNAME=<gitlab_username>" >> ~/.bashrc
    echo "export GITLAB_ACCESS_TOKEN=<gitlab_access_token>" >> ~/.bashrc
    source ~/.bashrc
    ```
  - Make sure you have at least the maintenter role in the repository where the terraform states will be stored.

- Configure ssh private/public key
  - If you do not have an ssh public/private key pair configured in ~/.ssh/ directory, generate a new pair using the command `ssh-keygen` 

- Configure other services credentials (if required).
  - AWS credentials:
    - Create AWS access key, see [official documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey).
    - Save credentials in environment variables:
    ```
    echo "export AWS_ACCESS_KEY_ID=<aws_access_key_id>" >> ~/.bashrc
    echo "export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key>" >> ~/.bashrc
    source ~/.bashrc
    ```
  - Elastic Cloud credentials:
    - Create Elastic cloud api key, see [official documentation](https://www.elastic.co/guide/en/cloud/current/ec-api-authentication.html).
    - Save credentials in environment variables:
    ```
    echo "export EC_API_KEY=<ec_api_key>" >> ~/.bashrc
    source ~/.bashrc
    ```

- Configure libvirt environment (if required).
  - Create a volume pool to use in the cyberrange. For example, a dir backed pool named "tectonic":
    ```
      virsh -c qemu:///system pool-create-as tectonic dir --target=<directory>
    ```
    * Set the `libvirt_storage_pool` ini config file parameter to this pool name)
  - Create a bridge named as the `libvirt_bridge` ini file parameter:
    ```
    nmcli con add type bridge ifname <libvirt_bridge>
    nmcli con up bridge-<libvirt_bridge>
    ```
    * This bridge should connect to an external network for student entry point access.
    * It is ok to have a dummy empty bridge for testing.


#### Installation using Ansible
- Install Python 3.11
  ```
  sudo dnf install -y python3.11
  ```

- Install [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#pip-install) 
  ```
  python3 -m pip install --user ansible
  ```
- Clone or download this GitLab repository
  ```
  git clone https://gitlab.fing.edu.uy/gsi/cyberrange/tectonic.git
  ```

- Install tectonic using [installation playbook.yml](./installation/playbook.yml):
  ```
  ansible-playbook -i localhost, tectonic/installation/playbook.yml
  ```

### Versions support
Tectonic was tested on the following versions:

| **SO**            | **Terraform** | **Packer** | **Ansible** | **Python** |
|:-----------------:|:-------------:|:----------:|:-----------:|:----------:|
| Kali Linux 2022.2 | 1.5.3         | 1.9.2      | 2.15.2      | 3.11.4     |
| Rocky Linux 8.8   | 1.6.3         | 1.9.4      | 2.15.5      | 3.9.16     |
| Fedora 37         | 1.5.4         | 1.9.2      | 2.14.8      | 3.11.5     |
| Ubuntu 22.04      | 1.6.2         | 1.9.4      | 2.15.5      | 3.10.12    |
