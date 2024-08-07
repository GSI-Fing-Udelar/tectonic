# Tectonic - Example Scenarios

This directory contains two sample scenarios: 
+ **Password Cracking**: An annotated simple scenario with two
  machines.
+ ...


For example, to try the password cracking scenario, set the
`lab_repo_uri` option to point to a copy of this directory (either in
the tectonic ini file or using the `-u` command line option). Then create the base images:

```
tectonic -c <ini_file> ./password_cracking.yml create-images
```

This will create a base image disk (or an AMI in AWS) with the base
configuration of each machine in the scenario (the attacker and the
victim). Afterwards, the scenario can be deployed with:
```
tectonic -c <ini_file> ./password_cracking.yml deploy
```

This will create a clone of each machine for every instance, run the
after-clone playbook and enable student access.

You can combine both steps with:
```
tectonic -c <ini_file> ./password_cracking.yml deploy --images
```


