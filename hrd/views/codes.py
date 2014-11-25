from flask import render_template, request, abort, redirect

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool,
                 get_int, lang_codes)
from hrd.models import Category, Code

CAT_TYPES = ['org', 'res']


def check_cat_type(cat_type):
    if cat_type not in CAT_TYPES:
        abort(500)


@app.route('/admin/category_new/<cat_type>', methods=['POST'])
def category_new(cat_type):
    check_cat_type(cat_type)
    lang = 'en'
    category = Category(lang=lang)
    category.status = 'edit'
    category.cat_type = cat_type
    db.session.add(category)
    db.session.commit()
    return redirect(url_for_admin('category_edit',
                            id=category.category_id,
                            cat_type=cat_type))


@app.route('/admin/category_edit/<cat_type>/<id>', methods=['GET', 'POST'])
def category_edit(id, cat_type):
    set_menu(cat_type)
    lang = get_admin_lang()
    category = Category.query.filter_by(category_id=id, lang=lang).first()
    if not category and lang != 'en':
        category = Category.query.filter_by(category_id=id, lang='en').first()
        if not category:
            abort(404)
        return category_trans(id, cat_type)
    if not category:
        abort(404)
    if lang != 'en':
        trans = Category.query.filter_by(category_id=category.category_id,
                                         lang='en').first()
    else:
        trans = {}
    if request.method == 'POST':
        category.title = request.form['title']
        category.description = request.form['description']
        db.session.add(category)
        # Update locked fields
        if lang == 'en':
            locked = {
                'active': get_bool('active'),
                'order': get_int('order', 99),
            }
            Category.query.filter_by(
                category_id=category.category_id
            ).update(locked)
        db.session.commit()
        return redirect(url_for_admin('category_list', cat_type=cat_type))
    translations = get_cat_trans(category.category_id)
    return render_template('admin/category_edit.html', category=category,
                           trans=trans, cat_type=cat_type,
                           translations=translations)


def get_cat_trans(id):
    results = {}
    rows = db.session.query(Category.lang).filter_by(category_id=id)
    t = [row.lang for row in rows]
    for lang in lang_codes:
        if lang in t:
            results[lang] = {'missing': 0, 'unpublished': 0}
        else:
            results[lang] = {'missing': 1}
    return results


def get_code_trans(id):
    results = {}
    rows = db.session.query(Code.lang).filter_by(code_id=id)
    t = [row.lang for row in rows]
    for lang in lang_codes:
        if lang in t:
            results[lang] = {'missing': 0, 'unpublished': 0}
        else:
            results[lang] = {'missing': 1}
    return results


@app.route('/admin/code_edit/<cat_type>/<id>', methods=['GET', 'POST'])
def code_edit(id, cat_type):
    set_menu(cat_type)
    lang = get_admin_lang()
    code = Code.query.filter_by(code_id=id, lang=lang).first()
    if not code and lang != 'en':
        code = Code.query.filter_by(code_id=id, lang='en').first()
        if not code:
            abort(404)
        return code_trans(id, cat_type)
    if not code:
        abort(404)
    if request.method == 'POST':
        code.title = request.form['title']
        code.description = request.form['description']
        db.session.add(code)
        if lang == 'en':
            locked = {
                'active': get_bool('active'),
                'order': get_int('order', 99),
            }
            Code.query.filter_by(code_id=code.code_id).update(locked)
        db.session.commit()
        return redirect(url_for_admin('category_list', cat_type=cat_type))

    if lang != 'en':
        trans = Code.query.filter_by(code_id=code.code_id, lang='en').first()
    else:
        trans = {}
    cats = Category.query.filter_by(lang='en', current=True)
    categories = []
    for cat in cats:
        categories.append({'name': cat.title, 'value': cat.category_id})

    translations = get_code_trans(code.code_id)
    return render_template('admin/code_edit.html', code=code, trans=trans,
                           categories=categories, cat_type=cat_type,
                           translations=translations)


@app.route('/admin/category_trans/<cat_type>/<id>', methods=['POST'])
def category_trans(id, cat_type):
    lang = get_admin_lang()
    category = Category.query.filter_by(category_id=id, lang='en').first()
    if not category:
        abort(404)
    exists = Category.query.filter_by(category_id=category.category_id,
                                      lang=lang).first()
    if exists:
        abort(403)
    trans = Category(lang=lang)
    trans.status = 'edit'
    trans.category_id = id
    trans.cat_type = cat_type
    db.session.add(trans)
    db.session.commit()
    return redirect(url_for_admin('category_edit', id=id, cat_type=cat_type))


@app.route('/admin/code_trans/<cat_type>/<id>', methods=['POST'])
def code_trans(id, cat_type):
    lang = get_admin_lang()
    code = Code.query.filter_by(code_id=id, lang='en').first()
    if not code:
        abort(404)
    exists = Code.query.filter_by(code_id=code.code_id, lang=lang).first()
    if exists:
        abort(403)
    trans = Code(lang=lang)
    trans.status = 'edit'
    trans.code_id = id
    trans.category_id = code.category_id
    db.session.add(trans)
    db.session.commit()
    return redirect(url_for_admin('code_edit', id=id, cat_type=cat_type))


@app.route('/admin/category/<cat_type>')
def category_list(cat_type):
    set_menu(cat_type)
    check_cat_type(cat_type)
    lang = get_admin_lang()
    categories = Category.query.filter_by(
        lang=lang, current=True, cat_type=cat_type
    )
    categories = categories.order_by('"order"', 'title')
    all_ = all_codes(lang, cat_type)
    if lang == 'en':
        missing_cat = []
        m_codes = []
    else:
        # missing categories
        trans = db.session.query(Category.category_id).filter_by(
            lang=lang, cat_type=cat_type
        )
        missing_cat = db.session.query(Category).filter_by(
            lang='en', cat_type=cat_type
        )
        missing_cat = missing_cat.filter(
            db.not_(Category.category_id.in_(trans))
        )
        # missing codes
        trans = db.session.query(Code.code_id).filter_by(lang=lang)
        missing_codes = db.session.query(Code).filter_by(lang='en')
        missing_codes = missing_codes.filter(db.not_(Code.code_id.in_(trans)))
        m_codes = {}
        for code in missing_codes:
            if code.category_id not in m_codes:
                m_codes[code.category_id] = []
            m_codes[code.category_id].append(code)
    status = list_status(cat_type)
    return render_template('admin/category_list.html',
                           categories=categories,
                           missing_cat=missing_cat,
                           m_codes=m_codes,
                           all=all_,
                           cat_type=cat_type,
                           status=status,
                           lang=lang)


def list_status(cat_type):
    results = {}
    for lang in lang_codes:
        # missing categories
        cat_trans = db.session.query(Category.category_id).filter_by(
            lang=lang, cat_type=cat_type
        )
        missing_cat = db.session.query(Category).filter_by(
            lang='en', cat_type=cat_type
        )
        missing_cat = missing_cat.filter(
            db.not_(Category.category_id.in_(cat_trans))
        ).count()
        # missing codes
        trans = db.session.query(Code.code_id).filter_by(lang=lang).filter(
            Code.category_id.in_(cat_trans)
        )
        missing_codes = db.session.query(Code).filter_by(lang='en').filter(
            Code.category_id.in_(cat_trans)
        )

        missing_codes = missing_codes.filter(
            db.not_(Code.code_id.in_(trans))
        ).count()

        results[lang] = {'missing': missing_cat + missing_codes,
                         'unpublished': 0}
    return results


@app.route('/admin/code_new/<cat_type>/<category_id>', methods=['POST'])
def code_new(category_id, cat_type):
    lang = 'en'
    code = Code(lang=lang)
    code.status = 'edit'
    code.category_id = category_id
    db.session.add(code)
    db.session.commit()
    return redirect(url_for_admin('code_edit', id=code.code_id, cat_type=cat_type))


@app.route('/admin/category_delete/<cat_type>/<category_id>', methods=['POST'])
def category_delete(category_id, cat_type):
    # Prevent delet if there are codes for the category
    if Code.query.filter_by(category_id=category_id).all():
        return redirect(url_for_admin('category_list', cat_type=cat_type))
    Category.query.filter_by(category_id=category_id).delete()
    db.session.commit()
    return redirect(url_for_admin('category_list', cat_type=cat_type))


@app.route('/admin/code_delete/<cat_type>/<code_id>', methods=['POST'])
def code_delete(code_id, cat_type):
    Code.query.filter_by(code_id=code_id).delete()
    db.session.commit()
    return redirect(url_for_admin('category_list', cat_type=cat_type))


def all_codes(lang='en', cat_type=''):
    check_cat_type(cat_type)
    out = []
    cats = Category.query.filter_by(lang=lang, current=True, cat_type=cat_type)
    cats = cats.order_by('"order"', 'title')
    for cat in cats:
        cat_codes = Code.query.filter_by(lang=lang, current=True,
                                         category_id=cat.category_id)
        cat_codes = cat_codes.order_by('"order"', 'title')
        codes = []
        for code in cat_codes:
            codes.append({
                'code': code.code_id,
                'title': code.title,
                'desc': code.description,
                'id': code.id,
                'code_id': code.code_id,
                'active': code.active,
            })
        out.append({
            'title': cat.title,
            'id': cat.id,
            'category_id': cat.category_id,
            'active': cat.active,
            'codes': codes,
        })
    return out

def cat_codes(lang='en', cat_type=''):
    check_cat_type(cat_type)
    out = []
    cats = Category.query.filter_by(lang=lang, current=True, cat_type=cat_type)
    cats = cats.order_by('"order"', 'title')
    for cat in cats:
        cat_codes = Code.query.filter_by(lang=lang, current=True,
                                         category_id=cat.category_id)
        cat_codes = cat_codes.order_by('"order"', 'title')
        codes = []
        for code in cat_codes:
            codes.append(code.code_id)
        out.append(codes)
    return out


def set_menu(cat_type):
    request.environ['MENU_PATH'] = url_for_admin('category_list',
                                                 cat_type=cat_type)[3:]
