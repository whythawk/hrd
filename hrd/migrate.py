from hrd import db


sql = '''
ALTER TABLE organisation
    ADD private BOOLEAN
'''

try:
    db.engine.execute(sql)
except:
    pass


sql = '''
ALTER TABLE cms
    ADD private BOOLEAN
 '''

try:
    db.engine.execute(sql)
except:
    pass


sql = '''
CREATE TABLE translation (
    id VARCHAR(250) NOT NULL,
    plural VARCHAR(250),
    lang VARCHAR(2) NOT NULL,
    active BOOLEAN,
    trans1 VARCHAR(250),
    trans2 VARCHAR(250),
    trans3 VARCHAR(250),
    trans4 VARCHAR(250),
    PRIMARY KEY (id, plural, lang)
);
'''

try:
    db.engine.execute(sql)
except:
    pass
