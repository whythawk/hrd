from hrd import db


sql = '''
ALTER TABLE organisation
    ADD private BOOLEAN;
'''

try:
    db.engine.execute(sql)
except:
    pass


sql = '''
ALTER TABLE cms
    ADD private BOOLEAN;
'''

try:
    db.engine.execute(sql)
except:
    pass


sql = '''
CREATE TABLE translation (
    id INTEGER NOT NULL,
    string VARCHAR(250),
    plural VARCHAR(250),
    lang VARCHAR(2) NOT NULL,
    active BOOLEAN,
    trans0 VARCHAR(250),
    trans1 VARCHAR(250),
    trans2 VARCHAR(250),
    trans3 VARCHAR(250),
    trans4 VARCHAR(250),
    trans5 VARCHAR(250),
    PRIMARY KEY (id)
);
'''

try:
    db.engine.execute(sql)
except:
    pass


sql = '''
ALTER TABLE users
    ADD ga_enabled BOOLEAN NOT NULL DEFAULT True,
    ADD ga_key VARCHAR(50),
    ADD reset_code VARCHAR(50),
    ADD reset_date TIMESTAMP;
'''

try:
    db.engine.execute(sql)
except:
    pass

sql = '''
ALTER TABLE users
    ADD organization VARCHAR(50);
'''

try:
    db.engine.execute(sql)
except:
    pass

sql = '''
ALTER TABLE users
    ADD realname VARCHAR(250),
    ADD position VARCHAR(250);
'''

try:
    db.engine.execute(sql)
except:
    pass
