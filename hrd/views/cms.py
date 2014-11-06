from flask import render_template, request, abort, redirect

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool,
                 permission, permission_content, get_str, lang_codes)
from hrd.models import Cms


@app.route('/admin')
def admin():
    return render_template('index.html')


@app.route('/admin/translation')
def translation():
    permission('translatior')
    return render_template('admin/translation.html')


@app.route('/admin/content')
def content():
    permission('content_manage')
    return render_template('admin/content.html')


@app.route('/admin/cms_edit/<id>', methods=['GET', 'POST'])
def cms_edit(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang=lang, current=True)
    page = page.first()
    if not page and lang != 'en':
        page = Cms.query.filter_by(page_id=id, lang='en', current=True)
        if not page:
            abort(404)
        return cms_trans(id=id)
    if not page:
        abort(404)
    if page.status == 'publish':
        return cms_reedit(id=id)
    if request.method == 'POST':
        page.title = get_str('title')
        page.content = get_str('content')
        page.status = 'edit'
        db.session.add(page)
        if lang == 'en':
            locked = {
                'active': get_bool('active'),
                'url': get_str('url'),
            }
            Cms.query.filter_by(page_id=page.page_id).update(locked)
        db.session.commit()
        return redirect(url_for_admin('cms_preview', id=id))
    if lang != 'en':
        trans = Cms.query.filter_by(page_id=page.page_id, lang='en',
                                    current=True).first()
    else:
        trans = {}
    translations = get_trans(id)
    return render_template('admin/cms_edit.html', page=page, trans=trans,
                          translations=translations)


@app.route('/admin/cms_reedit/<id>', methods=['POST'])
def cms_reedit(id):
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, status='publish', lang=lang,
                               current=True).first()
    if not page:
        abort(404)
    new_page = Cms(
        lang=lang,
        page_id=page.page_id,
        content=page.content,
        title=page.title,
        url=page.url,
        status='edit',
        current=True,
        published=True
    )
    db.session.add(new_page)
    page.current = False
    db.session.add(page)
    db.session.commit()
    return redirect(url_for_admin('cms_edit', id=new_page.page_id))


@app.route('/admin/cms_delete/<id>', methods=['POST'])
def cms_delete(id):
    permission('content_manage')
    Cms.query.filter_by(page_id=id).delete()
    db.session.commit()
    return redirect(url_for_admin('cms_list'))


@app.route('/admin/cms_new/', methods=['POST'])
def cms_new():
    permission('content_manage')
    lang = 'en'
    page = Cms(lang=lang)
    page.status = 'edit'
    db.session.add(page)
    db.session.commit()
    return redirect(url_for_admin('cms_edit', id=page.page_id))


STATES = {
    'approve': 'edit',
    'approved': 'approve',
    'publish': 'approved',
}


@app.route('/admin/cms_state/<id>/<state>', methods=['POST'])
def cms_state(id, state):
    lang = get_admin_lang()
    permission_content(lang)
    if state not in STATES:
        abort(403)
    page = Cms.query.filter_by(page_id=id, status=STATES[state], lang=lang,
                               current=True).first()
    if not page:
        abort(403)
    if state == 'publish':
        page.published = True
        old_page = Cms.query.filter_by(page_id=id, status='publish',
                                       lang=lang).first()
        if old_page:
            old_page.status = 'archive'
            db.session.add(old_page)
    page.status = state
    db.session.add(page)
    db.session.commit()
    return redirect(url_for_admin('cms_preview', id=id))


@app.route('/page/<id>')
def cms_page(id):
    lang = get_admin_lang()
    lang = request.environ['LANG']
    page = Cms.query.filter_by(page_id=id, lang=lang, status='publish').first()
    if not page:
        page = Cms.query.filter_by(page_id=id, lang='en', status='publish').first()
        if not page:
            abort(404)
    return render_template('page.html', page=page)

@app.route('/<id>')
@app.route('/')
def cms_page2(id=''):
    id = '/%s' % id
    lang = get_admin_lang()
    lang = request.environ.get('LANG', 'en')
    page = Cms.query.filter_by(url=id, lang=lang, status='publish').first()
    if not page:
        page = Cms.query.filter_by(url=id, lang='en', status='publish').first()
        if not page:
            abort(404)
    return render_template('page.html', page=page)


@app.route('/admin/cms_preview/<id>')
def cms_preview(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang=lang, current=True).first()
    if not page:
        page = Cms.query.filter_by(page_id=id, lang='en', current=True).first()
        if not page:
            abort(404)
        page = None
    translations = get_trans(id)
    return render_template('admin/cms_preview.html', page=page, translations=translations)


@app.route('/admin/cms_trans/<id>', methods=['POST'])
def cms_trans(id):
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang='en', current=True).first()
    if not page:
        abort(404)
    exists = Cms.query.filter_by(page_id=page.page_id, lang=lang, current=True).first()
    if exists:
        return redirect(url_for_admin('cms_edit', id=page.page_id))
    trans = Cms(lang=lang)
    trans.status = 'edit'
    trans.page_id = page.page_id
    trans.active = page.active
    trans.url = page.url
    db.session.add(trans)
    db.session.commit()
    return redirect(url_for_admin('cms_edit', id=trans.page_id))


@app.route('/admin/cms')
def cms_list():
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    pages = Cms.query.filter_by(lang=lang, current=True)
    pages = pages.order_by('title')
    for page in pages:
        p = Cms.query.filter_by(page_id=page.page_id, lang=lang,
                                status='publish').first()
        page.has_published = bool(p)
    if lang == 'en':
        missing = []
        trans = {}
    else:
        # missing pages
        trans = db.session.query(Cms.page_id).filter_by(lang=lang)
        missing = db.session.query(Cms).filter_by(lang='en', current=True)
        missing = missing.filter(db.not_(Cms.page_id.in_(trans)))
    status = list_status()
    return render_template('admin/cms_list.html', pages=pages, lang=lang,
                           missing=missing, trans=trans, status=status)

def list_status():
    results = {}
    for lang in lang_codes:
        # Unpublished
        unpublished = Cms.query.filter_by(lang=lang, current=True).filter(Cms.status != 'publish').count()
        # Missing
        trans = db.session.query(Cms.page_id).filter_by(lang=lang)
        missing = db.session.query(Cms).filter_by(lang='en', current=True)
        missing = missing.filter(db.not_(Cms.page_id.in_(trans))).count()
        results[lang] = {'missing':missing, 'unpublished':unpublished}
    return results


def get_trans(id):
    results = {}
    rows = db.session.query(Cms.lang, Cms.status).filter_by(page_id=id, current=True)
    t = {}
    for row in rows:
        t[row.lang] = row.status
    for lang in lang_codes:
        if lang in t:
            if t[lang] == 'publish':
                results[lang] = {'missing':0}
            else:
                results[lang] = {'unpublished':1}
        else:
            results[lang] = {'missing':1}
    return results


def set_menu():
    request.environ['MENU_PATH'] = url_for_admin('cms_list')[3:]
