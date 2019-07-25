import threading
import random
import traceback
import datetime
import queue
import copy
import enum
import time

from .scenario import *
from .others import *
from .scselector import *
from .artevent import ArtEvent

DEFAULT_TIME_EVENT_ITERATION = 5.0

class DialogThread(threading.Thread):

    # {"party"(id/all): Scenario class object}    
    _run_scen = []

    # list of pair [["party"(id/all): Postproc scenario class object]]
    _run_post_scen = []

    # {"user_id": Thread class object}
    _sessions = {}

    def __init__(
            self, some_id, postback_queue, lib, interlocutors, 
            logger, global_names, global_admins,
            enable_ses, session_dur, run
        ):
        threading.Thread.__init__(self)
        self.daemon = True

        self.some_id = some_id
        self.status = run
        self._postback_queue = postback_queue
        self.queue = queue.Queue()
        self.interlocutors = interlocutors
        self._logger = logger

        self.enabled_session = enable_ses if isinstance(enable_ses, Wrap) else Wrap(enable_ses)
        self.session_duration = session_dur if isinstance(session_dur, Wrap) else Wrap(session_dur)
        self.time_event_iteration = Wrap(DEFAULT_TIME_EVENT_ITERATION)
        self._run_scen = []
        self._run_post_scen = []
        self._sessions = {}
        self.local_names = []
        self.local_admins = []
        self.lib = copy.deepcopy(lib)

        self._global_names = global_names
        self._global_admins = global_admins
        self._global_lib = lib

    def isEnabled(self):
        return self.status
    
    def setEnablingState(self, new_state):
        self.status = new_state
    
    def _response(self, answers, idle_time, silence_time):
            if answers:
                panswers = self._postprocess(answers, None, None, None, None)
                if panswers:
                    for ans in panswers:
                        self._postback_queue.put(ans)
                        silence_time.val = idle_time.val = datetime.datetime.now()

    def _time_events(self, idle_time, silence_time):
        idle_scens = select_wait_event(
            idle_time.val,
            self.lib[ArtEvent.IDLE],
            self._global_lib[ArtEvent.IDLE],
            self._run_scen,
            self.interlocutors,
            self.local_names + self._global_names
        )
        for scen in idle_scens:
            answers = self._run_scenario(scen, None, None, None)
            self._response(answers, idle_time, silence_time)

        silence_scens = select_wait_event(
            silence_time.val,
            self.lib[ArtEvent.SILENCE],
            self._global_lib[ArtEvent.SILENCE],
            self._run_scen,
            self.interlocutors,
            self.local_names + self._global_names
        )
        for scen in silence_scens:
            answers = self._run_scenario(scen, None, None, None)
            self._response(answers, idle_time, silence_time)
        
        time_scens = select_time_event(
            self.lib[ArtEvent.TIME],
            self._global_lib[ArtEvent.TIME],
            self._run_scen,
            self.interlocutors,
            self.local_names + self._global_names
        )
        for scen in time_scens:
            answers = self._run_scenario(scen, None, None, None)
            self._response(answers, idle_time, silence_time)
    
    def run(self):
        last_non_idle_time = Wrap(datetime.datetime.now())
        last_non_silence_time = Wrap(datetime.datetime.now())
        while True:
            try:
                try:
                    envelope = self.queue.get(timeout=DEFAULT_TIME_EVENT_ITERATION)
                    last_non_silence_time.val = datetime.datetime.now()
                    name = self._extract_name(envelope.message)
                    is_personal = self._is_message_personal(name)
                    sender = self._get_message_sender(envelope.sender_id)
                    if envelope.event == ArtEvent.MESSAGE:
                        answers = self._answer(envelope, name, is_personal, sender)
                    else:
                        answers = self._non_answer(envelope, sender)
                    self._response(answers, last_non_idle_time, last_non_silence_time)
                except queue.Empty:
                    pass
                except Exception:
                    self._logger.log(traceback.format_exc())
                if self.isEnabled():
                    self._time_events(last_non_idle_time, last_non_silence_time)
            except Exception:
                self._logger.log(traceback.format_exc())

    def _answer(self, envelope, name, is_personal, sender):
        """
            envelope = Envelope { message, sender_id, event }
        """
        if is_personal and self.enabled_session.val:
            self._update_session(envelope.sender_id)
        scenario = choose_scenario(
            self.lib[envelope.event],
            self._global_lib[envelope.event],
            self._run_scen, envelope.sender_id,
            sender, envelope.message, self.interlocutors,
            is_personal, name, self.local_names + self._global_names, None)
        answers = None
        try:
            while not answers:
                scn = next(scenario)
                answers =  self._run_scenario(scn, envelope.message, sender, is_personal)
        except StopIteration:
            pass
        return answers
        
    def _non_answer(self, envelope, sender):
        scenario = select_non_answer(
            self.lib[envelope.event],
            self._global_lib[envelope.event],
            self._run_scen, self.interlocutors,
            self.local_names + self._global_names)
        answers = None
        try:
            while not answers:
                scn = next(scenario)
                answers =  self._run_scenario(scn, envelope.message, sender, None)
        except StopIteration:
            pass
        return answers

    def _postprocess(self, answers, envelope, name, is_personal, sender):
        ret_answers = []
        if len(self.lib[ArtEvent.POSTPROC]) == 0:
            for ans in answers:
                send = ToSend(
                    self.some_id,
                    ans['message'],
                    ans['sleep'],
                    ans['attach'],
                   ans['sticker']
                )
                ret_answers.append(send)
            return ret_answers
        answers_left = len(answers)
        message = envelope.message if envelope else None
        sender_id = envelope.sender_id if envelope else None
        for answer in answers:
            answers_left -= 1
            pp_scenario = select_postproc(
                self.lib[ArtEvent.POSTPROC],
                self._global_lib[ArtEvent.POSTPROC],
                self._run_post_scen,
                sender_id, sender, message, self.interlocutors,
                is_personal, name, self.local_names + self._global_names,
                answer['message']
            )
            postproc_answers = None
            try:
                for scn in pp_scenario:
                    scn.answers_left = answers_left
                    postproc_answers = self._run_scenario(scn, message, sender, 
                                                          is_personal, answer['message'])
            except StopIteration:
                pass
            attach, sticker = None, None
            if answer['attach']:
                attach = answer['attach']
            if answer['sticker']:
                sticker = answer['sticker']
            #print(postproc_answers)
            for i in range(0, len(postproc_answers)):
                send = ToSend(
                    self.some_id,
                    postproc_answers[i]['message'],
                    postproc_answers[i]['sleep'],
                    postproc_answers[i]['attach'],
                    postproc_answers[i]['sticker']
                )
                if postproc_answers[i]['sleep'] == 0.0:
                    send.sleep = answer['sleep']
                if i == 0:
                    if not postproc_answers[0]['attach']:
                        send.attach = attach
                    if not postproc_answers[0]['sticker']:
                        send.sticker = sticker
                ret_answers.append(send)
        return ret_answers

    def _run_scenario(self, scen, message, sender, is_personal, answer=None):
        answers = None
        scen.update_env(message, sender, is_personal, answer)
        try:
            answers = run_scen(scen)
        except:
            self._logger.log(traceback.format_exc())
        #print(answers)
        if answers and [ans for ans in answers if ans['message'] != '']:
            return answers
        else:
            return None

    def _get_message_sender(self, sender_id):
        return find_element(
            self.interlocutors,
            lambda i: i.id == sender_id
        )

    def _extract_name(self, msg):
        if msg:
            name = find_element(
                self._global_names + self.local_names,
                lambda n: msg.startswith(n)
            )
            return name

    def _is_message_personal(self, name):
        if len(self.interlocutors) > 1 and not name:
            return False
        else:
            return True
            
    def _update_session(self, sender_id):
        if sender_id in self._sessions:
            self._sessions[sender_id].cancel()
        self._sessions[sender_id] = threading.Timer(
            self.session_duration.val,
            self.drop_session,
            { sender_id }
        )

    def drop_session(self, user_id):
        try:
            if user_id in self._sessions:
                del self._sessions[user_id]
        except:
            self._logger.log(traceback.format_exc())

