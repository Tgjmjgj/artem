import logging
import logging.handlers
import threading
import json
import re
import traceback
import queue
import sys
import types
import time
import os

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from .dialogthread import DialogThread
from .artem_pb2 import ProtoArtem
from .others import *
from .scenario import Scenario, wrapup
from .cmd import Control


VERSION = '1.9.16'
RELEASE = 'Artem3000'

SERIALIZE_FILE = 'dialogs.art'
CHAT_ID_MAX = 10000

if not os.path.exists('log'):
    os.makedirs('log')

ERROR_LOG_FILE = (('log\\' if sys.platform == 'win32' else 'log/') +
                  'artem_' + VERSION + '.log')


class Artem(object):


    def __init__(self, login, password, admins=[], names=[], 
               enabled_session=True, restore=True, twofact_auth=False):

        self._lib = Lib()
        # {some_id: DialogThread}
        self._dialog_threads = {} 
        self._restore = restore
        self._default_enabled_session = enabled_session
        self._admins = admins
        self._secondary_pooling_interval = 10.0
        self._default_session_duration = 30.0
        self._default_discourse_interval_max = 86400
        self._cmd = Control(self)
        
        self._create_logger()
        self._vk_init(login, password, twofact_auth)

        response = self._vk.method('users.get')
        name = response[0]['first_name'].lower()
        if name not in names:
            names.append(name)
        name += ' ' + response[0]['last_name'].lower()
        if name not in names:
            names.append(name)
        self._id = response[0]['id']
        self._names = sorted(names)

    def on(self, event, handler, prior=0):

        try:
            if type(event) != Event:
                event = Event[event]
            if isinstance(handler, types.FunctionType):
                handler = type(
                        'Scenario' + str(id(handler)),
                        (Scenario,),
                        {'respond': wrapup(handler)}
                    )
            self._lib.add(event, handler, prior)
            for id_ in self._dialog_threads:
                (self._dialog_threads[id_].lib.add(
                        event, handler, prior))

        except Exception:
            self._logger.error(traceback.format_exc())

    def _create_logger(self):

        self._logger = logging.getLogger()
        self._logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
                ERROR_LOG_FILE, maxBytes=1048576, backupCount=5)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def _vk_init(self, login, password, twofact_auth):

        try:
            if not twofact_auth:
                self._vk = vk_api.VkApi(login, password)
            else:
                self._vk = vk_api.VkApi(
                        login, password, 
                        auth_handler = lambda: 
                        (input('Enter authentication code: '), True)
                    )
            self._vk.auth()

        except Exception:
            self._logger.error(traceback.format_exc())

    def _get_interlocutors(self, some_id): 

            if some_id < CHAT_ID_MAX:
                response = self._vk.method(
                        'messages.getChat',
                        {'chat_id': some_id, 'fields': 'users'})
                inters = [Interlocutor(
                                user['id'], 
                                user['first_name'], 
                                user['last_name']) 
                            for user in response['users']
                            if user['id'] != self._id
                         ]
            else:
                response = self._vk.method(
                        'users.get', 
                        {'user_ids': some_id})
                inters = [Interlocutor(
                            some_id,
                            response[0]['first_name'],
                            response[0]['last_name']
                         )]
            return inters

    def _create_dialog_thread(
            self, some_id, names, sessions, 
            ses_duration, discourse_max, start=False):

        if some_id not in self._dialog_threads:
            dialog_thread = DialogThread(
                    some_id, self.send_queue, self._lib, 
                    self._get_interlocutors(some_id), self._logger, 
                    names, sessions, ses_duration, discourse_max, start)
            dialog_thread.start()
            self._dialog_threads[some_id] = dialog_thread
            if not start and self._restore:
                self._serialize()

    def _serialize(self):

        try:
            art = ProtoArtem()
            for admin in self._admins:
                art.admins.append(admin)
            art.default_discourse_interval_max = (
                    self._default_discourse_interval_max)
            for name in self._names:
                art.default_names.append(name)
            art.pooling_interval = self._secondary_pooling_interval
            art.default_session_duration = self._default_session_duration
            art.default_sessions = self._default_enabled_session
            for id in self._dialog_threads:
                thr = art.dialog_threads.add()
                thr.some_id = id
                thr.discourse_interval_max = (
                        self._dialog_threads[id].discourse_interval_max)
                for name in self._dialog_threads[id].names:
                    thr.names.append(name)
                thr.session_duration = (
                        self._dialog_threads[id].session_duration)
                thr.sessions = self._dialog_threads[id].enabled_session

            with open(SERIALIZE_FILE, 'wb') as protobuf_file:
                protobuf_file.write(art.SerializeToString())

        except Exception:
            self._logger.error(traceback.format_exc())

    def _deserialize(self):

        try:
            art = ProtoArtem()
            with open(SERIALIZE_FILE, 'rb') as protobuf_file:
                art.ParseFromString(protobuf_file.read())

            self._admins = [admin for admin in art.admins]
            self._default_discourse_interval_max = (
                    art.default_discourse_interval_max)
            self._names = [name for name in art.default_names]
            self._secondary_pooling_interval = art.pooling_interval
            self._default_session_duration = art.default_session_duration
            self._default_enabled_session = art.default_sessions
            for thr in art.dialog_threads:
                self._create_dialog_thread(
                        thr.some_id, [name for name in thr.names],
                        thr.sessions, thr.session_duration,
                        thr.discourse_interval_max, start=True)

        except FileNotFoundError:
            pass
        except Exception:
            self._logger.error(traceback.format_exc())

    def _send_listener(self):

        self.send_queue = queue.Queue()
        while True:
            try:
                answer = self.send_queue.get()
                if answer.id < CHAT_ID_MAX:
                    self._vk.method(
                            'messages.send',
                            {'chat_id': answer.id, 
                            'message': answer.message,
                            'attachment': answer.attach}
                            )
                else:
                    self._vk.method(
                            'messages.send', 
                            {'user_id': answer.id, 
                            'message': answer.message,
                            'attachment': answer.attach}
                            )

            except Exception:
                self._logger.error(traceback.format_exc())

    def _newfriend_pooling(self):

        while True:
            try:
                response = self._vk.method(
                        'friends.getRequests',
                        {'count': 100, 'out': 0,
                        'extended': 1, 'need_viewed': 1}
                        )
                if response['count'] != 0:
                    for item in response['items']:
                        self._vk.method(
                                'friends.add', 
                                {'user_id': item['user_id'], 
                                'follow': 0}
                                )
                        if item['user_id'] not in self._dialog_threads:
                            self._create_dialog_thread(
                                    item['user_id'], self._names, 
                                    self._default_enabled_session,
                                    self._default_session_duration, 
                                    self._default_discourse_interval_max, 
                                    False)
                        (self._dialog_threads[item['user_id']]
                                .queue.put(Envelope(
                                    Event.ADDFRIEND,
                                    item['user_id'], None)
                                ))
                time.sleep(self._secondary_pooling_interval)

            except Exception:
                self._logger.error(traceback.format_exc())

    def alive(self):

        threading.Thread(target=self._send_listener).start()
        threading.Thread(target=self._newfriend_pooling).start()
        if self._restore:
            self._deserialize()

        while True:
            try:
                longpool = VkLongPoll(self._vk)
                for event in longpool.listen():
                    if (event.type == VkEventType.MESSAGE_NEW and
                            not event.from_me):

                        some_id = (event.chat_id if event.from_chat
                                else event.user_id)
                        if some_id not in self._dialog_threads:
                            self._create_dialog_thread(
                                    some_id, self._names,
                                    self._default_enabled_session,
                                    self._default_session_duration,
                                    self._default_discourse_interval_max)

                        if event.text.startswith('/'):
                            self._commands(event.text.lower(), 
                                           event.user_id, some_id)
                        else:
                            (self._dialog_threads[some_id].
                                    queue.put(Envelope(
                                        Event.ANSWER,
                                        event.user_id, event.text.lower())
                                    ))
            except Exception:
                self._logger.error(traceback.format_exc())

    def _commands(self, message, user_id, some_id):
        need_save, answer = self._cmd.execute(message, user_id, some_id)
        if need_save:
            self._serialize()
        self.send_queue.put(ToSend(some_id, answer, None))

