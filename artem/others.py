import enum
import random

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

class EventMetaclass(enum.EnumMeta):

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.upper()
        for item in self:
            if item.name == key:
                return item
        return None


class Event(enum.Enum, metaclass=EventMetaclass):
    START = 1
    ADDFRIEND = 2
    ANSWER = 3
    POSTPROC = 4
    DISCOURSE = 5



class Lib(object):


    class Scenarios(object):


        class ScenariosIterator(object):

            def __init__(self, list_):
                self._list = list_
                self._cursor = 0
        
            def __next__(self):
                if self._cursor >= len(self._list):
                    raise StopIteration
                else:
                    result = self._list[self._cursor]
                    self._cursor += 1
                    return result


        class ScenInfo(object):
            
            def __init__(self, scen_class_type, priority):
                self.scn_type = scen_class_type
                self._priority = priority
                self.status = True

            @property
            def scn_type(self):
                return self._scn_type

            @scn_type.setter
            def scn_type(self, value):
                self._scn_type = value

            @property
            def priority(self):
                return self._priority

            @property
            def status(self):
                return self._status

            @status.setter
            def status(self, value):
                if isinstance(value, bool):
                    self._status = value


        def __init__(self, event):
            self.event = event
            self._scenarios = []

        def add(self, scn_type, priority):
            self._scenarios.append(self.ScenInfo(scn_type, priority))
            self._scenarios.sort(key=lambda s: s.priority, reverse=True)

        def such_scen(self, scn_name):
            return find_element(
                    self._scenarios, 
                    lambda s: s.scn_type.__name__.lower() == scn_name
                    )

        def get_status(self, scn_name):
            return self.such_scen(scn_name).status
        
        def set_status(self, scn_name, status):
            scn = self.such_scen(scn_name)
            if scn:
                scn.status = status
        
        def __iter__(self):
            return self.ScenariosIterator(self._scenarios)
        
        def __len__(self):
            return len(self._scenarios)

        def __getitem__(self, key):
            if key is None:
                raise KeyError
            elif not isinstance(key, int):
                raise TypeError
            else:
                return self._scenarios[key]


    def __init__(self):
        self._all_scenarios = []
        for event in Event:
            self._all_scenarios.append(self.Scenarios(event))

    def _get_scenarios(self, event):
        if isinstance(event, str):
            event = Event[event.upper()]
        return find_element(self._all_scenarios, lambda s: s.event == event)

    def get_sceninfo(self, event, scn_name):
        return self._get_scenarios(event).such_scen(scn_name.lower())

    def get_status(self, event, scn_name):
        return self._get_scenarios(event).get_status(scn_name.lower())

    def set_status(self, event, scn_name, status):
        self._get_scenarios(event).set_status(scn_name.lower(), status)

    def add(self, event, scn_type, priority):
        self._get_scenarios(event).add(scn_type, priority)

    def exists(self, event, scn_name):
        return (True 
                if self._get_scenarios(event).such_scen(scn_name)
                else False)
    
    def __getitem__(self, key):
        if isinstance(key, str):
            key = Event[key]
        if not isinstance(key, Event):
            raise TypeError
        else:
            return self._get_scenarios(key)


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

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, value):
        self._val = value