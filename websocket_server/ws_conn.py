from app import db
from app.model import Users, UserToken
from app.controller.global_config import GlobalConfig
from app.utils import PRIVILEGES
from app.tools.mq_proxy import WS_TAG, MessageQueueProxy

from tornado import websocket
from tornado.ioloop import IOLoop
from . import logger
import socketio, eventlet, json, re, threading, traceback

class WSConnections():
    instance = None

    @staticmethod
    def getInstance():
        if WSConnections.instance == None:
           WSConnections.instance = WSConnections()
        return WSConnections.instance

    def __init__(self):
        self.connections = {}

class WebSocketHandler(websocket.WebSocketHandler):

    def __init__(self, app, request):
        websocket.WebSocketHandler.__init__(self, app, request)
        # KEY :  <user_key> = user_{%uid}
        # VALUE : [<client1>, <client2>, ...]
        self.connections = WSConnections.getInstance().connections

    def _check_user(self, token):

        if token == None:
            return (None, None)

        user = db.session.query(UserToken).join(Users).filter(UserToken.token == token).first()
        if user is None:
            return (None, None)
        else:
            priv = user.ob_user.privilege
            uid = user.uid

            return (priv, uid)

    def open(self):
        priv, uid = self._check_user(self.get_cookie("session_token"))

        # socket is invalid
        if priv == None:
            self.close(reason="privilege invalid!")
        else:
            user_key = "user_%s" % uid
            if self.connections.get(user_key) == None:
                self.connections[user_key] = []

            if self not in self.connections.get(user_key):
                self.connections[user_key].append(self)

    def on_close(self):
        for user_key in self.connections:
            if self in self.connections.get(user_key):
                self.connections.get(user_key).remove(self)

    def on_message(self, data):
        _event = data.get("event")
        _props = data.get("props")

        # only root user could operate it
        # TODO extend priv range
        avail = self.client_available(self, permission=PRIVILEGES.ROOT_USER)

        if avail == True:
            logger.debug("send <-- event = %s, props = %s" % (_event, _props))
        else:
            logger.debug("reject <-- event = %s, props = %s" % (_event, _props))

    def client_available(self, client, permission = None):
        if permission == None:
            return True
        else:
            _uid = None
            _priv = None
            for user_key in self.connections:
                if client in self.connections.get(user_key):
                    _uid = user_key[5:]
                    break
            if _uid == None:
                return False
            else:
                user_obj = db.session.query(Users).filter(Users.id == int(_uid)).first()
                if user_obj == None:
                    return False
                else:
                    _priv = user_obj.privilege

            if _priv > permission:
                return False
            else:
                return True

def send_data(event, data, uid):
    '''
    send websocket data to all sessions that belongs to the user
    '''
    def _send_data_callback(clients):
        data_str = json.dumps(data)
        for client in clients:
            client.write_message(data_str)

    if uid == None:
        return None

    user_key = "user_%s" % uid
    clients = WSConnections.getInstance().connections

    sessions = clients.get(user_key)

    if sessions != None:
        logger.debug("send[B] <-- uid = %s, content = %s" % (uid, data))

        io_loop = IOLoop.current()
        if io_loop != None:
            io_loop.add_callback(_send_data_callback, sessions)
