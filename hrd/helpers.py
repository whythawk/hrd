# -*- coding: utf-8 -*-

import re
from datetime import datetime, timedelta

from flask import request, session, Markup
from babel.numbers import format_number as _format_number
from babel import Locale
from flask.ext.login import current_user

import flaskbb.forum.models as bb_f
from flaskbb.utils.settings import flaskbb_config


import hrd
import views.menu
import views.user
import models


# for fake translations
t1 = u'aBCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
t2 = u'ÅßÇÐËƑĢĦĨĴĶŁϺÑÕÞƍŘŠŦÙƔŴЖÝȤåɓçđêʄǧħîĵĸƖɱñðþƣŗšŧüɤŵϰŷż'
trans_table = dict(zip([ord(char) for char in t1], t2))


def _(value):
    if request.environ['LANG'] == 'en':
        return value
    else:
        return mangle(value)


def mangle(value):
    spf_reg_ex = "\+?(0|'.)?-?\d*(.\d*)?[\%bcdeufosxX]"
    extract_reg_ex = '(\%\([^\)]*\)' + spf_reg_ex + \
                     '|\[\d*\:[^\]]*\]' + \
                     '|\{[^\}]*\}' + \
                     '|<[^>}]*>' + \
                     '|\%((\d)*\$)?' + spf_reg_ex + ')'
    matches = re.finditer(extract_reg_ex, value)
    position = 0
    translation = u''
    for match in matches:
        translation += unicode(
            value[position:match.start()]
        ).translate(trans_table)
        position = match.end()
        translation += match.group(0)
    translation += unicode(value[position:]).translate(trans_table)
    return translation


def username():
    user = current_user
    if user:
        try:
            return user.username
        except:
            pass
    return False


def user_id():
    user = request.user
    if user:
        return user.id
    return False


def user_logged_in():
    if not hrd.config.GA_ENABLED:
        return True
    if session.get('ga') == 'authorized':
        return True
    return False

def has_perm(permission):
    try:
        request.permission
    except AttributeError:
        request.permissions = views.user.get_users_permissions(current_user)
    if isinstance(permission, basestring):
        permission = [permission]
    if not set(permission) & set(request.permissions):
        if 'sys_admin' not in request.permissions:
            return False
    return True


def search_subset(set1, set2):
    return set([c['code'] for c in set1]) & set(set2)


def menu_class(href, force_right, css_class):
    cls = []
    if force_right:
        cls.append('navbar-right')
    if href !='#' and href[3:] == request.environ.get(
        'MENU_PATH', request.environ['PATH_INFO']
    ):
        cls.append('active')
    if css_class:
        cls.append(css_class)
    if not cls:
        return ''
    return ' class="%s"' % ' '.join(cls)


def sub_menu_item(text, href, force_right=False):
    cls = 'nav-column col-md-2'
    if force_right:
        cls += ' navbar-right'
    return '<div class="%s"><a href="%s">%s</a></div>' % (cls, href, text)


def get_trans_state(value):
    if value.get('missing'):
        return 'no-translation'
    if value.get('unpublished'):
        return 'old-translation'
    return ''


def url_clean(qs):
    url = request.environ['CURRENT_URL']
    from urllib import urlencode
    from urlparse import urlparse, urlunparse, parse_qs

    u = urlparse(url)
    query = parse_qs(u.query)
    query.pop(qs, None)
    u = u._replace(query=urlencode(query, True))
    url = urlunparse(u)
    if '?' not in url:
        url += '?'
    return url


def none_to_empty_str(arg):
    return arg or ''


def locale_language_name(language_code):
    l = Locale.parse(language_code)
    lang = request.environ['LANG']
    return l.get_display_name(lang)


def format_number(arg):
    if arg is None:
        return 'Unknown'
    lang = request.environ['LANG']
    return _format_number(arg, locale=lang)


STATE_NICE_NAME = {
    'edit': 'Needs updating',
    'approve': 'Awaiting approval',
    'approved': 'Awaiting publication',
    'publish': 'Published',
}


def cms_state_nice_name(state):
    return STATE_NICE_NAME[state]

def organization_name(value):
    org = models.Organisation.query.filter_by(org_id=value).first()
    if not org:
        return _('None')
    return org.name

def unread_forums(forum_id):
    user = current_user
    read_cutoff = datetime.utcnow() - timedelta(
        days=flaskbb_config["TRACKER_LENGTH"])

    if  read_cutoff < user.date_joined:
        read_cutoff = user.date_joined - timedelta(days=1)

   # fetch the unread posts in the forum
    unread_count = bb_f.Topic.query.with_entities(bb_f.Topic.id).\
        outerjoin(bb_f.TopicsRead,
                  bb_f.db.and_(bb_f.TopicsRead.topic_id == bb_f.Topic.id,
                          bb_f.TopicsRead.user_id == user.id)).\
        outerjoin(bb_f.ForumsRead,
                  bb_f.db.and_(bb_f.ForumsRead.forum_id == bb_f.Topic.forum_id,
                          bb_f.ForumsRead.user_id == user.id)).\
        filter(bb_f.Topic.last_updated > read_cutoff).\
        filter(bb_f.Topic.forum_id == forum_id).\
        filter(bb_f.db.or_(bb_f.ForumsRead.cleared == None,
                           bb_f.ForumsRead.cleared < bb_f.Topic.last_updated)).\
       filter(
               bb_f.db.or_(bb_f.TopicsRead.last_read == None,
                      bb_f.TopicsRead.last_read < bb_f.Topic.last_updated
                          )).count()
    return unread_count


def unread_topics():
    user = current_user
    read_cutoff = datetime.utcnow() - timedelta(
        days=flaskbb_config["TRACKER_LENGTH"])

    if  read_cutoff < user.date_joined:
        read_cutoff = user.date_joined - timedelta(days=1)

   # fetch the unread posts in the forum
    unread_count = bb_f.Topic.query.with_entities(bb_f.Topic.id).\
        outerjoin(bb_f.TopicsRead,
                  bb_f.db.and_(bb_f.TopicsRead.topic_id == bb_f.Topic.id,
                          bb_f.TopicsRead.user_id == user.id)).\
        outerjoin(bb_f.ForumsRead,
                  bb_f.db.and_(bb_f.ForumsRead.forum_id == bb_f.Topic.forum_id,
                          bb_f.ForumsRead.user_id == user.id)).\
        filter(bb_f.Topic.last_updated > read_cutoff).\
        filter(bb_f.db.or_(bb_f.ForumsRead.cleared == None,
                           bb_f.ForumsRead.cleared < bb_f.Topic.last_updated)).\
       filter(
               bb_f.db.or_(bb_f.TopicsRead.last_read == None,
                      bb_f.TopicsRead.last_read < bb_f.Topic.last_updated
                          )).count()

    if unread_count:
        return Markup(' <span class="badge">%s</span>' % unread_count)
    return ''

hrd.app.jinja_env.globals.update(
    unread_topics=unread_topics,
    unread_forums=unread_forums,
    url_for_admin=hrd.url_for_admin,
    url_for=hrd.url_for,
    url_for_fixed=hrd.url_for_fixed,
    get_admin_lang=hrd.get_admin_lang,
    get_admin_lang_dir=hrd.current_admin_lang_dir,
    lang_html=hrd.lang_html,
    lang_html_body=hrd.lang_html_body,
    lang_pick=hrd.lang_pick,
    get_username=username,
    get_user_id=user_id,
    current_user=current_user,
    lang_list=hrd.lang_list,
    current_lang=hrd.current_lang,
    current_lang_name=hrd.current_lang_name,
    current_admin_lang=hrd.current_admin_lang,
    has_perm=has_perm,
    user_logged_in=user_logged_in,
    content_trans=hrd.content_trans,
    menu_class=menu_class,
    sub_menu_item=sub_menu_item,
    debug=hrd.DEBUG,
    search_subset=search_subset,
    get_trans_state=get_trans_state,
    get_menu_items=views.menu.get_menu_items,
    cms_state_nice_name=cms_state_nice_name,
    url_clean=url_clean,
    none_to_empty_str=none_to_empty_str,
    format_number=format_number,
    locale_language_name=locale_language_name,
    organization_name=organization_name,
)
