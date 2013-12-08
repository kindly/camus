# -*- coding: utf-8 -*-

from flask.ext.script import Manager
from camus import create_app

app = create_app
manager = Manager(app)

manager.add_option('-c', '--clean', dest='clean', required=False, help='Teardown all the modules')

manager.add_option('-m', '--mode', dest='mode', required=False, help='Mode of running the application. The only current option is "develop", which runs in debug mode')

if __name__ == "__main__":
    manager.run()
