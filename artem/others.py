import random
import re
from datetime import datetime
import types
import enum
from inspect import signature

from .scenario import *

def _if_dict(new_answer, nosleep=False):
    if not 'message' in new_answer:
        new_answer['message'] = ''
    if not 'sleep' in new_answer:
        if nosleep:
            new_answer['sleep'] = 0.0
        else:
            new_answer['sleep'] = 1 + 5 * round(random.random(), 3)
    if not 'attach' in new_answer:
        new_answer['attach'] = None
    if not 'sticker' in new_answer:
        new_answer['sticker'] = None

def run_scen(scen):
    new_answers = scen.respond()
    if not scen.answer:
        if not new_answers:
            new_answers = [m('')]
        elif isinstance(new_answers, str):
            new_answers = [m(new_answers)]
        elif isinstance(new_answers, dict):
            _if_dict(new_answers)
            new_answers = [new_answers]
        elif isinstance(new_answers, list):
            for i in range(0, len(new_answers)):
                if isinstance(new_answers[i], str):
                    new_answers[i] = m(new_answers[i])
                elif isinstance(new_answers[i], list):
                    try:
                        new_answers[i] = m(*new_answers[i])
                    except Exception:
                        new_answers[i] = m('')
                elif isinstance(new_answers[i], dict):
                    _if_dict(new_answers[i])
                else:
                    raise Exception('Incorrect answer type from scenario ' + 
                        str(type(scen)) + ' :  ' + str(new_answers))
        else:
            raise Exception('Incorrect answer type from scenario ' + 
                str(type(scen)) + ' :  ' + str(new_answers))
        if scen.message:
            scen.messages_history.append(scen.message)
    else:
        if not new_answers:
            new_answers = [m(scen.answer)]
        elif isinstance(new_answers, str):
            if new_answers == '':
                new_answers = [m(scen.answer)]
            else:
                new_answers = [m(new_answers)]
        elif isinstance(new_answers, dict):
            _if_dict(new_answers, nosleep=True)
            if new_answers['message'] == '':
                new_answers['message'] = scen.answer
            new_answers = [new_answers]
        elif isinstance(new_answers, list):
            for i in range(0, len(new_answers)):
                if isinstance(new_answers[i], str):
                    if new_answers[i] == '':
                        new_answers[i] = m(scen.answer)
                    else:
                        new_answers[i] = m(new_answers[i])
                elif isinstance(new_answers[i], list):
                    try:
                        new_answers[i] = m(*new_answers[i])
                    except Exception:
                        new_answers[i] = m(scen.answer)
                elif isinstance(new_answers[i], dict):
                    _if_dict(new_answers[i], nosleep=True)
                    if new_answers[i]['message'] == '':
                        new_answers[i]['message'] = scen.answer
                else:
                    raise Exception('Incorrect answer type from scenario ' + 
                        str(type(scen)) + ' :  ' + str(new_answers))
        else:
            raise Exception('Incorrect answer type from scenario ' + 
                str(type(scen)) + ' :  ' + str(new_answers))   
    return new_answers

def _wrap_respond(func):
    if isinstance(func, str):
        resp_string = func
        func = lambda: resp_string
    def wrap(self):
        sign = signature(func)
        if len(sign.parameters) == 0:
            ret = func()
        elif len(sign.parameters) == 1:
            ret = func(self)
        else:
            raise Exception('Handler must take 0 or 1 parameter (self), no more.')
        self.respond = None
        return ret
    return wrap

def _wrap_suitable(func):
    def wrap(message, i_sender, interlocutors, is_personal, name, answer):
        if isinstance(func, str):
            if func[0] == '<' and func[-1] == '>':
                words = func[1:-1].split('|')
                return True if find_element(words, lambda w: w in message) else False
            else:
                words = func.split('|')
                return True if message in words else False
        else:
            try:
                sign = signature(func)
                acceptable_args = {
                    'message': message,
                    'i_sender': i_sender,
                    'interlocutors': interlocutors,
                    'is_personal': is_personal,
                    'name': name,
                    'answer': answer
                }
                actual_args = []
                for arg in sign.parameters:
                    if arg not in acceptable_args:
                        raise ValueError(
                            f"Argument '{arg}' is not allowed in suitable scenario function. " +
                            f"Acceptable args is: {acceptable_args}."
                        )
                    actual_args.append(acceptable_args[arg])
                ret = func(*actual_args)
            except TypeError:
                ret = func()
            return True if ret else False
    return staticmethod(wrap)

def make_scen(scen, handler, suitable):
    if not scen:
        valid_types = (
            types.FunctionType,
            types.BuiltinFunctionType,
            types.MethodType,
            types.BuiltinMethodType,
            str
        )
        if handler:
            if not isinstance(handler, valid_types):
                raise TypeError('Handler must be function or str value')
        else:
            raise ValueError('Handler must be declared')
        if suitable:
            if not isinstance(suitable, valid_types):
                raise TypeError('Suitable must be function or str value')
        else:
            suitable = lambda: True
        scen = type(
            'Scenario' + str(id(handler)),
            (Scenario,),
            {
                'respond': _wrap_respond(handler),
                'suitable': _wrap_suitable(suitable)
            }
        )
    elif not isinstance(scen, Scenario):
        # duct tape 2 or not
        if not hasattr(scen, 'respond'):
            raise ValueError('Handler must be declared')
        if not hasattr(scen, 'suitable'):
            scen.suitable = _wrap_suitable(lambda: True)
        if not hasattr(scen, 'max_replicas'):
            scen.max_replicas = DEFAULT_MAX_REPLICAS
        if not hasattr(scen, 'max_idle_time'):
            scen.max_idle_time = DEFAULT_MAX_IDLE_TIME
        if not hasattr(scen, 'with_all'):
            scen.with_all = DEFAULT_WITH_ALL_MODE
        if not hasattr(scen, 'description'):
            scen.description = 'Auto-generated scenario without description'
    return scen

def left_seconds(from_datetime):
    return (datetime.now() - from_datetime).seconds / 60

class Interlocutor(object):

    def __init__(self, id, first_name, last_name):
        self._id = id
        self._first_name = first_name
        self._last_name = last_name

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def first_name(self):
        return self._first_name

    @first_name.setter
    def first_name(self, value):
        self._first_name = value

    @property
    def last_name(self):
        return self._last_name

    @last_name.setter
    def last_name(self, value):
        self._last_name = value

class Envelope(object):

    def __init__(self, event, sender_id, message):
        self._message = message
        self._sender_id = sender_id
        self._event = event
    
    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @property
    def sender_id(self):
        return self._sender_id

    @sender_id.setter
    def sender_id(self, value):
        self._sender_id = value
        
    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, value):
        self._event = value

class ToSend(object):

    def __init__(self, id, message, sleep=0.0,
                 attachment=None, sticker=None):
        self.id = id
        if sleep == 0.0:
            sleep = 1.0 + 5 * round(random.random(), 3)
        self.sleep = sleep
        self.message = message
        self.attach = attachment
        self.sticker = sticker

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @property
    def sleep(self):
        return self._sleep

    @sleep.setter
    def sleep(self, value):
        self._sleep = value

    @property
    def attach(self):
        return self._attach

    @attach.setter
    def attach(self, value):
        self._attach = value

    @property
    def sticker(self):
        return self._sticker

    @sticker.setter
    def sticker(self, value):
        self._sticker = value

class Wrap(object):

    def __init__(self, value):
        self.val = value

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, value):
        self._val = value
