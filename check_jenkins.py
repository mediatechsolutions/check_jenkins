#!/usr/bin/env python
import argparse
import json
import requests
import sys

output_state = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3,
}

class Jenkins(object):

    check_mode = dict()
    def __init__(self, args):
        self.host = args.host
        self.username = args.username
        self.password = args.password
        self.performance_data = args.enable_performance_data

    def __request(self, url):
        try:
            request = requests.get(url, auth=(self.username, self.password))
            if request.status_code != 200:
                raise ValueError('Request HTTP code %s' % (request.status_code))
            return request.text
        except ValueError as error:
            print(error)
            sys.exit(output_state['UNKNOWN'])
            

    def check(self, mode, warning, critical):
        return getattr(Jenkins, mode)(self, warning, critical)

    def check_nodes(self, warning, critical):
        path = 'computer/api/json'
        url = '%s/%s' % (self.host, path)
        response = json.loads(self.__request(url))

        summary = list()
        data = list()
        perf_data = list()
        offline_nodes = 0

        for computer in response['computer']:
            output = '%s: %s' % (computer['displayName'], 'offline' if computer['offline'] else 'online')
            if computer['offline']:
                output = '%s REASON: %s' % (output, computer['offlineCauseReason'])
                offline_nodes += 1

            data.append(output)
            # |label=value;warn;crit;min;max
            perf_data.append('%s=%s;%s;%s;;' % (
                computer['displayName'],
                '0' if computer['offline'] else '1', '', ''
            ))

        summary.append('Number of slaves: %s' %(len(response['computer'])))
        summary.append('Offline slaves: %s' %(offline_nodes))

        perf_data.insert(0, 
            ('%s=%s;%s;%s;;%s' % (
                'offline_nodes',
                offline_nodes,
                warning if warning != None else '',
                critical if critical != None else '',
                len(response['computer'])
            ))
        )

        if critical != None and offline_nodes >= int(critical):
            self.print_output('CRITICAL', summary, data, perf_data)
        if warning != None and offline_nodes >= int(warning):
            self.print_output('WARNING', summary, data, perf_data)
        
        self.print_output('OK', summary, data, perf_data)

    def print_output(self, status, summary, data, perf_data):
        output = '%s\n\n%s\n\n%s\n\n' % (status, '\n'.join(summary), '\n'.join(data))
        if self.performance_data:
            output += '|%s' % (' '.join(perf_data))

        print(output)
        sys.exit(output_state[status])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description =  'Return result of a elasticsearch query with nagios format')

    parser.add_argument('--host', help='ip or cname of jenkins endpoint', type=str, default='localhost')
    parser.add_argument('--username', type=str)
    parser.add_argument('--password', type=str)

    parser.add_argument('--mode', choices=['check_nodes'], help='operation mode', type=str, default='search')

    parser.add_argument('--enable-performance-data', help='enable output performance data', action='store_true', default=False)
    parser.add_argument('-w', '--warning', help='number of entries neededed to throw a warning', type=str, default=None)
    parser.add_argument('-c', '--critical', help='number of entries neededed to throw a critical', type=str, default=None)

    args = parser.parse_args()

    jenkins = Jenkins(args)
    
    jenkins.check(args.mode, args.warning, args.critical)
    #Checker(args).perform_check()
    