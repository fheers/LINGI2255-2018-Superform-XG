from flask import Blueprint

from superform.models import db, Authorization, Channel

user_page = Blueprint('users', __name__)

def channels_available_for_user(userid):
    chans= []
    auths = db.session.query(Authorization).filter(Authorization.user_id==userid)
    for auth in auths:
        chans.append(db.session.query(Channel).get(auth.channel_id))

    return chans

def get_moderate_channels_for_user(u):
    auth = Authorization.query.filter(Authorization.user_id == u.id, Authorization.permission == 2)
    chan = [Channel.query.get(a.channel_id) for a in auth]
    return chan

def is_moderator(user):
    auth = Authorization.query.filter(Authorization.user_id == user.id, Authorization.permission == 2)
    return auth.count() > 0
