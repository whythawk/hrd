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


def has_perm(permission):
    if permission in request.permissions:
        return True
    if 'sys_admin' in request.permissions:
        return True
    return False



hrd.app.jinja_env.globals.update(
    url_for_admin=hrd.url_for_admin,
    url_for=hrd.url_for,
    get_admin_lang=hrd.get_admin_lang,
    lang_html=hrd.lang_html,
    lang_pick=hrd.lang_pick,
    get_username=username,
    lang_list=hrd.lang_list,
    current_lang=hrd.current_lang,
    current_lang_name=hrd.current_lang_name,
    current_admin_lang=hrd.current_admin_lang,
    _=_,
    has_perm=has_perm,
    debug=hrd.DEBUG,
)
