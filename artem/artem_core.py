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
from .cmd import *

VERSION = '1.9.16'
RELEASE = 'Artem3000'

SERIALIZE_FILE = 'dialogs.art'
CHAT_ID_MAX = 10000
DEFAULT_POOLING_INTERVAL = 10.0

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
        self._global_admins = admins
        self._secondary_pooling_interval = Wrap()
        self._secondary_pooling_interval.val = DEFAULT_POOLING_INTERVAL
        self._send_queue = queue.Queue()
        
        self._create_logger()
        self._vk_init(login, password, twofact_auth)
        self._control_init()

        response = self._vk.method('users.get')
        name = response[0]['first_name'].lower()
        if name not in names:
            names.append(name)
        name += ' ' + response[0]['last_name'].lower()
        if name not in names:
            names.append(name)
        self._id = response[0]['id']
        self._global_names = sorted(names)

    def on(self, event, handler, prior=0):

        try:
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

    def _create_dialog_thread(self, some_id, start=False):

        if some_id not in self._dialog_threads:
            dialog_thread = DialogThread(
                    some_id, self._send_queue, self._lib,
                    self._get_interlocutors(some_id), self._logger,
                    start, self._global_names, self._global_admins
                )
            dialog_thread.start()
            self._dialog_threads[some_id] = dialog_thread
            if not start and self._restore:
                self._serialize()

    def _serialize(self):
        try:
            art = ProtoArtem()
            for admin in self._global_admins:
                art.global_admins.append(admin)
            for name in self._global_names:
                art.global_names.append(name)
            art.pooling_interval = self._secondary_pooling_interval.val
            for id_ in self._dialog_threads:
                thr = art.dialog_threads.add()
                thr.some_id = id_
                thr.discourse_interval_max = (
                        self._dialog_threads[id_].discourse_interval_max.val)
                thr.session_duration = (
                        self._dialog_threads[id_].session_duration.val)
                thr.sessions = self._dialog_threads[id_].enabled_session.val
                for name in self._dialog_threads[id_].local_names:
                    thr.names.append(name)
                for admin in self._dialog_threads[id_].local_admins:
                    thr.names.append(admin)

            with open(SERIALIZE_FILE, 'wb') as protobuf_file:
                protobuf_file.write(art.SerializeToString())

        except Exception:
            self._logger.error(traceback.format_exc())

    def _deserialize(self):
        try:
            art = ProtoArtem()
            with open(SERIALIZE_FILE, 'rb') as protobuf_file:
                art.ParseFromString(protobuf_file.read())

            self._global_admins = [admin for admin in art.global_admins]
            self._global_names = [name for name in art.global_names]
            self._secondary_pooling_interval.val = art.pooling_interval
            for thr in art.dialog_threads:
                self._create_dialog_thread(thr.some_id, start=True)
                self._dialog_threads[thr.some_id].restore(
                        thr.sessions, thr.session_duration,
                        thr.discourse_interval_max,
                        [name for name in thr.names], 
                        [admin for admin in thr.admins]
                    )
        except FileNotFoundError:
            pass
        except Exception:
            self._logger.error(traceback.format_exc())

    def _send_listener(self):
        while True:
            try:
                answer = self._send_queue.get()
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
                            self._create_dialog_thread(item['user_id'])
                        (self._dialog_threads[item['user_id']]
                                .queue.put(Envelope(
                                    Event.ADDFRIEND,
                                    item['user_id'], None)
                                ))
                time.sleep(self._secondary_pooling_interval.val)

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
                            self._create_dialog_thread(some_id)

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
        if user_id in self._global_admins:
            admin = AdminClass.GLOBAL
        elif user_id in self._dialog_threads[some_id].local_admins:
            admin = AdminClass.LOCAL
        else:
            admin = AdminClass.NONE
        answer, need_save = self._cmd.execute(message, some_id, admin)
        if need_save:
            self._serialize()
        self._send_queue.put(ToSend(some_id, answer, None))

    def _control_init(self):
        self._cmd = Control()
        self._cmd.add('version', 'Information about Artem version'
            ).action(
                CommandType.INFO, 
                AdminClass.NONE, 
                [],
                lambda some_id:
                    'ArtemCore v' + VERSION + '\nRelease: ' + RELEASE
            )
        self._cmd.add('scenario', 'Enable or disable a specific scenario'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.FUNC_ARG],
                 [ArgType.WORD, ArgRole.FUNC_ARG]],
                lambda some_id, *args: 
                    ('Local scenario status: ' + 
                    ('ON' if self._dialog_threads[some_id].lib.get_status(args[0], args[1])
                          else 'OFF'))
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.FUNC_ARG],
                 [ArgType.WORD, ArgRole.FUNC_ARG]],
                lambda *args:
                    ('Global scenario status: ' + 
                    ('ON' if self._lib.get_status(args[0], args[1]) else 'OFF')),
                glob=True
            ).action(
                CommandType.ON_OFF,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.ARG],
                 [ArgType.WORD, ArgRole.ARG],
                 [ArgType.ON_OFF, ArgRole.ARG]],
                lambda some_id:
                    self._dialog_threads[some_id].lib.set_status
            ).action(
                CommandType.ON_OFF,
                AdminClass.GLOBAL,
                [[ArgType.WORD, ArgRole.ARG],
                 [ArgType.WORD, ArgRole.ARG],
                 [ArgType.ON_OFF, ArgRole.ARG]],
                lambda:
                    self._lib.set_status,
                glob=True
            )
        self._cmd.add('pooling_interval',
            'Get or set time between secondary pooling (all except messages)'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Secondary pooling interval = ' +
                        str(self._secondary_pooling_interval.val) + ' sec')
            ).action(
                CommandType.SET,
                AdminClass.GLOBAL,
                [[ArgType.FLOAT, ArgRole.VALUE]],
                lambda some_id:
                    self._secondary_pooling_interval
            )
        self._cmd.add('admins',
            'Information and administration of a group of admins'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Local admins: ' + ', '.join(
                        [str(a) for a in self._dialog_threads[some_id].local_admins]))
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda:
                    ('Global admins: ' + ', '.join(
                        [str(a) for a in self._global_admins])),
                glob=True
            ).action(
                CommandType.ADD_DEL,
                AdminClass.LOCAL,
                [[ArgType.INTEGER, ArgRole.APPEND]],
                lambda some_id:
                    self._dialog_threads[some_id].local_admins
            ).action(
                CommandType.ADD_DEL,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.APPEND]],
                lambda:
                    self._global_admins,
                glob=True
            )
        self._cmd.add('names',
            'Information and administration of Artem respond names'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Artem local names: ' + ', '.join(
                        [str(a) for a in self._dialog_threads[some_id].local_names]))
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda:
                    ('Artem global names: ' + ', '.join(
                        [str(a) for a in self._global_names])),
                glob=True
            ).action(
                CommandType.ADD_DEL,
                AdminClass.LOCAL,
                [[ArgType.STRING, ArgRole.APPEND]],
                lambda some_id:
                    self._dialog_threads[some_id].local_names
            ).action(
                CommandType.ADD_DEL,
                AdminClass.GLOBAL,
                [[ArgType.STRING, ArgRole.APPEND]],
                lambda:
                    self._global_names,
                glob=True
            )
        self._cmd.add('sessions', 'Enabled or disabled sessions'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    'Sessions ' + ('enabled'
                        if self._dialog_threads[some_id].enabled_session.val
                        else 'disabled') +' in local chat'
            ).action(
                CommandType.ON_OFF,
                AdminClass.LOCAL,
                [[ArgType.ON_OFF, ArgRole.VALUE]],
                lambda some_id:
                    self._dialog_threads[some_id].enabled_session
            )
        self._cmd.add('session_duration', 'Get or set duration of session'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Session duration = ' +
                        str(self._dialog_threads[some_id].session_duration.val) + ' sec')
            ).action(
                CommandType.SET,
                AdminClass.GLOBAL,
                [[ArgType.FLOAT, ArgRole.VALUE]],
                lambda some_id:
                    self._dialog_threads[some_id].session_duration
            )
        self._cmd.add('discourse_interval',
            'Get or set maximal time between two discourse'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Max discourse interval = ' +
                        str(self._dialog_threads[some_id].discourse_interval_max.val) + ' sec')
            ).action(
                CommandType.SET,
                AdminClass.GLOBAL,
                [[ArgType.FLOAT, ArgRole.VALUE]],
                lambda some_id:
                    self._dialog_threads[some_id].discourse_interval_max
            )
        self._cmd.add('events',
            'Get information about event types and their scenarios'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [],
                lambda some_id:
                    ', '.join([(e.name + ': ' + str(len(self._lib[e])))
                            for e in Event])
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    args[0].upper() + ' scenarios:\n' +
                        '\n'.join(p.scn_type.__name__
                                  for p in self._lib[args[0]])
            )
        self._cmd.add('dialogs',
            'Provide information about artem\'s dialogs'
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [],
                lambda some_id:
                    'Chats with Artem: ' + ', '.join(
                        str(id_) for id_ in self._dialog_threads)
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    ('Dialog ' + str(args[0]) + ' interlocutors:\n' +
                        '\n'.join(
                            (str(i.id) + ' - ' + i.first_name + ' ' + i.last_name)
                            for i in self._dialog_threads[args[0]].interlocutors
                        )
                    )
            )
        self._cmd.add('id', 'Get id of current Artem account'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [],
                lambda some_id:
                    'ID of current Artem:  ' + str(self._id)
            )
        self._cmd.add('sendto', 'Forcing a message to the specified id'
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.FUNC_ARG],
                 [ArgType.MESSAGE, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    self._send_queue.put(ToSend(
                        args[0], args[1][0].upper() + args[1][1:], None))
            )

        
