import os
from importlib import import_module

from flask import request, abort
from flask.ext.themes2 import Themes, render_theme_template
from flask.ext.babel import Babel
from flask.ext.login import current_user

import flaskbb.forum.forms
from flaskbb import create_app
from flaskbb.configs.default import DefaultConfig as bb_config

import flaskbb.user

from hrd.bb import user_forms
from hrd.bb import forum_forms


DIR = os.path.dirname(os.path.realpath(__file__))

def set_translations(app):
    # we want a symbolic link between the translations so that
    # flaskbb can find them
    hrd_trans = os.path.join(DIR, 'translations')
    flaskbb_trans = os.path.normpath(
        os.path.join(DIR, '..', '..', 'flaskbb', 'flaskbb', 'translations')
    )
    try:
        os.symlink(hrd_trans, flaskbb_trans)
    except OSError:
        pass

    # attach babel-flask
    babel = Babel(app)

    # set locale on request
    def get_locale():
        return request.environ['LANG']
    babel.localeselector(get_locale)


def get_flaskbb(app, path, url_for):
    theme_hack(url_for)
    Themes(app, app_identifier="hrd")
    db = app.config['SQLALCHEMY_DATABASE_URI']
    if db.startswith('sqlite:///'):
        db = 'sqlite:///%s' % os.path.join(path, db[10:])
    bb_config.SQLALCHEMY_DATABASE_URI = db
    bb_config.SECRET_KEY = app.secret_key
    bb_config.USERS_PER_PAGE = 10

    _flaskbb = create_app(bb_config)

    set_translations(_flaskbb)

    _flaskbb.theme_manager = app.theme_manager

    helpers = [
        'lang_list',
        'current_lang',
        'lang_pick',
        'menu_class',
        'sub_menu_item',
        'has_perm',
    ]

    for helper in helpers:
        _flaskbb.jinja_env.globals[helper] = app.jinja_env.globals[helper]

    helpers = [
        'get_flashed_messages',
    ]

    for helper in helpers:
        app.jinja_env.globals[helper] = _flaskbb.jinja_env.globals[helper]
    block_routes(_flaskbb)

    user_form_hack()
    forum_form_hack()

    t_path = os.path.join(DIR, 'themes', 'hrd', 'templates')
    _flaskbb.jinja_loader.searchpath = [t_path] + _flaskbb.jinja_loader.searchpath


    @_flaskbb.before_request
    def no_guest():
        if not current_user.is_authenticated():
            abort(403)

    return _flaskbb


def theme_hack(url_for):
    ''' Force our theme on templates.
    We need to hack each module due to the way imports are done '''
    def render_template(template, **context):
        theme = 'hrd'
        return render_theme_template(theme, template, **context)

    hack_list = [
        'auth.views',
        'forum.views',
        'user.views',
        'email',
        'utils.helpers',
        'app',
        'management.views',
        'plugins.portal.views',
        'user.models',
        'forum.models',
    ]

    for module_name in hack_list:
        p = import_module('flaskbb.' + module_name)
        if hasattr(p, 'render_template'):
            p.render_template = render_template
        if hasattr(p, 'url_for'):
            p.url_for = url_for


def user_form_hack():
    hack_list= [
        'ChangePasswordForm',
        'ChangeEmailForm',
        'ChangeUserDetailsForm',
        'GeneralSettingsForm',
        'NewMessageForm',
        'EditMessageForm',
    ]
    for cls in hack_list:
        new_cls = getattr(user_forms, cls)
        setattr(flaskbb.user, cls, new_cls)
        setattr(flaskbb.user.forms, cls, new_cls)


def forum_form_hack():
    hack_list= [
        'QuickreplyForm',
        'ReplyForm',
        'NewTopicForm',
        'ReportForm',
        'UserSearchForm',
        'SearchPageForm',
    ]
    for cls in hack_list:
        new_cls = getattr(forum_forms, cls)
        setattr(flaskbb.forum.views, cls, new_cls)


BARRED_VIEWS = [
]


def block_routes(app):
    ''' remove routes for views we do not want '''
    rules = []
    for rule in app.url_map._rules:
        # print rule.endpoint, rule.rule
        if rule.endpoint not in BARRED_VIEWS:
            rules.append(rule)

    app.url_map._rules = rules
