from passlib.hash import sha512_crypt as passlib
from flask import render_template, request, abort, redirect, session


from hrd import (app, db, url_for_admin, get_str, url_for,
                 get_bool, permission_list)
from hrd.models import User, UserPerms


@app.before_request
def before_request():
    user_id = session.get('user')
    request.user = None
    request.permissions = []
    if user_id:
        user = User.query.filter_by(id=user_id, active=True).first()
        if user:
            request.user = user
            request.permissions = [
                p.permission
                for p in UserPerms.query.filter_by(user_id=user_id).all()
            ]


def password_verify(password, p_hash):
    return passlib.verify(password, p_hash)


def password_encrypt(value):
    return passlib.encrypt(value)


@app.route('/login', methods=['GET', 'POST'])
def login():
    username = ''
    if request.method == 'POST':
        username = get_str('name')
        password = get_str('password')
        if username and password:
            user = User.query.filter_by(name=username).first()
            if user and password_verify(password, user.password):
                session['user'] = user.id
                return redirect(url_for('index'))

    return render_template('user/login.html', username=username)


@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('user', None)
    session.clear()
    return redirect(url_for('index'))


@app.route('/user/edit/<id>', methods=['GET', 'POST'])
def user_edit(id):
    user = User.query.filter_by(id=id).first()
    perms = permission_list
    if not user:
        abort(404)
    if request.method == 'POST':
        user.name = get_str('name')
        db.session.add(user)
        # permissions
        p_in = []
        p_out = []
        for perm, rest in perms:
            if get_bool(perm):
                p_in.append(perm)
            else:
                p_out.append(perm)
        current = [
            p.permission for p in UserPerms.query.filter_by(user_id=id).all()
        ]
        for perm in p_in:
            if perm not in current:
                perm = UserPerms(user_id=id, permission=perm)
                db.session.add(perm)
        for perm in p_out:
            UserPerms.query.filter_by(user_id=id, permission=perm).delete()

        db.session.commit()
        return redirect(url_for_admin('user_edit', id=id))

    user_perms = [
        p.permission for p in UserPerms.query.filter_by(user_id=id).all()
    ]
    return render_template('user/edit.html', user=user, perms=perms,
                           user_perms=user_perms)


def autocreate_admin():
    admin = User.query.filter_by().first()
    if not admin:
        user = User(
            name='admin',
            password=password_encrypt('admin'),
        )
        db.session.add(user)
        db.session.commit()
        perm = UserPerms(user_id=user.id, permission='sys_admin')
        db.session.add(perm)
        db.session.commit()


autocreate_admin()
