#!/usr/bin/env python3

import connexion
import logging

from swagger_server import encoder


def create_app():
    logging.getLogger('connexion.operation').setLevel('ERROR')
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'Optimization framework service'})
    return app

def main():
    create_app().run(port=8080)

if __name__ == '__main__':
    create_app()