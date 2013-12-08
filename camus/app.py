# -*- coding: utf-8 -*-

import os
import glob
import json
import inspect

from flask import url_for, Flask, request, render_template, abort, redirect, g
from flask.ext.babel import Babel
from flask.helpers import locked_cached_property
from flask import session
import jinja2

import config
import collections
from .extensions import mail, cache, login_manager
import flask.ext.login as login
from .utils import make_dir


# For import *
__all__ = ['create_app']

file_path = os.path.dirname(os.path.realpath(__file__))

plugins = [
    {'name': 'core',
     'root_path': os.path.dirname(os.path.realpath(__file__)),
     'package_root': 'camus'},
]

route_template_map = {}
helpers = {}
helper_modules = set()

##### Routing and controllers ##########

class Redirect(Exception):
    def __init__(self, url, **kw):
        self.url = url_for(url, **kw)

def redirect_raiser(url, **kw):
    raise Redirect(url, **kw)

def controller(**kw):
    try:
        return render_template(
            route_template_map[request.endpoint], 
            helper=helper,
            abort=abort,
            redirect=redirect_raiser,
            path_args=kw,
        )
    except Redirect, e:
        return redirect(e.url)

def configure_url_rules(app):
    for plugin in plugins:
        gather_routes(app, plugin)

    for route_name, template in route_template_map.iteritems():
        route = route_name.replace('{{', '<')
        route = route.replace('}}', '>')
        app.add_url_rule(route, route_name, controller, methods=['GET','POST'])


def gather_routes(app, plugin):
    global route_template_map

    template_dir = os.path.join(plugin['root_path'], 'templates')

    def walk_callback(arg, directory, files):
        template_dir_path = directory[len(template_dir)+1:]
        for file in files:
            full_path = os.path.join(directory, file)
            if file.startswith('_') or os.path.isdir(full_path):
                continue
            template_path = os.path.join(template_dir_path, file)

            parts = file.split('.')
            extension = parts[-1]
            file_no_extension = '.'.join(parts[:-1])

            template_path = '%s/%s' % (plugin.get('name'), template_path)

            if file == 'index.html':
                route_template_map['/' + template_dir_path] = template_path
                route_template_map['/' + template_dir_path + '/'] = template_path
            elif extension == 'html':
                route = '/' + os.path.join(template_dir_path, file_no_extension)
                route_template_map[route] = template_path

            route = '/' + os.path.join(template_dir_path, file)
            route_template_map[route] = template_path

    os.path.walk(template_dir, walk_callback, None)

##### Helpers ##########

class HelperNotFound(Exception):
    pass

def configure_helpers(app):
    for plugin in plugins:
        plugin_name = plugin['name']
        package_root = plugin.get('package_root')
        if not package_root:
            continue
        try:
            package = __import__('%s.helpers' % package_root)
        except ImportError:
            continue

        root_path = os.path.dirname(os.path.realpath(package.__file__))
        helper_folder = os.path.join(root_path, 'helpers')
        files = glob.glob('%s/*.py' % helper_folder)
        module_names = []
        for file in files:
            file_name = os.path.basename(file)
            if file_name == '__init__.py':
                continue
            if not file_name.endswith('.py'):
                continue
            module_names.append(file_name[:-3])

        for module_name in module_names:
            helper_package = __import__(
                '%s.helpers.%s' % (package_root, module_name)
            ).helpers
            helper_modules.add(module_name)
            module = getattr(helper_package, module_name)
            for name, item in module.__dict__.items():
                if not hasattr(item, '__call__'):
                    continue
                if name.startswith('_'):
                    continue
                ### only allow functions that start with context as first arg
                try:
                    if inspect.getargspec(item).args[0] != 'context':
                        continue
                except (IndexError, TypeError):
                    continue

                helper_name = '%s.%s.%s' % (plugin_name, module_name, name)
                helpers[helper_name] = item

def setup_helpers(app, clean):
    clean = clean or ''
    clean_modules = clean.split()
    for helper_module in helper_modules:
        try:
            if helper_module in clean_modules or clean == 'ALL':
                helper('%s.teardown' % helper_module, app.config)
        except HelperNotFound:
            pass

    for helper_module in helper_modules:
        try:
            helper('%s.setup' % helper_module, app.config)
        except HelperNotFound:
            pass

    @app.before_first_request
    def before_first_request():
        for helper_module in helper_modules:
            try:
                helper('%s.setup_first_request' % helper_module, app.config)
            except HelperNotFound:
                pass

    @app.before_request
    def before_request():
        for helper_module in helper_modules:
            try:
                helper('%s.setup_request' % helper_module, app.config)
            except HelperNotFound:
                pass

    @app.after_request
    def after_request(response):
        for helper_module in helper_modules:
            try:
                helper('%s.after_request' % helper_module, app.config)
            except HelperNotFound:
                pass
        return response

    @app.teardown_request
    def teardown_request(response):
        for helper_module in helper_modules:
            try:
                helper('%s.teardown_request' % helper_module, app.config)
            except HelperNotFound:
                pass
        return response

def helper(name, *args, **kw):
    helper = None
    if name.count('.') == 2:
        helper = helpers.get(name)

    if name.count('.') == 1:
        for plugin in plugins:
            plugin_name = plugin['name']
            helper = helpers.get('%s.%s' % (plugin_name, name))
            if helper:
                break

    if not helper:
        raise HelperNotFound('Helper %s can not be found' % name)

    if not hasattr(g, 'context'):
        try:
            g.context = {}
            context = g.context
        except RuntimeError:
            context = {}
    else:
        context = g.context
    
    return helper(context, *args, **kw)


###  App  ###

class App(Flask):

    @locked_cached_property
    def jinja_loader(self):
        """The Jinja loader for this package bound object.

        .. versionadded:: 0.5
        """
        loaders = {}
        for plugin in plugins:
            template_path = os.path.join(plugin['root_path'], 'templates')
            loader = jinja2.FileSystemLoader(template_path)
            loaders[plugin['name']] = loader
        return jinja2.PrefixLoader(loaders)

    def acreate_jinja_environment(self):
        rv = Flask.create_jinja_environment(self)
        rv.globals.update({})
        return rv

def create_app(mode='default', clean=''):
    """Create a Flask app."""

    app = App('camus')
    configure_app(app, mode)
    configure_hook(app)
    configure_extensions(app)
    configure_logging(app)
    configure_template_filters(app)
    #configure_error_handlers(app)
    
    configure_helpers(app)
    setup_helpers(app, clean)
    configure_url_rules(app)
    app.add_template_filter(json.dumps, 'json_dumps')

    return app

def add_path_and_config(app, confg_option, path):
    if not app.config.get(confg_option):
        app.config[confg_option] = os.path.join(
            app.config.get('INSTANCE_FOLDER_PATH', path)
        )
    make_dir(app.config[confg_option])


def configure_app(app, mode):
    """Different ways of configurations."""

    # http://flask.pocoo.org/docs/api/#configuration
    if mode == 'develop':
        app.config.from_object(config.DevelopConfig)
    else:
        app.config.from_object(config.DefaultConfig)
    # Use instance folder instead of env variables to make deployment easier.
    app.config.from_envvar('CAMUS_CONFIG', silent=True)

    add_path_and_config(app, 'UPLOAD_FOLDER', 'upload')
    add_path_and_config(app, 'LOG_FOLDER', 'logs')
    add_path_and_config(app, 'DATA_FOLDER', 'data')
    add_path_and_config(app, 'APP_FOLDER', 'app')
    add_path_and_config(app, 'USER_FOLDER', 'user')


def configure_extensions(app):
    # flask-mail
    mail.init_app(app)

    # flask-cache
    cache.init_app(app)

    # flask-babel
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        accept_languages = app.config.get('ACCEPT_LANGUAGES')
        return request.accept_languages.best_match(accept_languages)

    login_manager.init_app(app)


def configure_template_filters(app):

    @app.template_filter()
    def pretty_date(value):
        return pretty_date(value)

    @app.template_filter()
    def format_date(value, format='%Y-%m-%d'):
        return value.strftime(format)


def configure_logging(app):
    """Configure file(info) and email(error) logging."""

    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return

    import logging
    from logging.handlers import SMTPHandler

    # Set info level on logger, which might be overwritten by handers.
    # Suppress DEBUG messages.
    app.logger.setLevel(logging.INFO)

    info_log = os.path.join(app.config['LOG_FOLDER'](), 'info.log')
    info_file_handler = logging.handlers.RotatingFileHandler(info_log, maxBytes=100000, backupCount=10)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(info_file_handler)

    # Testing
    #app.logger.info("testing info.")
    #app.logger.warn("testing warn.")
    #app.logger.error("testing error.")

    mail_handler = SMTPHandler(app.config['MAIL_SERVER'],
                               app.config['MAIL_USERNAME'],
                               app.config['ADMINS'],
                               'O_ops... %s failed!' % 'camus',
                               (app.config['MAIL_USERNAME'],
                                app.config['MAIL_PASSWORD']))
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(mail_handler)


def configure_hook(app):

    @app.after_request
    def after_request(*arg, **kw):
        ### flask login makes sesssion for all 
        if len(session) == 1 and '_id' in session:
            session.clear()

        return arg[0]

def configure_error_handlers(app):

    @app.errorhandler(403)
    def forbidden_page(error):
        return render_template("errors/forbidden_page.html"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/page_not_found.html"), 404

    @app.errorhandler(500)
    def server_error_page(error):
        return render_template("errors/server_error.html"), 500
