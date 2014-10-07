from flask import render_template, request, abort, redirect

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool,
                 permission, permission_content, get_str)
from hrd.models import Cms


@app.route('/')
def index():
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
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang=lang, current=True)
    page = page.filter(Cms.status != 'publish').first()
    if not page:
        abort(404)
    if page.status == 'publish':
        return redirect(url_for_admin('cms_reedit', id=id), code=307)
    if request.method == 'POST':
        page.title = get_str('title')
        page.content = get_str('content')
        page.status = 'edit'
        db.session.add(page)
        if lang == 'en':
            locked = {
                'active': get_bool('active'),
            }
            Cms.query.filter_by(page_id=page.page_id).update(locked)
        db.session.commit()
        return redirect(url_for_admin('cms_preview', id=id))
    if lang != 'en':
        trans = Cms.query.filter_by(page_id=page.page_id, lang='en',
                                    current=True).first()
    else:
        trans = {}
    return render_template('admin/cms_edit.html', page=page, trans=trans)


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
        status='edit',
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
        abort(404)
    return render_template('page.html', page=page)


@app.route('/admin/cms_preview/<id>')
def cms_preview(id):
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang=lang, current=True).first()
    if not page:
        abort(404)
    return render_template('admin/cms_preview.html', page=page)


@app.route('/admin/cms_trans/<id>', methods=['POST'])
def cms_trans(id):
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang='en').first()
    if not page:
        abort(404)
    exists = Cms.query.filter_by(page_id=page.page_id, lang=lang).first()
    if exists:
        abort(403)
    trans = Cms(lang=lang)
    trans.status = 'edit'
    trans.page_id = page.page_id
    db.session.add(trans)
    db.session.commit()
    return redirect(url_for_admin('cms_edit', id=trans.page_id))


@app.route('/admin/cms')
def cms_list():
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
        missing = db.session.query(Cms).filter_by(lang='en')
        missing = missing.filter(db.not_(Cms.page_id.in_(trans)))
    return render_template('admin/cms_list.html', pages=pages, lang=lang,
                           missing=missing, trans=trans)
