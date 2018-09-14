#!/usr/bin/env python3
import argparse
import json
import requests
import time
from urllib.parse import urlparse
import sys
import uuid
import traceback


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
        if arguments:
            for arg in arguments.split(','):
                key, value = arg.split('=')
                params[key] = value
        return params

    def execute_job(self, url, arguments):
        params = self.__parse_arguments(arguments)
        if 'TASKID' not in params:
            params['TASKID'] = uuid.uuid4().hex
        response = self.request('%s/buildWithParameters' % url, params=params)
        return self.__get_job_url(url, arguments)

    def __get_job_url(self, url, arguments):
        response = self.request('%s/api/json' % url)
        return response.json()['lastBuild']['url']

    def check_job_result(self, url):
        while True:
            response = self.request('%s/api/json?tree=timestamp,result,number,duration,url' % url)
            response.raise_for_status()
            result = response.json()
            if result['result']:
                return result 
            print("Waiting for result")
            time.sleep(10)

    def get_last_completed_build(self, url, timeout):
        response = self.request(
            '%s/api/json?tree=lastCompletedBuild[timestamp,result,number,duration,url]'
            % url
        )
        response.raise_for_status()
        result = response.json()['lastCompletedBuild']
        timestamp = result.get('timestamp', 0) / 1000.
        return {'result': 'TIMEOUT'} if timestamp + timeout < time.time() else result


def get_args():
    parser = argparse.ArgumentParser(
        description='Execute jenkins job. Return OK on Success, WARNING on UNSTABLE and FAIL on Failed build')

    parser.add_argument(
        '--jenkins-job',
        type=str,
        required=True
    )
    parser.add_argument(
        '--enable-performance-data',
        help='enable output performance data',
        action='store_true',
        default=False
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
    parser.add_argument(
        '-d','--delayed',
        action="store_true"
    )
    parser.add_argument(
        '--timeout',
        default=900,
        type=int,
        help="In delayed mode, seconds to consider the last build result"
    )

    return parser.parse_args()


class Nagios(object):
    def show(self, preface, result, show_performance):
        def format_prop(key, value):
            return '%s=%s;%s;%s;%s;%s ' % (key, value, '', '', '', '')
        props = ''
        props += format_prop("duration", result.get('duration')/1000. if result.get('duration') is not None else None)
        props += format_prop("success", 1 if result.get('result') == 'SUCCESS' else 0)
        print('%s\n\n|%s' % (preface, props))
        sys.exit(0 if result.get('result') == 'SUCCESS' else 2)
        

if __name__ == "__main__":
    args = get_args()
    job_result = {}
    message = 'FAILURE: unknown'

    try:
        jenkins = Jenkins(args.user, args.password, args.ignore_ssl)
        job_uri = jenkins.execute_job(args.jenkins_job, args.job_arguments)
        if args.delayed:
            print("delayed execution. Retrieving last completed build.")
            job_result = jenkins.get_last_completed_build(args.jenkins_job, args.timeout)
        else:
            job_result = jenkins.check_job_result(job_uri)
        pattern = (
            "OK\n\nJob {job} build {build} was successful" 
            if job_result.get('result') == 'SUCCESS' 
            else "FAIL\n\nJob {job} failed on build {build} with error {result} "
        )
        message = pattern.format(
            job=args.jenkins_job,
            build=job_result.get('number'),
            result=job_result.get('result')
        )
    except Exception as e:
        message = "FAILURE\n\nJob %s failed\n\nException: %s\nDetails:\n%s" % (args.jenkins_job, e, traceback.format_stack())
    finally:
        Nagios().show(message, job_result, args.enable_performance_data)

