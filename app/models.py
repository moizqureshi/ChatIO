from app import db
from sqlalchemy.inspection import inspect

class Serializer(object):

    def serialize(self):
        return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

    @staticmethod
    def serialize_list(l):
        return [m.serialize() for m in l]

class User(db.Model, Serializer):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), index=True, nullable=False)
    username = db.Column(db.String(25), index=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    pic_path = db.Column(db.String(150), nullable=True)

    def __init__(self, email, username, password, pic_path):
        self.email = email
        self.username = username
        self.password = password
        self.pic_path = pic_path

class Message(db.Model, Serializer):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    messageTxt = db.Column(db.Text, nullable=False)
    dateTime = db.Column(db.DateTime, index=True, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, messageTxt, dateTime, sender_id):
        self.messageTxt = messageTxt
        self.dateTime = dateTime
        self.sender_id = sender_id
