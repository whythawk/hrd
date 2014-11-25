# -*- coding: utf-8 -*-

import re

from flask import request

import hrd
import views.menu


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
    user = request.user
    if user:
        return user.name
    return False


def user_id():
    user = request.user
    if user:
        return user.id
    return False


def has_perm(permission):
    if permission in request.permissions:
        return True
    if 'sys_admin' in request.permissions:
        return True
    return False


def search_subset(set1, set2):
    return set([c['code'] for c in set1]) & set(set2)


def menu_class(href, force_right, css_class):
    cls = []
    if force_right:
        cls.append('navbar-right')
    if href[3:] == request.environ.get('MENU_PATH', request.environ['PATH_INFO']):
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


STATE_NICE_NAME = {
    'edit': 'Needs updating',
    'approve': 'Awaiting approval',
    'approved': 'Awaiting publication',
    'publish': 'Published',
}


def cms_state_nice_name(state):
    return STATE_NICE_NAME[state]


hrd.app.jinja_env.globals.update(
    url_for_admin=hrd.url_for_admin,
    url_for=hrd.url_for,
    url_for_fixed=hrd.url_for_fixed,
    get_admin_lang=hrd.get_admin_lang,
    lang_html=hrd.lang_html,
    lang_pick=hrd.lang_pick,
    get_username=username,
    get_user_id=user_id,
    lang_list=hrd.lang_list,
    current_lang=hrd.current_lang,
    current_lang_name=hrd.current_lang_name,
    current_admin_lang=hrd.current_admin_lang,
    has_perm=has_perm,
    menu_class=menu_class,
    sub_menu_item=sub_menu_item,
    debug=hrd.DEBUG,
    search_subset=search_subset,
    get_trans_state=get_trans_state,
    get_menu_items=views.menu.get_menu_items,
    cms_state_nice_name=cms_state_nice_name,
)
