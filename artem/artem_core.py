#!/usr/bin/python3
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
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from .dialogthread import DialogThread
from .artem_pb2 import ProtoArtem
from .others import *
from .scenario import Scenario
from .commands import Commands
from .cmd import AdminClass
from .lib import Lib
from .time_parser import *
from .artevent import ArtEvent
from .artem_logger import ArtemLogger
from .defaults import *

class Artem():
    """Main Artem bot class
    
    Parameters
    ----------
    groupId : str
        Id of VK community, where the bot will be placed
    group_acess_token : str
        Secret community access token
    admins : list of str, optional
        CLI bot admin Id list, by default []
    names : list of str, optional
        List of bot names to contact, by default []
    enable_session : bool, optional
        Will the bot be able to memorize the conversation and answer without name invocation, by default True
    restore : bool, optional
        Enable or not the state of configs after bot restart, by default True
    """

    def __init__(
            self, groupId, group_acess_token, admins=[],
            names=[], enable_session=True, restore=True
        ):
        self._lib = Lib()
        # {some_id: [DialogThread, status(True/False)]}
        self._dialog_threads = {}
        self._restore = restore
        self._global_admins = admins
        self._secondary_polling_interval = Wrap(DEFAULT_POLLING_INTERVAL)
        self._sessions = Wrap(enable_session)
        self._send_queue = queue.Queue()
        self._run = True
        self._sessions = Wrap(enable_session)
        self._logger = ArtemLogger()
        self._vk_init(group_acess_token)
        self._groupId = groupId
        self._cmd = Commands(self)
        response = self._vk.method('groups.getById')
        full_name = response[0]['name'].lower()
        if full_name not in names:
            names.append(full_name)
        first_word_name = full_name.split()[0]
        if first_word_name not in names:
            names.append(first_word_name)
        self._global_names = sorted(names)

    def on(
        self,
        event, scen=None, prior=0, handler=None, suitable=None):
        """Add scenario (handler) to one of the regular events
        
        Parameters
        ----------
        event : Union[str, :class:`artem.artevent.ArtEvent`]
            Available events: 'MESSAGE', 'START', 'JOIN', 'POSTPROC'
        scen : :class:`artem.scenario.Scenario`, optional
            Handler in form of a complete Scenario class to this event, by default None
        prior : int, optional
            Priority of the scenario, the lower the value, the higher the priority, by default 0
        handler : Union[str, Function], optional
            Scenario event handler function, by default None
            May be just a string representing the clear answer.
            Or function, which can take one parameter 'self' - Scenario object with
            all members: message, i_sender, is_personal, answer, etc.
        suitable : Union[str, Function], optional
            Scenario event handler checker function, by default None
            It can be a string with special syntax:
                "msg" - scenario fits if the message EXACTLY matches 'msg'
                "msg1|msg2" - fits if the message EXACTLY matches 'msg1' OR 'msg2'
                "<msg1|msg2>" - fits if the message CONTAINS 'msg1' OR 'msg2' 
            Or it can be a function, which can takes such parameters:
                message, i_sender, interlocutors, is_personal, name, answer
            in no particular order and number
            
        Returns
        -------
        `artem.scenario.Scenario`
            Completed scenario class
        """
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
        """Add scenario to (handler) to one of the time-based event
        
        Parameters
        ----------
        event : Union[str, :class:`artem.artevent.ArtEvent`]
            Available events: 'TIME', 'IDLE', 'SILENCE'
        first_time : Union[datetime.datetime, str]
            For 'TIME' event it is the main datetime when run the scenario,
            or first datetime in interval scenario
            For 'IDLE' and 'SILENCE' events it need to be an human-friendly interval string, like:
                '30 seconds', '2 hours 10 minutes', '1 day'
        second_time : datetime.datetime, optional
            Second datetime in 'TIME' interval scenario, by default None
        rand_shift : int, optional
            The number of seconds by which time may deviate from the specified time, by default 0
        static_time : bool, optional
            Only for the interval 'TIME' event.
            It means from what point in time the next interval should be started.
            If set to True the next interval starts clearly after delta time (second_time - first_time).
            If set to False the next interval starts after delta time shifted by random value from rand_shift.
            By default True
        scen : :class:`artem.scenario.Scenario`, optional
            Handler in form of a complete Scenario class to this event, by default None
        handler : Union[str, Function], optional
            Scenario event handler function, by default None
            May be just a string representing the clear answer.
            Or function, which can take one parameter 'self' - Scenario object with
            all members: message, i_sender, is_personal, answer, etc.
        suitable : Union[str, Function], optional
            Scenario event handler checker function, by default None
            It can be a string with special syntax:
                "msg" - scenario fits if the message EXACTLY matches 'msg'
                "msg1|msg2" - fits if the message EXACTLY matches 'msg1' OR 'msg2'
                "<msg1|msg2>" - fits if the message CONTAINS 'msg1' OR 'msg2' 
            Or it can be a function, which can takes such parameters:
                message, i_sender, interlocutors, is_personal, name, answer
            in no particular order and number
        
        Returns
        -------
        `artem.scenario.Scenario`
            Completed scenario class
        """
        try:
            scen = make_scen(scen, handler, suitable)
            if ArtEvent[time_event] == ArtEvent.IDLE or ArtEvent[time_event] == ArtEvent.SILENCE:
                time_delta = parse_timedelta(first_time)
                self._lib.add_event(time_event, scen, time_delta=time_delta, rand_shift=rand_shift)
                for s_id in self._dialog_threads:
                    self._dialog_threads[s_id].lib.add_event(time_event, scen,
                        time_delta=time_delta, rand_shift=rand_shift)
            elif ArtEvent[time_event] == ArtEvent.TIME:
                first_time = parse_time(first_time)
                second_time = parse_time(second_time)
                self._lib.add_event(time_event, scen,
                    time1=first_time, time2=second_time,
                    rand_shift=rand_shift, static_time=static_time)
                for s_id in self._dialog_threads:
                    self._dialog_threads[s_id].lib.add_event(time_event, scen,
                        time1=first_time, time2=second_time,
                        rand_shift=rand_shift, static_time=static_time)
            return scen
        except Exception:
            self._logger.log(traceback.format_exc())

    def _vk_init(self, access_token):
        try:
            self._vk = vk_api.VkApi(token=access_token)
        except Exception:
            self._logger.log(traceback.format_exc())

    def _get_interlocutors(self, some_id): 
        if some_id > CHAT_ID_START:
            response = self._vk.method(
                'messages.getConversationMembers',
                { 'peer_id': some_id }
            )
            inters = [
                Interlocutor(
                    profile['id'], 
                    profile['first_name'], 
                    profile['last_name']
                ) 
                for profile in response['profiles']
                if profile['id'] != self._groupId
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

    def _create_dialog_thread(
            self, some_id,
            enable_ses=DEFAULT_ENABLED_SESSION,
            session_dur=DEFAULT_SESSION_DURATION,
            names=None,
            admins=None,
            run=True
        ):
        if not names:
            names = self._global_names
        if not admins:
            admins = self._global_admins
        if some_id not in self._dialog_threads:
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
                run
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
            art.run = self._run
            for sid in self._dialog_threads:
                thr = art.dialog_threads.add()
                thr.some_id = sid
                thr.session_duration = self._dialog_threads[sid].session_duration.val
                thr.sessions = self._dialog_threads[sid].enabled_session.val
                thr.run = self._dialog_threads[sid].isEnabled()
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
            self._run = art.run
            for thr in art.dialog_threads:
                self._create_dialog_thread(
                    thr.some_id,
                    thr.sessions,
                    thr.session_duration,
                    [name for name in thr.names], 
                    [admin for admin in thr.admins],
                    thr.run
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
                if answer.attach is not None:
                    if answer.attach.startswith('http'):
                        image = session.get(answer.attach, stream=True)
                        photo = upload.photo_messages(photos=image.raw)[0]
                        answer.attach = 'photo{}_{}'.format(
                            photo['owner_id'], photo['id']
                        )
                        answer.sleep = 0.0
                time.sleep(answer.sleep)
                self._vk.method(
                    'messages.send',
                    {
                        'peer_id': answer.id, 
                        'message': answer.message,
                        'random_id': random.getrandbits(32),
                        'attachment': answer.attach,
                        'sticker_id': answer.sticker
                    }
                )
        except Exception:
            self._logger.log(traceback.format_exc())

    def alive(self):
        """Start the bot
        """
        threading.Thread(target=self._send_listener).start()
        if self._restore:
            self._deserialize()
        for thr in self._dialog_threads.values():
            thr.queue.put(Envelope(ArtEvent.START, None, None))
        while True:
            try:
                longpoll = VkBotLongPoll(self._vk, self._groupId)
                for event in longpoll.listen():
                    if str(event.object.from_id) == '-' + self._groupId:
                        continue
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        some_id = event.object.peer_id
                        sender_id = event.object.from_id
                        msg_text = event.object.text.lower()
                        if some_id not in self._dialog_threads:
                            self._create_dialog_thread(some_id, self._sessions)
                        if msg_text.startswith('/'):
                            self._executeCommand(msg_text, sender_id, some_id)
                        elif self._run and self._dialog_threads[some_id].isEnabled():
                            if msg_text.startswith('.'):
                                self._dialog_threads[some_id].drop_session(sender_id)
                                msg_text = msg_text[1:]
                            self._dialog_threads[some_id].queue.put(
                                Envelope(ArtEvent.MESSAGE, sender_id, msg_text)
                            )
                    elif event.type == VkBotEventType.GROUP_JOIN:
                        user_id = event.object.user_id
                        if user_id not in self._dialog_threads:
                            self._create_dialog_thread(user_id, self._sessions)
                        self._dialog_threads[user_id].queue.put(
                            Envelope(ArtEvent.JOIN, user_id, None)
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
        output, need_save = self._cmd.execute(message, some_id, admin)
        if need_save:
            self._serialize()
        self._send_queue.put(ToSend(some_id, output))

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
