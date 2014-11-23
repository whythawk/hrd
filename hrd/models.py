from hrd import db
import uuid


def make_uuid():
    return unicode(uuid.uuid4())


class Cms(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    page_id = db.Column(db.String(50), default=make_uuid)
    url = db.Column(db.String(250))
    title = db.Column(db.String(250))
    content = db.Column(db.Text())
    lang = db.Column(db.String(2), primary_key=True)
    status = db.Column(db.String(10))
    current = db.Column(db.Boolean(), default=True)
    published = db.Column(db.Boolean(), default=False)
    active = db.Column(db.Boolean(), default=True)
    needs_trans = db.Column(db.Boolean(), default=False)
    image = db.Column(db.String(250))

    def __repr__(self):
        return "<Cms %s>" % self.title


class Code(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    code_id = db.Column(db.String(50), default=make_uuid)
    category_id = db.Column(db.String(50))
    title = db.Column(db.String(250))
    description = db.Column(db.Text())
    lang = db.Column(db.String(2), primary_key=True)
    status = db.Column(db.String(10))
    current = db.Column(db.Boolean(), default=True)
    active = db.Column(db.Boolean(), default=True)
    public = db.Column(db.Boolean(), default=True)
    order = db.Column(db.Integer(), default=99)

    def __repr__(self):
        return "<Code %s>" % self.title


class Category(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    category_id = db.Column(db.String(50), default=make_uuid)
    title = db.Column(db.String(250))
    description = db.Column(db.Text())
    lang = db.Column(db.String(2), primary_key=True)
    status = db.Column(db.String(10))
    cat_type = db.Column(db.String(10))
    current = db.Column(db.Boolean(), default=True)
    active = db.Column(db.Boolean(), default=True)
    order = db.Column(db.Integer(), default=99)

    def __repr__(self):
        return "<Category %s>" % self.title


class Organisation(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    org_id = db.Column(db.String(50), default=make_uuid)
    lang = db.Column(db.String(2), primary_key=True)
    status = db.Column(db.String(10))
    current = db.Column(db.Boolean(), default=True)
    active = db.Column(db.Boolean(), default=True)
    private = db.Column(db.Boolean(), default=True)
    name = db.Column(db.String(250))
    description = db.Column(db.Text())
    address = db.Column(db.String(250))
    contact = db.Column(db.String(250))
    phone = db.Column(db.String(250))
    email = db.Column(db.String(250))
    pgp_key = db.Column(db.String(250))
    website = db.Column(db.String(250))
    published = db.Column(db.Boolean(), default=False)
    image = db.Column(db.String(50))
    needs_trans = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return "<Organisation %s>" % self.name


class OrgCodes(db.Model):
    org_id = db.Column(db.String(50), primary_key=True)
    code = db.Column(db.String(50), primary_key=True)

    def __repr__(self):
        return "<OrgCode %s %s>" % (self.org_id, self.code)


class User(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    name = db.Column(db.String(250))
    password = db.Column(db.String(250))
    active = db.Column(db.Boolean(), default=True)

    def __repr__(self):
        return "<User %s>" % self.name


class UserPerms(db.Model):
    user_id = db.Column(db.String(50), primary_key=True)
    permission = db.Column(db.String(50), primary_key=True)

    def __repr__(self):
        return "<UserPerm %s %s>" % (self.user_id, self.permission)


db.create_all()
