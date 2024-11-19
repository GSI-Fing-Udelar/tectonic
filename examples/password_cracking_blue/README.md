# Password Cracking Blue Team Scenario
This scenario is identical to the password cracking scenario but with a blue team approach. 
The idea is that the attack is executed automatically by Caldera and the student must perform 
a forensic analysis to identify the attack.

The scenario simulates an company internal network and is composed of:

+ A previously compromised Linux machine (A), with the required attack
  tools.
+ A victim workstation (V) to use as target of the attack.

## Scenario objective:
Understand the type of attack executed on the victim machine.


## Scenario resolution
The necessary steps to solve the scenario are as follows:

Analyze the authentications and identify a large number of failed authentications for different users using the ftp service. Subsequently, a successful ssh authentication is identified for the user jtrincav. All this activity has as its source IP the IP 10.0.1.4.

 ```console
 trainee01@victim-1$ less /var/log/auth.log
  ...
  Nov 19 22:30:38 victim-1 vsftpd: pam_listfile(vsftpd:auth): Refused user epilotta for service vsftpd
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): check pass; user unknown
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=epilotta rhost=::ffff:10.0.1.4 
  Nov 19 22:30:38 victim-1 vsftpd: pam_listfile(vsftpd:auth): Refused user oreula for service vsftpd
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): check pass; user unknown
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=oreula rhost=::ffff:10.0.1.4 
  Nov 19 22:30:38 victim-1 vsftpd: pam_listfile(vsftpd:auth): Refused user crosas for service vsftpd
  Nov 19 22:30:38 victim-1 vsftpd: message repeated 2 times: [ pam_listfile(vsftpd:auth): Refused user crosas for service vsftpd]
  Nov 19 22:30:38 victim-1 vsftpd: pam_listfile(vsftpd:auth): Refused user cschurrer for service vsftpd
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): check pass; user unknown
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=crosas rhost=::ffff:10.0.1.4 
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): check pass; user unknown
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=crosas rhost=::ffff:10.0.1.4 
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): check pass; user unknown
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=crosas rhost=::ffff:10.0.1.4 
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): check pass; user unknown
  Nov 19 22:30:38 victim-1 vsftpd: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=cschurrer rhost=::ffff:10.0.1.4 
  
  ...
  Nov 19 22:36:45 victim-1 sshd[1323]: Accepted password for jtrincav from 10.0.1.4 port 57600 ssh2
  Nov 19 22:37:44 victim-1 sshd[1323]: pam_unix(sshd:session): session opened for user jtrincav(uid=1003) by (uid=0)
  Nov 19 22:37:44 victim-1 systemd: pam_unix(systemd-user:session): session opened for user jtrincav(uid=1003) by (uid=0)
  Nov 19 22:37:44 victim-1 systemd-logind[53]: New session 310 of user jtrincav.
  Nov 19 22:37:44 victim-1 sshd[1341]: Received disconnect from 10.0.1.4 port 57600:11: disconnected by user
  Nov 19 22:37:44 victim-1 sshd[1341]: Disconnected from user jtrincav 10.0.1.4 port 57600
  Nov 19 22:37:44 victim-1 sshd[1323]: pam_unix(sshd:session): session closed for user jtrincav
  ...
  ```

Analyzing files in the home directory of user jtrincav. A file flag.txt is identified with last access 2024-11-19 22:36:45.789205532, which coincides with the ssh login date.

  ```console
  trainee01@victim-1$ stat /home/jtrincav/flag.txt 
    File: /home/jtrincav/flag.txt
    Size: 33              Blocks: 8          IO Block: 4096   regular file
  Device: 88h/136d        Inode: 28490183    Links: 1
  Access: (0600/-rw-------)  Uid: ( 1003/jtrincav)   Gid: ( 1003/jtrincav)
  Access: 2024-11-19 22:36:45.789205532 +0000
  Modify: 2024-11-19 22:28:04.530585000 +0000
  Change: 2024-11-19 22:28:05.130599549 +0000
  Birth: 2024-11-19 22:28:04.858592950 +0000
  ```
It is presumed that the malicious actor gained access to the system and obtained the contents of this file.


