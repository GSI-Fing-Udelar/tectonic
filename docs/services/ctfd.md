# CTFd
CTFd is a Capture The Flag framework focusing on ease of use and customizability. In Tectonic, CTFd can be deployed as a service in order to implement capture the flag competencies.

### Challenge creation

The main resource in CTFd is an challenge. To create a challenge, follow these steps:

1. Log in with the administrator account.
2. Click the Admin panel tab.
3. Click the Challenges tab and complete with the necessary content (name, description, files, hints, flags, etc.).

For more information, consult the [CTFd documentation](https://docs.ctfd.io/docs/challenges/overview).

### Challenge backup

Once the challenges have been generated and tested, a backup must be created so that Tectonic can automate their import when deploying the scenario. 

For this, the challenge specification defined by the ctfcli tool must be followed, see [documentation](https://github.com/CTFd/ctfcli?tab=readme-ov-file#challenge-specification). A directory with the name of the challenge must be generated, and within this, a challenge.yml file must be created where all the elements of the challenge are described.

To facilitate this task, it is suggested to work on the CTFd machine as follows:
- Generate the challenges from the web.
- Connect to the CTFd machine and navigate to the /opt/challenges directory (you can use tectonic command console).
- For each challenge, create a subdirectory with its name. Inside each subdirectory, create a challenge.yml file with the following content: 
    ```yml
    name: <challenge_name>
    ```
- For each challenge, run: /opt/CTFd/venv/bin/python3 -m ctfcli challenge mirror <challenge_name>

Once the challenge backups were created, copy the generated directories into a `ctfd` directory inside the scenario specification.

Note: ctfcli has some limitations. For example, it's not possible to import or export requirements for flags.

### CTFd bakup

Additionally, you can back up your entire CTFd instance by following the steps documented here [https://docs.ctfd.io/docs/exports/ctfd-exports]. This backup can then be manually imported from the web interface. Keep in mind that doing this will overwrite all the base configuration created by Tectonic (the event, the admin user and their token, and the trainee users), so you'll need to know the password for one of the users you're importing beforehand and also modify the event settings after the import.