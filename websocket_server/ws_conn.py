from app import db
from app.model import Users, UserToken
from app.controller.global_config import GlobalConfig
from app.utils import PRIVILEGES
from app.tools.mq_proxy import WS_TAG, MessageQueueProxy

from tornado import websocket
from . import logger
import socketio, eventlet, json, re, threading, traceback

class WebSocketHandler(websocket.WebSocketHandler):

    instance = None

    @staticmethod
    def getInstance():
        if WebSocketHandler.instance == None:
           WebSocketHandler.instance = WebSocketHandler()
        return WebSocketHandler.instance

    def __init__(self):
        # KEY :  <user_key> = user_{%uid}
        # VALUE : [<client1>, <client2>, ...]
        self.connections = {}

    def _check_user(self, environment):

        def _construct_cookie(headers_raw):
            '''
            format: ((<key>,<value>), .. )
            For cookies:
            ('Cookie', 'A=B; C=D')
            :param headers_raw:
            :return:
            '''
            cookies = {}
            _re = "^(.+)=(.+)"
            for x in range(0, len(headers_raw)):
                _key , _val = headers_raw[x]

                if _key.lower() == "cookie":
                    _cookie_str = _val
                    _cookie_str_arr = _cookie_str.split(" ")
                    for _cookie_item in _cookie_str_arr:
                        r = re.search(_re, _cookie_item)
                        if r != None:
                            cookies[r.group(1)] = r.group(2)
                    break
            return cookies

        # after  initialization
        cookies = _construct_cookie(environment["headers_raw"])
        _token = cookies.get("session_token")

        if _token == None:
            return (None, None)

        user = db.session.query(UserToken).join(Users).filter(UserToken.token == _token).first()
        if user is None:
            return (None, None)
        else:
            priv = user.ob_user.privilege
            uid = user.uid

            return (priv, uid)

    def open(self):
        print(self.get_cookie("session_token"))
#        priv, uid = self._check_user(environment)
        priv = None
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
        avail = self.sid_available(self, permission=PRIVILEGES.ROOT_USER)

        if avail == True:
            logger.debug("send <-- event = %s, props = %s" % (_event, _props))
        else:
            logger.debug("reject <-- event = %s, props = %s" % (_event, _props))

    def sid_available(self, sid, permission = None):
        if permission == None:
            return True
        else:
            _uid = None
            _priv = None
            for user_key in self.connections:
                if sid in self.connections.get(user_key):
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

    def find_uid(self, sid):
        _uid = None
        for user_key in self.connections:
            if sid in self.connections.get(user_key):
                _uid = user_key[5:]
                break
        return _uid

    def send_data(self, event, data, uid = None, sid = None):
        '''
        send websocket data to all session that belongs to the user
        '''
        if sid != None:
            logger.debug("send <-- sid = %s, content = %s" % (sid[0:6], data))
            self.sio.emit(event, data, room=sid, namespace="/")
        elif uid == None:
            return None
        else:
            user_key = "user_%s" % uid
            sessions = self.connections.get(user_key)
            if sessions != None:
                logger.debug("send[B] <-- uid = %s, content = %s" % (uid, data))
                for sid in sessions:
                    self.sio.emit(event, data, room=sid, namespace="/")
