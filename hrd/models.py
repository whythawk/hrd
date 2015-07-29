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
    private = db.Column(db.Boolean(), default=True)
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
    active = db.Column(db.Boolean(), default=False)
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
    active = db.Column(db.Boolean(), default=False)
    order = db.Column(db.Integer(), default=99)

    def __repr__(self):
        return "<Category %s>" % self.title


class MenuItem(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    menu_id = db.Column(db.String(50), default=make_uuid)
    parent_menu_id = db.Column(db.String(50))
    title = db.Column(db.String(250))
    item = db.Column(db.String(250))
    lang = db.Column(db.String(2), primary_key=True)
    active = db.Column(db.Boolean(), default=False)
    private = db.Column(db.Boolean(), default=False)
    order = db.Column(db.Integer(), default=99)

    def __repr__(self):
        return "<MenuItem %s>" % self.title


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


class Resource(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    resource_id = db.Column(db.String(50), default=make_uuid)
    lang = db.Column(db.String(2), primary_key=True)
    status = db.Column(db.String(10))
    current = db.Column(db.Boolean(), default=True)
    active = db.Column(db.Boolean(), default=True)
    private = db.Column(db.Boolean(), default=True)
    name = db.Column(db.String(250))
    description = db.Column(db.Text())
    published = db.Column(db.Boolean(), default=False)
    url = db.Column(db.String(1024))
    file = db.Column(db.String(50))
    filename = db.Column(db.String(250))
    file_type = db.Column(db.String(250))
    file_size = db.Column(db.Integer())
    mime_type = db.Column(db.String(250))
    mime_encoding = db.Column(db.String(250))

class ResourceCodes(db.Model):
    resource_id = db.Column(db.String(50), primary_key=True)
    code = db.Column(db.String(50), primary_key=True)

    def __repr__(self):
        return "<ResourseCode %s %s>" % (self.resource_id, self.code)


from flaskbb.user.models import User, Guest


User.organization = db.Column(db.String(50))
User.realname = db.Column(db.String(250))
User.position = db.Column(db.String(250))
#class User(db.Model):
#    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
#    name = db.Column(db.String(250))
#    password = db.Column(db.String(250))
#    active = db.Column(db.Boolean(), default=True)



class UserPerms(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    permission = db.Column(db.String(50), primary_key=True)

    def __repr__(self):
        return "<UserPermBB %s %s>" % (self.user_id, self.permission)


class Translation(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    string = db.Column(db.String(250))
    plural = db.Column(db.String(250))
    lang = db.Column(db.String(2))
    active = db.Column(db.Boolean(), default=True)
    plural = db.Column(db.String(250))
    trans0 = db.Column(db.String(250))
    trans1 = db.Column(db.String(250))
    trans2 = db.Column(db.String(250))
    trans3 = db.Column(db.String(250))
    trans4 = db.Column(db.String(250))
    trans5 = db.Column(db.String(250))

    def __repr__(self):
        return "<Translation %s %s>" % (self.id, self.lang)

class News(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=make_uuid)
    lang = db.Column(db.String(2), primary_key=True)
    active = db.Column(db.Boolean(), default=True)
    title = db.Column(db.String(250))
    description = db.Column(db.Text())
    last_updated = db.Column(db.Date())
    file = db.Column(db.String(50))
    filename = db.Column(db.String(250))
    file_type = db.Column(db.String(250))
    file_size = db.Column(db.Integer())
    mime_type = db.Column(db.String(250))
    mime_encoding = db.Column(db.String(250))

db.create_all()
