# -*- coding: utf-8 -*-
import os.path
import urllib

from flask import Flask, request, abort
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.babel import Babel

from werkzeug.wsgi import DispatcherMiddleware

from flaskbb_shim import get_flaskbb

# Import our config
try:
    import config.production as config
except ImportError:
    import config.default as config


language_list = config.LANGUAGE_LIST
DIR = os.path.dirname(os.path.realpath(__file__))


app = Flask(__name__)
app.debug = config.DEBUG
app.secret_key = config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = config.DB_CONNECTION
app.config['UPLOAD_FOLDER'] = os.path.join(DIR, config.UPLOAD_FOLDER)
app.config['BABEL_DEFAULT_LOCALE'] = 'en'

if not os.path.isdir(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
babel = Babel(app)

def get_locale():
    return request.environ['LANG']

babel.localeselector(get_locale)

DEBUG = config.DEBUG

default_url_for = app.jinja_env.globals['url_for']

_truncate = app.jinja_env.filters['truncate']
def truncate(s, length=255, killwords=False, end='...'):
    if not s:
        return ''
    return _truncate(s, length=length, killwords=killwords, end=end)
app.jinja_env.filters.update({'truncate': truncate})


# Capitalize the language names for consistency/client desires
_language_list = []
for code, name, dir_, active in language_list:
    _language_list.append(( code, name.title(), dir_, active))
language_list = _language_list


lang_dir = {}
for code, name, dir_, active in language_list:
    lang_dir[code] = dir_


lang_name = {}
for code, name, dir_, active in language_list:
    lang_name[code] = name


lang_codes = []
for code, name, dir_, active in language_list:
    lang_codes.append(code)


permission_list = config.PERMISSIONS


def permission(permission):
    if permission not in request.permissions:
        if 'sys_admin' not in request.permissions:
            abort(403)


def permission_content(lang):
    permission('content_manage')


def lang_list():
    return language_list


def current_lang():
    return request.environ['LANG']


def current_lang_name():
    return lang_name[request.environ['LANG']]


def current_admin_lang():
    return lang_name[get_admin_lang()]


def current_admin_lang_dir():
    return lang_dir[get_admin_lang()]

def lang_html():
    lang = request.environ['LANG']
    return 'lang="%s" dir="%s"' % (lang, lang_dir[lang])


def lang_html_body():
    lang = request.environ['LANG']
    return lang_dir[lang]

def lang_pick(lang):
    current_url = request.environ['CURRENT_URL']
    current_url = '/%s%s' % (lang, current_url)
    return current_url


def url_for(*args, **kw):
    url = default_url_for(*args, **kw)
    lang = request.environ['LANG']
    url = '/%s%s' % (lang, url)
    return url


def url_for_fixed(url):
    lang = request.environ['LANG']
    url = '/%s%s' % (lang, url)
    return url


def url_for_admin(*args, **kw):
    if 'lang' not in kw:
        lang = request.args.get('lang')
        if lang:
            kw['lang'] = lang
    return url_for(*args, **kw)


def get_admin_lang():
    lang = request.args.get('lang')
    return lang or 'en'


def get_bool(field):
    return bool(request.form.get(field, False))


def get_str(field):
    return request.form.get(field, '')


def get_int(field, default):
    value = request.form.get(field, default)
    try:
        value = int(value)
    except ValueError:
        value = default
    return value

import migrate
import helpers
import models
import views


@app.template_filter('sn')
def reverse_filter(s):
    if s is None:
        return ''
    return s


class I18nMiddleware(object):
    """I18n Middleware selects the language based on the url
    eg /fr/home is French"""

    def __init__(self, app):
        self.app = app
        self.default_locale = 'en'
        locale_list = []
        for code, lang, _dir, active in language_list:
            locale_list.append(code)
        self.locale_list = locale_list

    def __call__(self, environ, start_response):
        # strip the language selector from the requested url
        # and set environ variables for the language selected
        # LANG is the language code eg en, fr
        # CURRENT_URL is set to the current application url
        if 'LANG' not in environ:
            path_parts = environ['PATH_INFO'].split('/')
            if len(path_parts) > 1 and path_parts[1] in self.locale_list:
                environ['LANG'] = path_parts[1]
                # rewrite url
                if len(path_parts) > 2:
                    environ['PATH_INFO'] = '/'.join([''] + path_parts[2:])
                else:
                    environ['PATH_INFO'] = '/'
            else:
                environ['LANG'] = self.default_locale
            # Current application url
            path_info = environ['PATH_INFO']
            # sort out weird encodings
            path_info = '/'.join(urllib.quote(pce, '')
                                 for pce in path_info.split('/'))
            qs = environ.get('QUERY_STRING')
            if qs:
                # sort out weird encodings
                # qs = urllib.quote(qs, '')
                environ['CURRENT_URL'] = '%s?%s' % (path_info, qs)
            else:
                environ['CURRENT_URL'] = path_info
        return self.app(environ, start_response)

flaskbb = get_flaskbb(app, __path__[0], url_for)
flaskbb.jinja_env.globals['url_for'] = url_for
flaskbb.jinja_env.globals['url_for_fixed'] = url_for_fixed

filters = [
    'format_date',
    'can_edit_user',
    'can_ban_user',
    'is_admin',

    'time_since',
    'is_online',
    'markup',
]

for f in filters:
    app.jinja_env.filters[f] = flaskbb.jinja_env.filters[f]

app.extensions['cache'] = flaskbb.extensions['cache']

app.login_manager = flaskbb.login_manager
app.bb = flaskbb

app = DispatcherMiddleware(app, {
    '/forum': flaskbb
})

app = I18nMiddleware(app)
