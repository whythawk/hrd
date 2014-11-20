import os.path
from importlib import import_module

from flask.ext.themes2 import Themes, render_theme_template
from flaskbb import create_app

from flaskbb.configs.development import DevelopmentConfig as bb_config


def get_flaskbb(app, path):
    Themes(app, app_identifier="hrd")
    db = app.config['SQLALCHEMY_DATABASE_URI']
    if db.startswith('sqlite:///'):
        db = 'sqlite:///%s' % os.path.join(path, db[10:])
    bb_config.SQLALCHEMY_DATABASE_URI = db
    bb_config.SECRET_KEY = app.secret_key

    flaskbb = create_app(bb_config)

    flaskbb.theme_manager = app.theme_manager
    return flaskbb

# we want to force our theme but need to hack each module due to the way
# imports are done


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

for x in hack_list:
    p = import_module('flaskbb.' + x)
    p.render_template = render_template
