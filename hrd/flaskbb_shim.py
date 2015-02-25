import os
from importlib import import_module
from datetime import datetime, timedelta


from flask import request, abort
from flask.ext.themes2 import Themes, render_theme_template
from flask.ext.babel import Babel
from flask.ext.login import current_user
from werkzeug.wrappers import Response

import flaskbb.forum.forms
from flaskbb import create_app
from flaskbb.configs.default import DefaultConfig as bb_config

import flaskbb.user

from hrd.bb import user_forms
from hrd.bb import forum_forms


import hrd


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


def forum_is_unread(forum, forumsread, user):
    """Checks if a forum is unread

    :param forum: The forum that should be checked if it is unread

    :param forumsread: The forumsread object for the forum

    :param user: The user who should be checked if he has read the forum
    """
    # If the user is not signed in, every forum is marked as read
    if not user.is_authenticated():
        return False

##    read_cutoff = datetime.utcnow() - timedelta(
##        days=bb_config.get("TRACKER_LENGTH"))
##
##    # disable tracker if read_cutoff is set to 0
##    if read_cutoff == 0:
##        return False

    # If there are no topics in the forum, mark it as read
    if forum and forum.topic_count == 0:
        return False

    # If the user hasn't visited a topic in the forum - therefore,
    # forumsread is None and we need to check if it is still unread
#    if forum and not forumsread:
#        return forum.last_post.date_created > read_cutoff
    try:
        # check if the forum has been cleared and if there is a new post
        # since it have been cleared
        if forum.last_post.date_created > forumsread.cleared:
            if forum.last_post.date_created < forumsread.last_read:
                return False
    except TypeError:
        pass
    # else just check if the user has read the last post
    return forum.last_post.date_created > forumsread.last_read

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
        'user_logged_in',
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
        ga = hrd.check_ga()
        if ga:
            return ga

    _flaskbb.jinja_env.filters['forum_is_unread'] = forum_is_unread
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

from wtforms import StringField
from wtforms.validators import DataRequired
from wtforms.ext.sqlalchemy.fields import QuerySelectField

flaskbb.management.forms.ForumForm.title = StringField("Section Title", validators=[
        DataRequired(message="Section title required")])

flaskbb.management.forms.ForumForm.category = QuerySelectField(
        "Message board",
        query_factory=flaskbb.management.forms.selectable_categories,
        allow_blank=False,
        get_label="title",
        description="The category that contains this forum."
    )

flaskbb.management.forms.CategoryForm.title = StringField("Message board title", validators=[
        DataRequired("Message board title required")])


import flaskbb.forum.models as bb_f

def delete_forum(self, users=None):
    """Deletes forum. If a list with involved user objects is passed,
    it will also update their post counts

    :param users: A list with user objects
    """
    # delete reports
    topics = bb_f.db.session.query(bb_f.Topic.id).filter_by(forum_id=self.id)
    posts = bb_f.db.session.query(bb_f.Post.id).filter(bb_f.Post.topic_id.in_(topics))
    reports = bb_f.db.session.query(bb_f.Report).filter(bb_f.Report.post_id.in_(posts)).all()
    for report in reports:
        report.delete()
    # Delete the entries for the forum in the ForumsRead and TopicsRead
    # relation
    bb_f.ForumsRead.query.filter_by(forum_id=self.id).delete()
    bb_f.TopicsRead.query.filter_by(forum_id=self.id).delete()

    # Delete the forum
    bb_f.db.session.delete(self)
    bb_f.db.session.commit()

    # Update the users post count
    if users:
        users_list = []
        for user in users:
            user.post_count = bb_f.Post.query.filter_by(user_id=user.id).count()
            users_list.append(user)
        bb_f.db.session.add_all(users_list)
        bb_f.db.session.commit()

    return self

bb_f.Forum.delete = delete_forum

_delete_topic = bb_f.Topic.delete

def delete_topic(self, users=None):
    # need to remove reported posts
    posts = bb_f.db.session.query(bb_f.Post.id).filter_by(topic_id=self.id)
    reports = bb_f.db.session.query(bb_f.Report).filter(bb_f.Report.post_id.in_(posts)).all()
    for report in reports:
        report.delete()
    return _delete_topic(self, users=users)


bb_f.Topic.delete = delete_topic




BARRED_VIEWS = [

#    'forum.index',
#    'forum.view_category',
#    'forum.view_forum',
#    'forum.view_topic',
#    'forum.view_post',
#    'forum.new_topic',
#    'forum.delete_topic',
#    'forum.lock_topic',
#    'forum.unlock_topic',
#    'forum.move_topic',
#    'forum.merge_topic',
#    'forum.new_post',
#    'forum.reply_post',
#    'forum.edit_post',
#    'forum.delete_post',
#    'forum.report_post',
#    'forum.raw_post',
#    'forum.markread',
#    'forum.who_is_online',
#    'forum.memberlist',
#    'forum.topictracker',
#    'forum.track_topic',
#    'forum.untrack_topic',
#    'forum.search',
#    'user.profile',
#    'user.view_all_topics',
#    'user.view_all_posts',
#    'user.settings',
#    'user.change_password',
#    'user.change_email',
#    'user.change_user_details',
#    'user.inbox',
#    'user.view_message',
#    'user.sent',
#    'user.trash',
#    'user.drafts',
    'user.new_message',
    'user.edit_message',
    'user.move_message',
    'user.restore_message',
    'user.delete_message',
#    'auth.login',
#    'auth.reauth',
#    'auth.logout',
#    'auth.register',
#    'auth.forgot_password',
#    'auth.reset_password',
#    'management.overview',
    'management.settings',
    'management.users',
    'management.edit_user',
    'management.delete_user',
    'management.add_user',
#    'management.banned_users',
#    'management.ban_user',
#    'management.unban_user',
#    'management.reports',
#    'management.unread_reports',
#    'management.report_markread',
#    'management.groups',
#    'management.edit_group',
#    'management.delete_group',
#    'management.add_group',
#    'management.forums',
#    'management.edit_forum',
#    'management.delete_forum',
#    'management.add_forum',
#    'management.add_category',
#    'management.edit_category',
#    'management.delete_category',
    'management.plugins',
    'management.enable_plugin',
    'management.disable_plugin',
    'management.uninstall_plugin',
    'management.install_plugin',

]


def block_routes(app):
    ''' remove routes for views we do not want '''
    rules = []
    for rule in app.url_map._rules:
        if rule.endpoint not in BARRED_VIEWS:
            # print rule.endpoint, rule.rule
            rules.append(rule)

    app.url_map._rules = rules
