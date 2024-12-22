## Installation

### Requirements
- SO: Linux or Mac OS
- Python and pip: version 3.10 or newer.
- Packages needed to build: build-essentials, pkg-config, libvirt-dev/libvirt-devel. Keep in mind that the name of the packages may vary depending on the Linux distribution.
- IaC Tools: Terraform and Packer
- Base platforms: Libvirt or Docker
- AWS credentials and AWS CLI (for AWS deployment)
- Other tools: [xsltproc](http://xmlsoft.org/xslt/xsltproc.html) command line tool (for Libvirt deployments)

### Instructions

#### Linux Ubuntu
- Install Python 3.10 (or newer) and pip
  ```bash
  sudo apt-get install -y python3 python3-pip
  ```

- Install packages needed to build Tectonic
  ```bash
  sudo apt-get install -y build-essential pkg-config libvirt-dev python3-dev
  ```
- Install IaC tools:
  - Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
    ```bash
    sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update
    sudo apt-get install -y terraform
    ```

  - Install [Packer](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli)
    ```bash
    sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update
    sudo apt-get install -y packer
    ```
    Note: steps 1-4 should not be necessary since the Hashicorp repository should already be set up if you installed Terraform following the instructions. 

- Install Tectonic Python package:
  ```bash
  python3 -m pip install tectonic-cyberrange
  ```

- Configure ssh private/public key
  - If you do not have an ssh public/private key pair configured in ~/.ssh/ directory, generate a new pair using the command `ssh-keygen` 

- Base platforms configurations:
  - Docker:
    - Install docker following [instructions](https://docs.docker.com/engine/install/)
    ```bash
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli
    ```

  - AWS:
    - Configure credentials:
      - Create AWS access key, see [official documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey).
      - Save credentials in environment variables:
      ```bash
      export AWS_ACCESS_KEY_ID=<aws_access_key_id>
      export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key>
      ```
    - Install [aws cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html):
      ```bash
      curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
      unzip awscliv2.zip
      sudo ./aws/install
      ```

  - Libvirt:
    - Install libvirt following your distribution specific instructions.
    ```bash
    sudo apt-get install -y qemu-kvm libvirt-daemon-system
    ```
    - Create a volume pool to use in the cyberrange. For example, a dir backed pool named "tectonic":
      ```bash
        virsh -c qemu:///system pool-create-as tectonic dir --target=<directory>
      ```
      * Set the `libvirt_storage_pool` ini config file parameter to this pool name)
    - Create a bridge named as the `libvirt_bridge` ini file parameter:
      ```bash
      nmcli con add type bridge ifname <libvirt_bridge>
      nmcli con up bridge-<libvirt_bridge>
      ```
      * This bridge should connect to an external network for student entry point access.
      * It is ok to have a dummy empty bridge for testing.
    - Install xsltproc
      ```bash
      sudo apt-get install xsltproc
      ```

#### Linux Rocky
- Install Python 3.11 (or newer) and pip
  ```bash
  sudo dnf install -y python3 python3-pip
  ```

- Install packages needed to build Tectonic
  ```bash
  sudo dnf group install -y "Development Tools"
  sudo dnf install -y pkg-config libvirt-devel python3-devel
  ```
- Install IaC tools:
  - Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
    ```bash
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
    sudo dnf install -y terraform
    ```

  - Install [Packer](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli)
    ```bash
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
    sudo dnf install -y packer
    ```
    Note: steps 1-2 should not be necessary since the Hashicorp repository should already be set up if you installed Terraform following the instructions. 

- Install Tectonic Python package:
  ```bash
  python3 -m pip install tectonic-cyberrange
  ```

- Configure ssh private/public key
  - If you do not have an ssh public/private key pair configured in ~/.ssh/ directory, generate a new pair using the command `ssh-keygen` 

- Base platforms configurations:
  - Docker:
    - Install docker following [instructions](https://docs.docker.com/engine/install/)
    ```bash
    sudo dnf -y install dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install -y docker-ce docker-ce-cli
    ```

  - AWS:
    - Configure credentials:
      - Create AWS access key, see [official documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey).
      - Save credentials in environment variables:
      ```bash
      export AWS_ACCESS_KEY_ID=<aws_access_key_id>
      export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key>
      ```
    - Install [aws cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html):
      ```bash
      curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
      unzip awscliv2.zip
      sudo ./aws/install
      ```

  - Libvirt:
    - Install libvirt following your distribution specific instructions.
    ```bash
    sudo dnf install -y qemu-kvm libvirt virt-install
    ```
    - Create a volume pool to use in the cyberrange. For example, a dir backed pool named "tectonic":
      ```bash
      virsh -c qemu:///system pool-create-as tectonic dir --target=<directory>
      ```
      * Set the `libvirt_storage_pool` ini config file parameter to this pool name)
    - Create a bridge named as the `libvirt_bridge` ini file parameter:
      ```bash
      nmcli con add type bridge ifname <libvirt_bridge>
      nmcli con up bridge-<libvirt_bridge>
      ```
      * This bridge should connect to an external network for student entry point access.
      * It is ok to have a dummy empty bridge for testing.
    - Install xsltproc
      ```bash
      sudo dnf install -y libxslt
      ```

#### MacOS
- Install Python 3.10 (or newer) and pip
  ```bash
  brew install python3
  ```
- Install IaC tools:
  - Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
    ```bash
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
    brew upgrade hashicorp/tap/terraform
    ```

  - Install [Packer](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli)
    ```bash
    brew tap hashicorp/tap
    brew install hashicorp/tap/packer
    brew upgrade hashicorp/tap/packer
    ```
    Note: step 1 should not be necessary since the Hashicorp repository should already be set up if you installed Terraform following the instructions. 

- Install Tectonic Python package:
  ```bash
  python3 -m pip install tectonic-cyberrange
  ```

- Configure ssh private/public key
  - If you do not have an ssh public/private key pair configured in ~/.ssh/ directory, generate a new pair using the command `ssh-keygen` 

- Base platforms configurations:
  - Docker:
    - Install Docker Desktop following [instructions](https://docs.docker.com/desktop/setup/install/mac-install/)
    - If you get the following error when running Tectonic:
        ```
        objc[29118]: +[NSMutableString initialize] may have been in progress in another thread when fork() was called.
        ```
        then run:
        ```bash
        export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
        ```

  - AWS:
    - Configure credentials:
      - Create AWS access key, see [official documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey).
      - Save credentials in environment variables:
      ```bash
      export AWS_ACCESS_KEY_ID=<aws_access_key_id>
      export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key>
      ```
    - Install [aws cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html):

  - Libvirt:
    We have not installed libvirt on MacOS so we cannot help you on this point.

#### Windows 10/11
- On Windows
  - Install Linux on WSL 2
    - Install WSL following [instructions](https://learn.microsoft.com/windows/wsl/install)
    - From Microsoft Store install your preferred Linux distro (for example Ubuntu 22.04)

  - Base platforms configurations:
    - Docker:
      - Install Docker Desktop following [instructions](https://docs.docker.com/desktop/setup/install/mac-install/)
      - Enable Docker on your WSL 2 distro. On Docker Desktop go to Configuration -> Resources -> WSL Integration and select your distro

  - AWS:
    - Configurations are applied within the Linux installed on WSL

  - Libvirt:
    Not compatible with Windows

- On Linux WSL 2
  - Follow the Tectonic installation guides for Linux Ubuntu/RHEL until the step where the ssh key is generated
  - If you want to use AWS then also apply the configurations detailed in the installation guide
