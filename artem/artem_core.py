import threading
import datetime
import json
import re
import traceback
import queue
import types
import time
import random
from functools import reduce

import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from .dialogthread import DialogThread
from .artem_pb2 import ProtoArtem
from .others import *
from .scenario import Scenario, wrap_respond, wrap_suitable
from .commands import *
from .lib import Lib
from .time_parser import *
from .Event import Event
from .ArtemLogger import ArtemLogger



class Artem(object):

    def __init__(self, login, password, admins=[], names=[], 
               enabled_session=True, restore=True, twofact_auth=False):

        self._lib = Lib()
        # {some_id: [DialogThread, status(True/False)]}
        self._dialog_threads = {}
        self._restore = restore
        self._global_admins = admins
        self._secondary_polling_interval = Wrap(DEFAULT_POLLING_INTERVAL)
        self._send_queue = queue.Queue()
        self._run = True
        
        self._logger = ArtemLogger()
        self._vk_init(login, password, twofact_auth)
        self._cmd = Commands(self)

        response = self._vk.method('users.get')
        name = response[0]['first_name'].lower()
        if name not in names:
            names.append(name)
        name += ' ' + response[0]['last_name'].lower()
        if name not in names:
            names.append(name)
        self._id = response[0]['id']
        self._global_names = sorted(names)

    def on(self, event, scen=None, prior=0, handler=None, suitable=None):
        try:
            scen = make_scen(scen, handler, suitable)
            self._lib.add_event(event, scen, prior)
            for s_id in self._dialog_threads:
                self._dialog_threads[s_id].lib.add_event(event, scen, prior)
            return scen
        except Exception:
            self._logger.log(traceback.format_exc())

    def ontime(self, time_event, first_time, second_time=None, rand_shift=0,
        static_time=True, scen=None, handler=None, suitable=None):
        try:
            scen = make_scen(scen, handler, suitable)
            if time_event == Event.IDLE or time_event == Event.SILENCE:
                time_delta = parse_timedelta(first_time)
                self._lib.add_event(event, scen, time_delta=time_delta, rand_shift=rand_shift)
                for s_id in self._dialog_threads:
                    self._dialog_threads[s_id].lib.add_event(event, scen,
                        time_delta=time_delta, rand_shift=rand_shift)
            elif time_event == Event.TIME:
                first_time = parse_time(first_time)
                second_time = parse_time(second_time)
                self._lib.add_event(event, scen,
                    time1=first_time, time2=second_time,
                    rand_shift=rand_shift, static_time=static_time)
                for s_id in self._dialog_threads:
                    self._dialog_threads[s_id].lib.add_event(event, scen,
                        time1=first_time, time2=second_time,
                        rand_shift=rand_shift, static_time=static_time)
            return scen
        except Exception:
            self._logger.log(traceback.format_exc())

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
            self._logger.log(traceback.format_exc())

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
                    {'user_ids': some_id}
                )
            inters = [Interlocutor(
                        some_id,
                        response[0]['first_name'],
                        response[0]['last_name']
                        )]
        return inters

    def _create_dialog_thread(self, some_id,
        enable_ses=DEFAULT_ENABLED_SESSION,
        session_dur=DEFAULT_SESSION_DURATION,
        discourse_max=DEFAULT_DISCOURSE_INTERVAL_MAX,
        names=self._global_names,
        admins=self._global_admins):

        if some_id not in self._dialog_threads.index():
            dialog_thread = DialogThread(
                some_id,
                self._send_queue,
                self._lib,
                self._get_interlocutors(some_id),
                self._logger,
                names,
                admins,
                enable_ses,
                session_dur,
                discourse_max
            )
            dialog_thread.start()
            self._dialog_threads[some_id] = dialog_thread
            if self._restore:
                self._serialize()

    def _serialize(self):
        try:
            art = ProtoArtem()
            for admin in self._global_admins:
                art.global_admins.append(admin)
            for name in self._global_names:
                art.global_names.append(name)
            art.polling_interval = self._secondary_polling_interval.val
            for sid in self._dialog_threads:
                thr = art.dialog_threads.add()
                thr.some_id = sid
                thr.discourse_interval_max = self._dialog_threads[sid].discourse_interval_max.val
                thr.session_duration = self._dialog_threads[sid].session_duration.val
                thr.sessions = self._dialog_threads[sid].enabled_session.val
                for name in self._dialog_threads[sid].local_names:
                    thr.names.append(name)
                for admin in self._dialog_threads[sid].local_admins:
                    thr.names.append(admin)

            with open(SERIALIZE_FILE, 'wb') as protobuf_file:
                protobuf_file.write(art.SerializeToString())

        except Exception:
            self._logger.log(traceback.format_exc())

    def _deserialize(self):
        try:
            art = ProtoArtem()
            with open(SERIALIZE_FILE, 'rb') as protobuf_file:
                art.ParseFromString(protobuf_file.read())

            self._global_admins = [admin for admin in art.global_admins]
            self._global_names = [name for name in art.global_names]
            self._secondary_polling_interval.val = art.polling_interval
            for thr in art.dialog_threads:
                self._create_dialog_thread(
                    thr.some_id,
                    thr.sessions,
                    thr.session_duration,
                    thr.discourse_interval_max,
                    [name for name in thr.names], 
                    [admin for admin in thr.admins]
                )
        except FileNotFoundError:
            pass
        except Exception:
            self._logger.log(traceback.format_exc())

    def _send_listener(self):
        upload = vk_api.VkUpload(self._vk)
        session = requests.Session()
        try:
            while True:
                answer = self._send_queue.get()
                if answer.attach:
                    if answer.attach.startswith('http'):
                        image = session.get(answer.attach, stream=True)
                        photo = upload.photo_messages(photos=image.raw)[0]
                        answer.attach = 'photo{}_{}'.format(
                            photo['owner_id'], photo['id']
                            )
                        answer.sleep = 0.0
                whose_id = 'chat_id' if answer.id < CHAT_ID_MAX else 'user_id'
                time.sleep(answer.sleep)
                self._vk.method(
                        'messages.send',
                        {
                            whose_id: answer.id, 
                            'message': answer.message,
                            'random_id': random.getrandbits(32),
                            'attachment': answer.attach,
                            'sticker_id': answer.sticker
                        }
                    )
        except Exception:
            self._logger.log(traceback.format_exc())

    def _newfriend_polling(self):
        try:
            while True:
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
                                item['user_id'],
                                None
                            ))
                        )
                time.sleep(self._secondary_polling_interval.val)
        except Exception:
            self._logger.log(traceback.format_exc())

    def alive(self):

        threading.Thread(target=self._send_listener).start()
        threading.Thread(target=self._newfriend_polling).start()
        if self._restore:
            self._deserialize()
        for thr in self._dialog_threads.values:
            thr.queue.put(Envelope(Event.START, None, None))
        while True:
            try:
                longpoll = VkLongPoll(self._vk)
                for event in longpoll.listen():
                    if (event.type == VkEventType.MESSAGE_NEW and not event.from_me):

                        some_id = event.chat_id if event.from_chat else event.user_id
                        if some_id not in self._dialog_threads:
                            self._create_dialog_thread(some_id)

                        if event.text.startswith('/'):
                            self._executeCommand(event.text.lower(), event.user_id, some_id)
                        elif self._run and self._dialog_threads[some_id].isEnabled():
                            if event.text.startswith('.'):
                                self._dialog_threads[some_id].drop_session(event.user_id)
                                event.text = event.text[1:]
                            self._dialog_threads[some_id].queue.put(
                                Envelope(
                                    Event.ANSWER,
                                    event.user_id, 
                                    event.text.lower()
                                )
                            )
            except Exception:
                self._logger.log(traceback.format_exc())

    def _executeCommand(self, message, user_id, some_id):
        if user_id in self._global_admins:
            admin = AdminClass.GLOBAL
        elif user_id in self._dialog_threads[some_id].local_admins:
            admin = AdminClass.LOCAL
        else:
            admin = AdminClass.NONE
        answer, need_save = self._cmd.execute(message, some_id, admin)
        if need_save:
            self._serialize()
        self._send_queue.put(ToSend(some_id, answer))

    def _stop_artem(self, some_id=None):
        if some_id:
            self._dialog_threads[some_id].setEnablingState(False)
        else:
            self._run = False

    def _resume_artem(self, some_id=None):
        if some_id:
            self._dialog_threads[some_id].setEnablingState(True)
        else:
            self._run = True

    def _sleep_artem(self, interval, some_id=None):
        if some_id:
            self._dialog_threads[some_id].setEnablingState(False)
            args = {some_id}
        else:
            self._run = False
            args = {}
        timer = threading.Timer(interval, self._resume_artem, args)
        timer.start()
