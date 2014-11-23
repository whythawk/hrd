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
