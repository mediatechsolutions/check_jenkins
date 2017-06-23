#!/usr/bin/env python
import argparse
import json
import requests
import sys

nagios_output_state = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3,
}


class Jenkins(object):

    def __init__(self, args):
        self.host = args.host
        self.username = args.username
        self.password = args.password

        self.enable_performance_data = args.enable_performance_data

        self.perf_data = list()
        self.data = list()
        self.summary = list()

        self.check_status = 'OK'

    def __request(self, url):
        try:
            request = requests.get(url, auth=(self.username, self.password))
            if request.status_code != 200:
                raise ValueError(
                    'Request HTTP code %s' % (request.status_code)
                )
            return request.text
        except ValueError as error:
            print(error)
            sys.exit(nagios_output_state['UNKNOWN'])

    def check(self, check_mode, warning, critical):
        try:
            return getattr(Jenkins, 'check_%s' % check_mode)(
                self, warning, critical
            )
        except ValueError as error:
            print(error)
            sys.exit(nagios_output_state['UNKNOWN'])

    def check_node_status(self, warning, critical):
        path = 'computer/api/json'
        url = '%s/%s' % (self.host, path)
        response = json.loads(self.__request(url))

        warning = int(warning) if warning is not None else ''
        critical = int(critical) if critical is not None else ''

        offline_nodes = 0

        for computer in response['computer']:
            output = '%s: %s' % (
                computer['displayName'],
                'offline' if computer['offline'] else 'online'
            )
            if computer['offline']:
                output = '%s REASON: %s' % (
                    output,
                    computer['offlineCauseReason']
                )
                offline_nodes += 1

            self.data.append(output)
            # |label=value;warn;crit;min;max
            self.perf_data.append('%s=%s;%s;%s;;' % (
                computer['displayName'] + '.online',
                '0' if computer['offline'] else '1', '', ''
            ))
            self.perf_data.append('%s=%s;%s;%s;;' % (
                computer['displayName'] + '.running',
                '0' if computer['idle'] else '1', '', ''
            ))

        self.summary.append(
            'Number of nodes: %s' % (len(response['computer'])))
        self.summary.append('Offline nodes: %s' % (offline_nodes))

        self.perf_data.insert(0, (
            '%s=%s;%s;%s;;%s' % (
                'offline_nodes',
                offline_nodes,
                warning,
                critical,
                len(response['computer'])
            ))
        )

        self.__set_status(warning, critical, offline_nodes)
        self.__nagios_output()

    def check_queue_lenght(self, warning, critical):
        path = 'queue/api/json'
        url = '%s/%s' % (self.host, path)
        response = json.loads(self.__request(url))

        warning = int(warning) if warning is not None else ''
        critical = int(critical) if critical is not None else ''

        queue_lenght = len(response['items'])

        self.summary.append('Queue lenght: %s jobs' % (queue_lenght))

        self.perf_data.append('%s=%s;%s;%s;;' % (
            'queue_lenght',
            queue_lenght,
            warning,
            critical
        ))

        self.__set_status(warning, critical, queue_lenght)
        self.__nagios_output()

    def __set_status(self, warning, critical, value_to_check):

        if critical != '' and value_to_check >= critical:
            self.check_status = 'CRITICAL'
            return

        if warning != '' and value_to_check >= warning:
            self.check_status = 'WARNING'
            return

        self.check_status = 'OK'

    def __nagios_output(self):
        output = self.check_status

        if self.summary:
            output += '\n\n%s' % '\n'.join(self.summary)
        if self.data:
            output += '\n\n%s' % '\n'.join(self.data)
        if self.enable_performance_data:
            output += '\n\n|%s' % (' '.join(self.perf_data))

        print(output)
        sys.exit(nagios_output_state[self.check_status])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Return result of a chek to jenkins with nagios format')

    parser.add_argument(
        '--host',
        help='ip or cname of jenkins endpoint',
        type=str,
        required=True
    )
    parser.add_argument('--username', type=str)
    parser.add_argument('--password', type=str)

    parser.add_argument(
        '--check-mode',
        choices=['node_status', 'queue_lenght'],
        help='operation mode',
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
        '-w', '--warning',
        help='number of entries neededed to throw a warning',
        type=str,
        default=None
    )
    parser.add_argument(
        '-c', '--critical',
        help='number of entries neededed to throw a critical',
        type=str,
        default=None
    )

    args = parser.parse_args()

    jenkins = Jenkins(args)

    jenkins.check(args.check_mode, args.warning, args.critical)
