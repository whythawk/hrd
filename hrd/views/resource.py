import os.path
from urlparse import urlparse
import uuid

import magic
from flask import (render_template, request, abort, redirect,
                   send_from_directory)
from flask import _request_ctx_stack
from werkzeug import secure_filename


from hrd import (app, db, url_for_admin, get_admin_lang, get_bool, config,
                 permission, permission_content, get_str, lang_codes)
from hrd.models import Resource, ResourceCodes
from hrd.views.codes import all_codes, cat_codes



@app.route('/admin/resource_file/<type>/<id>')
def resource_file(type, id):
    if type == 'live':
        resource = Resource.query.filter_by(
            resource_id=id, lang='en', status='publish'
        ).first()
    else:
        resource = Resource.query.filter_by(
            resource_id=id, lang='en', current=True
        ).first()
    return send_from_directory(app.config['UPLOAD_FOLDER'], resource.file)


def fix_url(url):
    if not url:
        return url
    o = urlparse(url)
    if o.scheme:
        return url
    return 'http://%s' % url


@app.route('/admin/resource_edit/<id>', methods=['GET', 'POST'])
def resource_edit(id):
    set_menu()
    permission_content('en')
    errors = []
    resource = Resource.query.filter_by(
        resource_id=id, current=True
    ).first()
    if not resource:
        abort(404)
    if request.method == 'POST' and 'name' in request.form:
        if resource.status == 'publish':
            resource = resource_reedit(resource)
        resource.name = get_str('name')
        resource.description = get_str('description')
        resource.status = 'edit'

        resource.lang = get_str('lang')
        resource.private = get_bool('private')
        resource.active = get_bool('active')

        resource.url = fix_url(get_str('url'))

        if get_bool('logo_remove'):
            resource.file = None

        logo = request.files['file']
        if logo:
            extension = os.path.splitext(logo.filename)[1]
            if extension: # and extension.lower() in config.ALLOWED_RESOURCES:
                filename = unicode(uuid.uuid4())
                filename += extension
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo.save(path)
                resource.file = filename
                # file info
                resource.filename = secure_filename(logo.filename)
                with magic.Magic() as m:
                    try:
                        resource.file_type = m. id_filename(path)
                    except:
                        resource.file_type = 'Unknown'
                with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                    try:
                        resource.mime_type = m. id_filename(path)
                    except:
                        resource.mime_type = 'Unknown'
                with magic.Magic(flags=magic.MAGIC_MIME_ENCODING) as m:
                    try:
                        resource.mime_encoding = m. id_filename(path)
                    except:
                        resource.mime_encoding = 'Unknown'
                try:
                    resource.file_size = os.stat(path).st_size
                except:
                    pass

            else:
                errors.append(
                    'The file uploaded is not of an allowed type'
                )


        db.session.add(resource)
        if True:
            # codes
            codes_data = all_codes('en', 'res')
            cats = [cat for cat in codes_data if cat['active']]
            cat_codes = []
            for cat in cats:
                cat_codes += cat['codes']
            codes = [code['code'] for code in cat_codes if code['active']]
            c_in = []
            c_out = []
            for code in codes:
                if get_bool(code):
                    c_in.append(code)
                else:
                    c_out.append(code)
            current = [
                c.code for c in ResourceCodes.query.filter_by(resource_id=id).all()
            ]
            for code in c_in:
                if code not in current:
                    code = ResourceCodes(resource_id=id, code=code)
                    db.session.add(code)
            for code in c_out:
                ResourceCodes.query.filter_by(resource_id=id, code=code).delete()

        db.session.commit()
        if not errors:
            return redirect(url_for_admin('resource_preview', id=id))

    codes = all_codes('en', 'res')
    current = [
        c.code for c in ResourceCodes.query.filter_by(resource_id=id).all()
    ]
    languages = []
    for code, name, dir_, active in config.LANGUAGE_LIST:
        languages.append({
            'name': '%s (%s)' % (name, code),
            'value':code,
        })
    return render_template('admin/resource_edit.html', resource=resource,
                           options=languages,
                           codes=codes, current=current, errors=errors)


def resource_reedit(resource):
    new_resource = Resource(
        lang=resource.lang,
        resource_id=resource.resource_id,
        description=resource.description,
        name=resource.name,
        status='edit',
        published=True,

        private=resource.private,
        active=resource.active,
        file=resource.file,

    )
    db.session.add(new_resource)
    resource.current = False
    db.session.add(resource)
    db.session.commit()
    return new_resource


@app.route('/admin/resource_delete/<id>', methods=['POST'])
def resource_delete(id):
    permission('content_manage')
    Resource.query.filter_by(resource_id=id).delete()
    db.session.commit()
    return redirect(url_for_admin('resource_list'))


@app.route('/admin/resource_new/', methods=['POST'])
def resource_new():
    permission('content_manage')
    lang = get_admin_lang()
    resource = Resource(lang=lang)
    resource.status = 'edit'
    db.session.add(resource)
    db.session.commit()
    return redirect(url_for_admin('resource_edit', id=resource.resource_id))


STATES = {
    'approve': 'edit',
    'approved': 'approve',
    'publish': 'approved',
}


@app.route('/admin/resource_state/<id>/<state>', methods=['POST'])
def resource_state(id, state):
    lang = get_admin_lang()
    permission_content('en')
    if state not in STATES:
        abort(403)
    resource = Resource.query.filter_by(
        resource_id=id, status=STATES[state], lang=lang, current=True
    ).first()
    if not resource:
        abort(403)
    if state == 'publish':
        resource.published = True
        old_resource = Resource.query.filter_by(
            resource_id=id, status='publish', lang=lang
        ).first()
        if old_resource:
            old_resource.status = 'archive'
            db.session.add(old_resource)
    resource.status = state
    db.session.add(resource)
    db.session.commit()
    return redirect(url_for_admin('resource_preview', id=id))


def update_translations(resource):
    trans = Resource.query.filter_by(resource_id=resource.resource_id)
    trans = trans.filter(db.not_(Resource.id == resource.id))
    trans = trans.filter(
        db.or_(
            Resource.status == 'publish', Resource.current == True
        )
    )

    for tran in trans:
        tran.address = resource.address
        tran.contact = resource.contact
        tran.phone = resource.phone
        tran.email = resource.email
        tran.pgp_key = resource.pgp_key
        tran.website = resource.website
        tran.active = resource.active
        tran.private = resource.private
        tran.file = resource.file
        db.session.add(tran)
    db.session.commit()


@app.route('/resource/<id>')
def resource(id):
    lang = get_admin_lang()
    lang = request.environ['LANG']
    resource = Resource.query.filter_by(
        resource_id=id, lang=lang, status='publish', active=True
    )

    resource = resource.first()
    if not resource:
        resource = Resource.query.filter_by(
            resource_id=id, lang='en', status='publish', active=True
        ).first()
        if not resource:
            abort(404)

    # only show public resources
    if not bool(request.user) and resource.private:
        abort(403)

    cat_codes = resource_cat_codes(lang, id)
    return render_template('admin/resource.html',
                           resource=resource,
                           cat_codes=cat_codes)


def resource_cat_codes(lang, id):
    codes = all_codes(lang, 'res')
    current = [
        c.code for c in ResourceCodes.query.filter_by(resource_id=id).all()
    ]
    out = []
    for cat in codes:
        found = []
        for code in cat['codes']:
            if code['code_id'] in current:
                found.append(code['title'])
        if found:
            out.append((cat['title'], ', '.join(found)))
    return out


@app.route('/admin/resource_preview/<id>')
def resource_preview(id):
    set_menu()
    lang = get_admin_lang()
    permission_content('en')
    resource = Resource.query.filter_by(
        resource_id=id, lang=lang, current=True
    ).first()
    if not resource:
        resource = Resource.query.filter_by(
            resource_id=id, lang='en', current=True
        ).first()
        if not resource:
            abort(404)
    translations = get_trans(id)
    cat_codes = resource_cat_codes(lang, id)
    ctx = _request_ctx_stack.top
    if ctx:
        ctx.babel_locale = lang
    request.environ['LANG'] = lang
    return render_template('admin/resource_preview.html', resource=resource,
                           cat_codes=cat_codes,
                           translations=translations)


def get_trans(id):
    results = {}
    for lang in lang_codes:
        results[lang] = {'missing': 0}
    return results


@app.route('/admin/resource')
def resource_list():
    set_menu()
    lang = get_admin_lang()
    permission_content('en')
    resources = Resource.query.filter_by(lang=lang, current=True)
    resources = resources.order_by('name')
    for resource in resources:
        p = Resource.query.filter_by(
            resource_id=resource.resource_id, lang=lang, status='publish'
        ).first()
        resource.has_published = bool(p)
    status = list_status()
    return render_template('admin/resource_list.html', resources=resources, lang=lang,
                           status=status)


def list_status():
    results = {}
    for lang in lang_codes:
        # Unpublished
        unpublished = Resource.query.filter_by(
            lang=lang, current=True
        ).filter(
            Resource.status != 'publish'
        ).count()
        # Missing
        trans = db.session.query(Resource.resource_id).filter_by(lang=lang)
        missing = db.session.query(Resource).filter_by(
            lang='en', current=True
        )
        missing = missing.filter(
            db.not_(Resource.resource_id.in_(trans))
        ).count()
        results[lang] = {'missing': missing, 'unpublished': unpublished}
    return results


@app.route('/resources')
def resource_search():
    lang = request.environ['LANG']
    cats = all_codes(lang, 'res')
    codes_list = cat_codes(lang, 'res')


    resources = Resource.query.filter_by(
        status='publish', active=True
    )

    if not 'all_languages' in request.args:
        resources = resources.filter_by(lang=lang)

    # only show public resources
    if not bool(request.user):
        resources = resources.filter_by(private=False)

    search_codes = set()
    for field, _null in request.args.items():
        if field == 'Filter':
            continue
        search_codes.add(field)

    for codes in codes_list:
        union = set(codes) & search_codes
        if union:
            c = db.session.query(ResourceCodes.resource_id).filter(ResourceCodes.code.in_(list(union)))
            resources = resources.filter(Resource.resource_id.in_(c))

    resources = resources.order_by('name')

    count = resources.count()
    try:
        page = int(request.args.get('page', 0))
    except ValueError:
        page = 0
    pages = page_num(count, config.ORG_PER_PAGE)

    resources = resources.limit(config.ORG_PER_PAGE).offset(page * config.ORG_PER_PAGE)
    resources = resources.all()


    return render_template(
        'resource_search.html', cats=cats, resources=resources, count=count, page=page, pages=pages
    )


def page_num(count, number_per_page):
    if count % number_per_page:
        return (count / number_per_page) + 1
    return count / number_per_page


def get_trans(id):
    results = {}
    rows = db.session.query(Resource.lang, Resource.status).filter_by(
        resource_id=id, current=True
    )
    t = {}
    for row in rows:
        t[row.lang] = row.status
    for lang in lang_codes:
        if lang in t:
            if t[lang] == 'publish':
                results[lang] = {'missing': 0}
            else:
                results[lang] = {'unpublished': 1}
        else:
            results[lang] = {'missing': 1}
    return results


def set_menu():
    request.environ['MENU_PATH'] = url_for_admin('resource_list')[3:]
