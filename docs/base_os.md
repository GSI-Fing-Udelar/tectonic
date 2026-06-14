# Operating Systems

Tectonic supports various operating systems for deploying the machines that make up a scenario. 
The operating systems supported by each platform are listed in the following table.

| Operating System    | AWS | Libvirt | Docker |
|---------------------|-----|---------|--------|
| Rocky 9             | Yes | Yes     | Yes    |
| Rocky 8             | Yes | Yes     | Yes    |
| Ubuntu 22           | Yes | Yes     | Yes    |
| Ubuntu 24           | Yes | Yes     | Yes    |
| Kali Linux          | Yes | Yes*    | Yes    |
| Windows Server 2022 | Yes | No      | No     |

* You must manually download the [Kali Generic Cloud image](https://www.kali.org/get-kali/#kali-cloud), extract it, and convert it from raw format to qcow2. You must then adjust the `tectonic/constant.py` file to specify the path to the base qcow2 image. For the conversion you can use the command: `qemu-img convert -f raw -O qcow2 source.img destination.qcow2`