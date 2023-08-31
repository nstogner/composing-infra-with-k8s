#!/usr/bin/env python
"""
Usage::
    ./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json
import copy
import re
import os

def primary_bucket(config, parent_name):
    prefix = config.get('bucket_prefix')
    return {
        "apiVersion": "s3.aws.upbound.io/v1beta1",
        "kind": "Bucket",
        "metadata": {
            "name": f'{prefix}-{parent_name}-primary',
            "annotations": {
                "hello": "there",
            },
        },
        "spec": {
            "forProvider": {
              "region": config.get('bucket_region'),
            },
            "providerConfigRef": {
                "name": "default",
            },
        },
    }

def backup_bucket(config, parent_name, suffix, hosted_zone_id):
    prefix = config.get('bucket_prefix')
    return {
        "apiVersion": "s3.aws.upbound.io/v1beta1",
        "kind": "Bucket",
        "metadata": {
            "name": f'{prefix}-{parent_name}-{suffix}',
            "annotations": {
                "primary-hosted-zone-id": hosted_zone_id,
            },
        },
        "spec": {
            "forProvider": {
              "region": config.get('bucket_region'),
            },
            "providerConfigRef": {
                "name": "default",
            },
        },
    }

class Controller(BaseHTTPRequestHandler):

    def sync(self, parent, observed_children):
        print("----------- Parent -----------\n",
              json.dumps(parent), "\n",
              "----- Observed Children ------\n",
              json.dumps(observed_children),
              )

        # TODO: Move to startup?
        with open("/config/cloud.json", 'r') as stream:
            config = json.load(stream)
        print('Configured: ', config)

        parent_name = parent.get('metadata').get('name')
        desired_primary = primary_bucket(config, parent_name)

        desired_children = [
          desired_primary
        ]

        primary_name = desired_primary.get('metadata').get('name')

        try:
            backups = parent.get('spec').get('backups')
            observed_primary = observed_children.get('Bucket.s3.aws.upbound.io/v1beta1').get(primary_name)
            primary_hosted_zone_id = observed_primary.get('status').get('atProvider').get('hostedZoneId')
            desired_children.extend([backup_bucket(config, parent_name, backup, primary_hosted_zone_id) for backup in backups])
            print('Backup buckets: reconciling')
        except Exception as error:
            print('Buckup buckets: waiting on primary bucket to be ready before reconiling:', error)

        print("----- Desired Children ------\n",
            json.dumps(desired_children),
            )

        return {'status': {}, 'children': desired_children}

    def do_POST(self):
        observed = json.loads(
            self.rfile.read(int(self.headers['Content-Length'])))
        desired = self.sync(observed['parent'], observed['children'])

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(desired).encode())

def run(server_class=HTTPServer, handler_class=Controller, port=80):
    logging.basicConfig(level=logging.INFO)

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
