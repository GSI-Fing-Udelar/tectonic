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

#### Ubuntu Linux
- Install Python 3.10 (or newer) and other dependencies:
  ```bash
  sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential pkg-config libvirt-dev
  ```

- Install IaC tools:
  - Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) and [Packer](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli)
    ```bash
    sudo apt update && sudo apt install -y gnupg software-properties-common
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update
    sudo apt install -y terraform packer
    ```
    
- Install Tectonic Python package in a python virtual environment:
  ```bash
  python3 -m venv ~/.tectonic
  source ~/.tectonic/bin/activate
  python3 -m pip install tectonic-cyberrange
  ```
  * Each time you login, you should execute `source ~/.tectonic/bin/activate` to enter the tectonic virtual environment. You can execute `deactivate` to exit the environment and return to a normal shell.

- Configure ssh private/public key
  - If you do not have an ssh public/private key pair configured in ~/.ssh/ directory, generate a new pair using the command `ssh-keygen` 

- Base platforms configurations:
  - Docker:
    - Install docker following [instructions](https://docs.docker.com/engine/install/)
    ```bash
    sudo apt install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli
    sudo usermod -a -G docker <current_user>
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
    - Install libvirt and all dependencies:
    ```bash
    sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients xsltproc bridge-utils xorriso genisoimage
    ```
    - Add current user to the libvirt group
      ```bash
      sudo usermod -a -G libvirt <current_user>
      ```
    - Verify that there is a network named `default' of type NAT:
      ```
      virsh net-list --all
      ```
      If that network does not exist, then create it by applying the following steps:
        - Create an network.xml file with the network definition containing the following content:
          ```
          <network>
            <name>default</name>
            <forward mode="nat">
              <nat>
                <port start="1024" end="65535"/>
              </nat>
            </forward>
            <bridge name="virbr0" stp="on" delay="0"/>
            <ip address="192.168.124.1" netmask="255.255.255.0">
              <dhcp>
                <range start="192.168.124.2" end="192.168.124.254"/>
              </dhcp>
            </ip>
          </network>
          ```
        - Create and start network:
          ```
          virsh net-define network.xml
          virsh net-start default
          virsh net-autostart default
          ```
    - Create the `libvirt_storage_pool` volume pool to use in the cyberrange. For example, a dir backed pool named `tectonic`:
      ```bash
        sudo mkdir -p <directory>
        sudo chmod 0775 <directory>
        sudo chgrp libvirt <directory>
        virsh -c qemu:///system pool-create-as tectonic dir --target=<directory>
      ```

    - Create a bridge named as the `libvirt_bridge` ini file parameter (`tectonic` by default):
      ```bash
      nmcli con add type bridge ifname tectonic
      nmcli con up bridge-tectonic
      ```
      * This bridge should connect to an external network for student entry point access.
      * It is ok to have a dummy empty bridge for testing.
    - Install xsltproc and mkisofs
      ```bash
      sudo apt-get install xsltproc mkisofs
      ```
    - It might be necessary to modify the AppArmor configuration. If you have "permission denied" problems, try disabling it:
      ```bash
	  systemctl disable --now apparmor
	  ```

	  + To permamently disable AppArmor, edit `/etc/default/grub` and add the line: 
	    ```
		GRUB_CMDLINE_LINUX="apparmor=0"
		```

	    Then run `grub-update` and reboot.

#### Rocky Linux
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
      sudo dnf install -y libxslt genisoimage
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
	Unfortunately, Libvirt is not yet supported for MacOS installations.

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
      - You can run libvirt on a Linux VM in WSL 2 if you have nested
        virtualization enabled. Configurations are applied within the
        Linux installed on WSL

- On Linux WSL 2
  - Follow the Tectonic installation guides for Ubuntu/RHEL Linux until the step where the ssh key is generated
  - If you want to use AWS or Libvirt then also apply the configurations detailed in the installation guide
