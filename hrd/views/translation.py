import re
import uuid
import os.path

from sqlalchemy.util import OrderedDict
from flask import (render_template, request, abort, redirect,
                   send_from_directory)
from babel.messages.plurals import PLURALS

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool, get_int,
                 permission, permission_content, get_str, lang_codes)
from hrd.models import Translation


@app.route('/admin/translation')
def translation_list():
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    translations_en = Translation.query.filter_by(lang='en', active=True).order_by('string', 'plural')
    missing = OrderedDict()
    for t in translations_en:
        missing[(t.string, t.plural)] = t.id

    translations = Translation.query.filter_by(lang=lang, active=True).order_by('string', 'plural').all()
    for t in translations:
        if t.trans0:
            missing.pop((t.string, t.plural), None)

    status = list_status()
    return render_template('admin/translation_list.html',
                           translations=translations,
                           status=status,
                           missing=missing)

@app.route('/admin/translation/<id>', methods=['GET', 'POST'])
def translation_edit(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    info = PLURALS.get(lang)
    if not info:
        abort(500)
    plurals, rule = info
    translation = Translation.query.filter_by(id=id, active=True).one()
    if not translation:
        abort(404)
    if not translation.plural:
        plurals = 1
    errors = []
    metadata = get_metadata(translation.string)
    if request.method == 'POST' and 'trans0' in request.form:
        if translation.lang != lang:
            translation = Translation(
                string=translation.string,
                plural=translation.plural,
                lang=lang,
                active=True,
            )
        for i in range(plurals):
            key = 'trans%s' % i
            value = get_str(key)
            if not value:
                errors.append('translation[%s] needs completing' % i)
            m = get_metadata(value)
            if  m ^ metadata:
                if metadata - m:
                    errors.append('translation[%s] Does not contain needed metadata %s' % (i, clean_meta(metadata - m)))
                if m - metadata:
                    errors.append('translation[%s] contain unwanted metadata %s.  This must be removed' % (i, clean_meta(m - metadata)))
            setattr(translation, key, value)
        if not errors:
            db.session.add(translation)
            db.session.commit()
            return redirect(url_for_admin('translation_list'))

    if translation.lang != lang:
        translation = Translation(string=translation.string, plural=translation.plural)
    return render_template('admin/translation_edit.html',
                           rule=rule,
                           plurals=plurals,
                           errors=errors,
                           metadata=metadata,
                           translation=translation)


def clean_meta(meta):
    return ', '.join(meta)


def get_metadata(value):
    spf_reg_ex = "\+?(0|'.)?-?\d*(.\d*)?[\%bcdeufosxX]"
    extract_reg_ex = '(\%\([^\)]*\)' + spf_reg_ex + \
                     '|\[\d*\:[^\]]*\]' + \
                     '|\{[^\}]*\}' + \
                     '|<[^>}]*>' + \
                     '|\%((\d)*\$)?' + spf_reg_ex + ')'
    matches = re.finditer(extract_reg_ex, value)
    metadata = []
    for match in matches:
        metadata.append(match.group(0))
    return set(metadata)




def list_status():
    def get_set(lang):
        t = db.session.query(
            Translation.string,
            Translation.plural
        ).filter_by(lang=lang, active=True).all()
        return set(t)
    set_en = get_set('en')
    results = {}
    for lang in lang_codes:
        # missing categories
        results[lang] = {'missing': len(set_en - get_set(lang)),
                         'unpublished': 0}
    return results


def set_menu():
    request.environ['MENU_PATH'] = url_for_admin('translation_list')[3:]

