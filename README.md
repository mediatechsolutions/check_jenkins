# Check Jenkins

This repository contains some jenkins checks in nagios

## Check modes
* queue_lenght: check the number of queued jobs
* node_status: check status of each jenkins node (running or not)

## Usage
```bash
usage: check_jenkins.py [-h] --host HOST [--username USERNAME]
                        [--password PASSWORD] --check-mode
                        {node_status,queue_lenght} [--enable-performance-data]
                        [-w WARNING] [-c CRITICAL]

Return result of a chek to jenkins with nagios format

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           ip or cname of jenkins endpoint
  --username USERNAME
  --password PASSWORD
  --check-mode {node_status,queue_lenght}
                        operation mode
  --enable-performance-data
                        enable output performance data
  -w WARNING, --warning WARNING
                        number of entries neededed to throw a warning
  -c CRITICAL, --critical CRITICAL
                        number of entries neededed to throw a critical
```

```bash
usage: execute_jenkins_job.py [-h] --jenkins-job JENKINS_JOB
                              [--job-arguments JOB_ARGUMENTS] [--ignore-ssl]
                              -u USER -p PASSWORD

Execute jenkins job. Return OK on Success, WARNING on UNSTABLE and FAIL on
Failed build

optional arguments:
  -h, --help            show this help message and exit
  --jenkins-job JENKINS_JOB
  --job-arguments JOB_ARGUMENTS
                        Arguments to set when execute jenkins job. Written as
                        key=value csv
  --ignore-ssl
  -u USER, --user USER
  -p PASSWORD, --password PASSWORD
```
