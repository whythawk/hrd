# -*- coding: utf-8 -*-

import re

from flask import request

import hrd


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

def menu_class(href, force_right):
    cls = []
    if force_right:
        cls.append('navbar-right')
    if href[3:] == request.environ['PATH_INFO']:
        cls.append('active')
    if not cls:
        return ''
    return ' class="%s"' % ' '.join(cls)


def sub_menu_item(text, href, force_right=False):
    cls = 'nav-column col-md-2'
    if force_right:
        cls += ' navbar-right'
    return '<div class="%s"><a href="%s">%s</a></div>' % (cls, href, text)


hrd.app.jinja_env.globals.update(
    url_for_admin=hrd.url_for_admin,
    url_for=hrd.url_for,
    get_admin_lang=hrd.get_admin_lang,
    lang_html=hrd.lang_html,
    lang_pick=hrd.lang_pick,
    get_username=username,
    get_user_id=user_id,
    lang_list=hrd.lang_list,
    current_lang=hrd.current_lang,
    current_lang_name=hrd.current_lang_name,
    current_admin_lang=hrd.current_admin_lang,
    _=_,
    has_perm=has_perm,
    menu_class=menu_class,
    sub_menu_item=sub_menu_item,
    debug=hrd.DEBUG,
)
