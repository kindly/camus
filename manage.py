# -*- coding: utf-8 -*-

from flask.ext.script import Manager
from camus import create_app

app = create_app
manager = Manager(app)

@manager.command
def develop():
    print 'hello'
    '''Run local server using developer config.'''
    app(mode='develop')
    app.run()

manager.add_option('-m', '--mode', dest='mode', required=False, help='Mode of running the application. The only current option is "develop", which runs in debug mode')

if __name__ == "__main__":
    manager.run()
