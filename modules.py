# -*- coding: UTF-8 -*-
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zxyx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = u'my_secret_key'
# app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)
db.init_app(app)


class System(db.Model):
    __tablename__ = 'system'

    inventory = db.Column(db.String(20), primary_key=True)
    hostname = db.Column(db.String(20), nullable=None)
    os_info = db.Column(db.String(20))
    platform = db.Column(db.String(20), nullable=True)
    cpu_num = db.Column(db.Integer)
    memory = db.Column(db.Integer)

    def __repr__(self):
        return "inventory=%s, hostname=%s, os_info=%s, platform=%s, cpu_num=%s, memory=%s" % (self.inventory, \
                    self.hostname, self.os_info, self.platform, self.cpu_num, self.memory)


class WebSphere(db.Model):
    __tablename__ = 'websphere'

    was_info_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    max_mem = db.Column(db.Integer)
    curr_mem = db.Column(db.Float)
    prf_name = db.Column(db.String(100))
    srv_name = db.Column(db.String(20))
    sys_inventory = db.Column(db.String(50), ForeignKey('system.inventory'))

    def __init__(self, max_mem, curr_mem, prf_name, srv_name, sys_inventory):
        self.max_mem = max_mem
        self.curr_mem = curr_mem
        self.prf_name = prf_name
        self.srv_name = srv_name
        self.sys_inventory = sys_inventory

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'was_info_id': self.was_info_id,
            'prf_name': self.prf_name,
            'srv_name': self.srv_name,
            'max_mem': self.max_mem,
            'curr_mem': self.curr_mem,
            'sys_inventory': self.sys_inventory
        }

    def __repr__(self):
        return "sys_inventory=%s, was_info_id=%s, prf_name=%s, srv_name=%s, max_mem=%s, curr_mem=%s" % ( \
            self.sys_inventory, self.was_info_id, self.prf_name, self.srv_name, self.max_mem, self.curr_mem)


class DB2(db.Model):
    __tablename__ = 'db2'

    db2_info_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    sys_inventory = db.Column(db.String(20), ForeignKey('system.inventory'))
    inst_name = db.Column(db.String(20), nullable=False)
    db_name = db.Column(db.String(20), nullable=False)
    listen_port = db.Column(db.Integer, nullable=False)

    @property
    def serialize(self):
        return {
            'db2_info_id': self.db2_info_id,
            'sys_inventory': self.sys_inventory,
            'inst_name': self.inst_name,
            'db_name': self.db_name,
            'listen_port': self.listen_port
        }

    def __repr__(self):
        return "sys_inventory=%s, db2_info_id=%s, inst_name=%s, db_name=%s, listen_port=%s" % ( \
            self.sys_inventory, self.db2_info_id, self.inst_name, self.db_name, self.listen_port)


if __name__ == '__main__':
    db.create_all()
