import threading
import random
import traceback
import datetime
import queue
import copy
import time

from .scenario import *
from .others import *


class DialogThread(threading.Thread):

    # {"party"(unique): Scenario class object}    
    _run_scen = []

    # list of pair [["party"(non unique): Postproc scenario class object]]
    _run_post_scen = []

    # {"user_id": Thread class object}
    _sessions = {}

    def __init__(self, some_id, postback_queue, lib,
                interlocutors, logger, names, enabled_session,
                session_duration, discourse_max, start):

        threading.Thread.__init__(self)
        self.daemon = True

        self.some_id = some_id
        self._postback_queue = postback_queue
        self.queue = queue.Queue()
        self.interlocutors = interlocutors
        self._logger = logger
        self.enabled_session = enabled_session
        self.session_duration = session_duration
        self.discourse_interval_max = discourse_max
        self._start = start
        self._run_scen = []
        self._run_post_scen = []
        self._sessions = {}
        self.names = names.copy()
        self.lib = copy.deepcopy(lib)

    def run(self):

        try:
            if self._start:
                self._run(Event.START,
                                     msg=None, one=False)
            self._activate_discourse()
        except:
            self._logger.error(traceback.format_exc())

        while True:
            try:
                msg = self.queue.get()
                if msg.event == Event.ANSWER:
                    self._run(Event.ANSWER, msg)
                elif msg.event == Event.ADDFRIEND:
                    self._run(Event.ADDFRIEND, msg)
            except:
                self._logger.error(traceback.format_exc())

    # FEROCITY or 'лютая дичь'
    def _run(self, event, msg, one=True):

        message = msg.message if msg else None
        sender_id = msg.sender_id if msg else None
        is_personal = True
        name = None
        if len(self.interlocutors) > 1:
            if event == Event.ANSWER:
                if sender_id in self._sessions and self.enabled_session:
                    self._sessions[sender_id].cancel()
                    self._sessions[sender_id] = threading.Timer(
                            self.session_duration,
                            self._drop_session, {sender_id})
                    self._sessions[sender_id].start()
                else: 
                    name = find_element(
                            self.names, lambda nam: message.startswith(nam))
                    if name:
                        if self.enabled_session:
                            self._sessions[sender_id] = threading.Timer(
                                    self.session_duration, 
                                    self._drop_session, {sender_id})
                            self._sessions[sender_id].start()
                    else:
                        is_personal = False

        def answer_handler(answers):
            for ans in answers:
                if ans['message'] == '':
                    continue
                else:
                    time.sleep(ans['sleep'])
                    postproc_answers = self._find_answer(
                        Event.POSTPROC,
                        sender_id, message, is_personal, name,
                        lambda a: (a, len(a) > 1),
                        ans['message'], False
                        )
                    attach = None
                    if ans['attach']:
                        attach = ans['attach']
                    #print(postproc_answers)
                    for i in range(0, len(postproc_answers)):
                        send = ToSend(
                                self.some_id,
                                postproc_answers[i]['message'],
                                postproc_answers[i]['attach'])
                        if i == 0: 
                            if not postproc_answers[i]['attach']:
                                send.attach = attach
                        else:
                            time.sleep(postproc_answers[i]['sleep'])
                        self._postback_queue.put(send)
            return answers, False

        self._find_answer(event, sender_id, message, is_personal,
                          name, answer_handler)

    def _find_answer(self, event, sender_id, message, is_personal,
                     name, handler, answer=None, one=True):

        i_sender = find_element(
                self.interlocutors,
                lambda i: i.id == sender_id
                )
        if event == Event.POSTPROC:
            run = self._run_post_scen
        else:
            run = self._run_scen

        i = 0
        while i != len(run):
            if run[i][1].max_idle_time:
                if ((datetime.datetime.now() - 
                        run[i][1].time).seconds / 60 >= 
                            run[i][1].max_idle_time
                        ):
                    run.remove(run[i])
                    i -= 1
            i += 1

        index = 0
        ret_answers = []
        ret_answers.append(m(answer))
        while index != len(run) + len(self.lib[event]):
            scen = None
            if index < len(run):
                item = run[index]
                if item[0] == 'all' or item[0] == sender_id:
                    scen = item[1]
                else:
                    index += 1

            else:
                scen_info = self.lib[event][index - len(run)]
                index += 1
                is_suitable = scen_info.scn_type.suitable(
                        message, i_sender, self.interlocutors,
                        is_personal, name
                        )
                find_run = find_element(
                        run, lambda item: 
                            type(item[1]) == scen_info.scn_type and
                            item[0] == ('all' or sender_id)
                        )
                if is_suitable and not find_run and scen_info.status == 'on':
                    #print('run scenario ' + str(scen_info.scn_type))
                    scen = scen_info.scn_type()
                    scen.replic_count = 0
                    set_env(scen, self.interlocutors, self.names)
                    new_id = ('all' 
                            if not sender_id or scen.with_all
                            else sender_id
                            )
                    run.append([new_id, scen])
            if not scen:
                continue

            index += 1
            answers = None
            scen.replic_count += 1
            update_env(scen, message, i_sender,
                       is_personal, answer)
            try:
                answers = run_scen(scen)
            except:
                self._logger.error(traceback.format_exc())
            scen.time = datetime.datetime.now()
            #print(answers)

            if answers and [ans for ans in answers if ans['message'] != '']:
                success = True
                ret_answers, end = handler(answers)
            else:
                success, end = False, False 

            if (not answers or not scen.respond or 
                    scen.replic_count == scen.max_replicas):

                run.remove(find_element(
                            run, lambda item: item[1] == scen)
                        )
                index -= 1
                if not answers:
                    raise Exception('Scenario ' +
                            type(scen).__name__ + ' return not that.')
            if (success and one) or end:
                break

        return ret_answers


    def _activate_discourse(self):
        rnd_time = random.randint(10, self.discourse_interval_max)
        #print('Random time: ' + str(rnd_time) + ' s.')
        timer = threading.Timer(rnd_time, self._discourse, {})
        timer.start()

    def _discourse(self):
        try:
            self._run(Event.DISCOURSE, None)
        except:
            self._logger.error(traceback.format_exc())
        finally:
            self._activate_discourse()

    def _drop_session(self, user_id):
        try:
            if user_id in self._sessions:
                del self._sessions[user_id]
        except:
            self._logger.error(traceback.format_exc())

    # duct tape
    def stop_scenario(self, event, scen_name):
        if event == Event.POSTPROC:
            el = find_element(
                    self._run_post_scen,
                    lambda el: type(el[1]).__name__.lower() == scen_name)
            while el:
                self._run_post_scen.remove(el)
                el = find_element(
                        self._run_post_scen,
                        lambda el: type(el[1]).__name__.lower() == scen_name)
        else:
            keys_to_del = []
            for key in self._run_scen:
                if type(self._run_scen[key])._name_.lower() == scen_name:
                    keys_to_del.append(key)
            for key in keys_to_del:
                del self._run_scen[key]
