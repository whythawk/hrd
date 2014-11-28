import os
from importlib import import_module

from flask import request
from flask.ext.themes2 import Themes, render_theme_template
from flask.ext.babel import Babel

from flaskbb import create_app
from flaskbb.configs.default import DefaultConfig as bb_config



def set_translations(app):
    # we want a symbolic link between the translations so that
    # flaskbb can find them
    DIR = os.path.dirname(os.path.realpath(__file__))
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


def get_flaskbb(app, path):
    theme_hack()
    Themes(app, app_identifier="hrd")
    db = app.config['SQLALCHEMY_DATABASE_URI']
    if db.startswith('sqlite:///'):
        db = 'sqlite:///%s' % os.path.join(path, db[10:])
    bb_config.SQLALCHEMY_DATABASE_URI = db
    bb_config.SECRET_KEY = app.secret_key

    flaskbb = create_app(bb_config)

    set_translations(flaskbb)

    flaskbb.theme_manager = app.theme_manager

    helpers = [
        'lang_list',
        'current_lang',
        'lang_pick',
        'menu_class',
        'sub_menu_item',
        'has_perm',
    ]

    for helper in helpers:
        flaskbb.jinja_env.globals[helper] = app.jinja_env.globals[helper]

    block_routes(flaskbb)
    return flaskbb


def theme_hack():
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
        'plugins.portal.views'
    ]

    for module_name in hack_list:
        p = import_module('flaskbb.' + module_name)
        p.render_template = render_template


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
