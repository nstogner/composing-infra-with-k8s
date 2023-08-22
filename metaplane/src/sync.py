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

def bucket(config, claim_name, bucket_name):
    prefix = config.get('bucket_prefix')
    return {
        "apiVersion": "s3.aws.upbound.io/v1beta1",
        "kind": "Bucket",
        "metadata": {
            "name": f'{prefix}-{claim_name}-{bucket_name}',
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

class Controller(BaseHTTPRequestHandler):
    config = {
        "bucket_prefix": os.environ['BUCKET_PREFIX'],
        "bucket_region": os.environ['BUCKET_REGION'],
    }

    def sync(self, claim, children):
        print(claim)
        print(children)

        claim_name = claim.get('metadata').get('name')
        buckets = claim.get('spec').get('names')

        children = [
            bucket(self.config, claim_name, bucket_name) for bucket_name in buckets
        ]

        return {'status': {}, 'children': children}

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
