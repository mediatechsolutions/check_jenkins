#!/usr/bin/env python3
import argparse
import json
import requests
import time
from urllib.parse import urlparse
import sys


nagios_output_state = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3,
}


class Jenkins(object):

    def __init__(self, user, password, verify_ssl):
        self.user = args.user
        self.password = args.password
        self.verify_ssl = verify_ssl

    def __get_csrf_token(self, jenkins_base_url):
        response = requests.get('%s/crumbIssuer/api/json' % jenkins_base_url, verify=self.verify_ssl, auth=self.auth)
        if response.status_code == 200:
            json = response.json()
            return {json['crumbRequestField']: json['crumb']}

        else:
            return dict()

    @property
    def auth(self):
        if self.user and self.password:
            return (self.user, self.password)
        return None

    def request(self, url, **kwargs):
        jenkins_base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(url))
        csrf_token = self.__get_csrf_token(jenkins_base_url)
        headers = dict()
        for key in csrf_token:
            headers[key] = csrf_token[key]

        response = requests.post(url, auth=self.auth, verify=self.verify_ssl, headers=headers, **kwargs)
        if not 200 <= response.status_code < 400:
            print("Error accessing to %s(%s):\n%s" % (url, response.status_code, response.content))
            sys.exit(-1)
        return response

    def __parse_arguments(self, arguments):
        params = dict()
        for arg in arguments.split(','):
            key, value = arg.split('=')
            params[key] = value
        return params
    def execute_job(self, url, arguments):
        params = self.__parse_arguments(arguments)
        response = self.request('%s/buildWithParameters' % url, params=params)
        return self.__get_job_url(url, arguments)

    def __get_job_url(self, url, arguments):
        response = self.request('%s/api/json' % url)
        return response.json()['lastBuild']['url']

    def check_job_result(self, url):
        result = None
        while not result:
            response = self.request('%s/api/json' % url)
            result = response.json()['result']
            if result:
                break
            print("Waiting for result")
            time.sleep(10)
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Execute jenkins job. Return OK on Success, WARNING on UNSTABLE and FAIL on Failed build')

    parser.add_argument(
        '--jenkins-job',
        type=str,
        required=True
    )
    parser.add_argument(
        '--job-arguments',
        help='Arguments to set when execute jenkins job. Written as key=value csv',
        type=str,
        default=''
    )
    parser.add_argument(
        '--ignore-ssl',
        action='store_false',
        default=True
    )
    parser.add_argument(
        '-u','--user',
        type=str,
        required=True
    )
    parser.add_argument(
        '-p','--password',
        type=str,
        required=True
    )

    args = parser.parse_args()

    print('Executing job %s with arguments %s\n' % (args.jenkins_job, args.job_arguments))

    jenkins = Jenkins(args.user, args.password, args.ignore_ssl)
    job_uri = jenkins.execute_job(args.jenkins_job, args.job_arguments)

    print('Executing job %s\n' % job_uri)
    job_result = jenkins.check_job_result(job_uri)

    print('\nFinished: %s' % job_result)
    if (job_result == 'SUCCESS'):
        sys.exit(0)
    else:
        sys.exit(2)
