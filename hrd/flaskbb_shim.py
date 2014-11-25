import os.path
from importlib import import_module

from flask.ext.themes2 import Themes, render_theme_template
from flask.ext.babel import Babel

from flaskbb import create_app
from flaskbb.configs.development import DevelopmentConfig as bb_config


def get_flaskbb(app, path):
    theme_hack()
    Themes(app, app_identifier="hrd")
    db = app.config['SQLALCHEMY_DATABASE_URI']
    if db.startswith('sqlite:///'):
        db = 'sqlite:///%s' % os.path.join(path, db[10:])
    bb_config.SQLALCHEMY_DATABASE_URI = db
    bb_config.SECRET_KEY = app.secret_key

    flaskbb = create_app(bb_config)
    babel = Babel(flaskbb)

    flaskbb.theme_manager = app.theme_manager
    flaskbb.jinja_env.globals['lang_list'] = app.jinja_env.globals['lang_list']
    flaskbb.jinja_env.globals['current_lang'] = app.jinja_env.globals['current_lang']
    flaskbb.jinja_env.globals['lang_pick'] = app.jinja_env.globals['lang_pick']
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
        print rule.endpoint, rule.rule
        if rule.endpoint not in BARRED_VIEWS:
            rules.append(rule)

    app.url_map._rules = rules
