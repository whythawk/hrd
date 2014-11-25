import uuid
import os.path

from flask import (render_template, request, abort, redirect,
                   send_from_directory)

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool, get_int,
                 permission, permission_content, get_str, lang_codes)
from hrd.models import MenuItem, Cms


@app.route('/admin/menu')
def menu_list():
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    menu_items = MenuItem.query.filter_by(lang=lang, parent_menu_id=None)
    menu_items = menu_items.order_by('"order"', 'title')
    if lang == 'en':
        missing = []
        trans = {}
    else:
        # missing menu_items
        trans = db.session.query(MenuItem.menu_id).filter_by(lang=lang)
        missing = db.session.query(MenuItem).filter_by(lang='en')
        missing = missing.filter(db.not_(MenuItem.menu_id.in_(trans)))
    status = list_status()
    return render_template('admin/menu_list.html', menu_items=menu_items, lang=lang,
                           missing=missing, trans=trans, status=status)


def list_status():
    results = {}
    for lang in lang_codes:
        # missing categories
        trans = db.session.query(MenuItem.menu_id).filter_by(
            lang=lang
        )
        missing = db.session.query(MenuItem).filter_by(
            lang='en'
        )
        missing = missing.filter(
            db.not_(MenuItem.menu_id.in_(trans))
        ).count()
        # missing codes
#        trans = db.session.query(Code.code_id).filter_by(lang=lang).filter(
#            Code.menu_id.in_(cat_trans)
#        )
#        missing_codes = db.session.query(Code).filter_by(lang='en').filter(
#            Code.menu_id.in_(cat_trans)
#        )
#
#        missing_codes = missing_codes.filter(
#            db.not_(Code.code_id.in_(trans))
#        ).count()

        results[lang] = {'missing': missing,
                         'unpublished': 0}
    return results

@app.route('/admin/menu_new', methods=['POST'])
@app.route('/admin/menu_new/<id>', methods=['POST'])
def menu_new(id=None):
    lang = 'en'
    menu_item = MenuItem(lang=lang)
    menu_item.active = False
    if id:
        menu_item.parent_menu_id = id
    db.session.add(menu_item)
    db.session.commit()
    return redirect(url_for_admin('menu_edit', id=menu_item.menu_id))


@app.route('/admin/menu_delete/<id>', methods=['POST'])
def menu_delete(id):
    permission('content_manage')
    MenuItem.query.filter_by(menu_id=id).delete()
    db.session.commit()
    return redirect(url_for_admin('menu_list'))



@app.route('/admin/menu_edit/<id>', methods=['GET', 'POST'])
def menu_edit(id):
    set_menu()
    lang = get_admin_lang()
    menu_item = MenuItem.query.filter_by(menu_id=id, lang=lang).first()
    if not menu_item and lang != 'en':
        menu_item = MenuItem.query.filter_by(menu_id=id, lang='en').first()
        if not menu_item:
            abort(404)
    if not menu_item:
        abort(404)
    if request.method == 'POST' and 'title' in request.form:
        if menu_item.lang != lang:
            menu_item = reedit(menu_item)
        menu_item.title = request.form['title']
        db.session.add(menu_item)
        db.session.commit()
        # Update locked fields
        if lang == 'en':
            locked = {
                'active': get_bool('active'),
                'private': get_bool('private'),
                'item': get_str('item'),
                'order': get_int('order', 99),
            }
            MenuItem.query.filter_by(
                menu_id=id
            ).update(locked)
        db.session.commit()
        return redirect(url_for_admin('menu_list'))
    if lang != 'en':
        trans = MenuItem.query.filter_by(menu_id=menu_item.menu_id,
                                         lang='en').first()
    else:
        trans = {}
    translations = get_trans(id)
    options = []
    if lang == 'en':
        options = [
            {'value': 'orgs', 'name': 'Special: Organisation search'},
            {'value': 'res', 'name': 'Special: Resources'},
        ]

        menu_items = db.session.query(Cms.url, Cms.title).filter_by(
            lang='en', active=True, status='publish'
        )
        for i in menu_items:
            options.append({'value': i.url, 'name': 'Page: %s' %i.title})
    elif menu_item.lang == 'en':
        menu_item = MenuItem()
    return render_template('admin/menu_edit.html', menuitem=menu_item,
                           trans=trans, options=options,
                           translations=translations)


def reedit(menu_item):
    lang = get_admin_lang()
    new_menu_item = MenuItem(
        lang=lang,
        menu_id=menu_item.menu_id,
        item=menu_item.item,
        active=menu_item.active,
        private=menu_item.private,
    )
    db.session.add(new_menu_item)
    db.session.commit()
    return new_menu_item



def get_trans(id):
    results = {}
    rows = db.session.query(MenuItem.lang).filter_by(menu_id=id)
    t = [row.lang for row in rows]
    for lang in lang_codes:
        if lang in t:
            results[lang] = {'missing': 0, 'unpublished': 0}
        else:
            results[lang] = {'missing': 1}
    return results


def get_menu_items(lang):
    en_menu_items = MenuItem.query.filter_by(lang='en', active=True).order_by('"order"', 'title')
    if lang != 'en':
        trans_menu_items = MenuItem.query.filter_by(lang=lang, active=True).order_by('"order"', 'title')
        trans = {}
        for t in trans_menu_items:
            trans[t.item] = t.title
    else:
        trans = {}
    menu = []
    for m in en_menu_items:
        menu.append({
            'title': trans.get(m.item, m.title),
            'item': m.item,
            'private': m.private,
        })
    return menu


def set_menu():
    request.environ['MENU_PATH'] = url_for_admin('menu_list')[3:]
