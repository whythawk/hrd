# -*- coding: utf-8 -*-

import os


from flask import Flask, request, abort
from flask.ext.sqlalchemy import SQLAlchemy


secret_key = os.urandom(24)
secret_key = 'FIXME - DELETE THIS'

app = Flask(__name__)
app.debug = True
app.secret_key = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
db = SQLAlchemy(app)

DEBUG = True

default_url_for = app.jinja_env.globals['url_for']

language_list = [
    ('en', u'English', 'ltr'),
    ('fr', u'français', 'ltr'),
    ('es', u'español', 'ltr'),
    ('ar', u'العربية', 'rtl'),
    ('zh', u'中文', 'ltr'),
]

lang_dir = {}
for code, name, dir_ in language_list:
    lang_dir[code] = dir_


lang_name = {}
for code, name, dir_ in language_list:
    lang_name[code] = name



permission_list = [
    ('sys_admin', 'System administrator'),
    ('content_manage', 'Content managment'),
    ('translator', 'Content translation'),
    ('user_admin', 'User administrator'),
    ('user_manage', 'User management'),
]


def permission(permission):
    if permission not in request.permissions:
        if 'sys_admin' not in request.permissions:
            abort(403)


def permission_content(lang):
    if lang == 'en':
        permission('content_manage')
    else:
        permission('translation')


def lang_list():
    return language_list


def current_lang():
    return request.environ['LANG']

def current_lang_name():
    return lang_name[request.environ['LANG']]


def current_admin_lang():
    return lang_name[get_admin_lang()]


def lang_html():
    lang = request.environ['LANG']
    return 'lang="%s" dir="%s"' % (lang, lang_dir[lang])


def lang_pick(lang):
    current_url = request.environ['CURRENT_URL']
    current_url = '/%s%s' % (lang, current_url)
    return current_url


def url_for(*args, **kw):
    url = default_url_for(*args, **kw)
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

import helpers
import models
import views
