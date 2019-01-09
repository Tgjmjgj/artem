from sortedcontainers import SortedList

from .Event import Event
from .ScenInfo import *
from .scenario import find_element

class Lib(object):

    def __init__(self):
        self._start = []
        self._addfriend = []
        self._answer = SortedList(True, lambda x: x.priority)
        self._postproc = []
        self._time = []
        self._idle = []
        self._silence = []
        # LIFO

    def add_event(self, event, scen, prior=0, time_delta=None,
        time1=None, time2=None, rand_shift=0, static_time=False):
        
        if event == Event.START:
            self._start.append(ScenInfo(scen))
        elif event == Event.ADDFRIEND:
            self._addfriend.append(ScenInfo(scen))
        elif event == Event.ANSWER:
            self._answer.add(PriorScenInfo(scen, prior))
        elif event == Event.POSTPROC:
            self._postproc.append(ScenInfo(scen))
        elif event == Event.TIME:
            self._time.append(TimeScenInfo(scen, time1, time2, rand_shift, static_time))
        elif event == Event.IDLE:
            self._idle.append(WaitScenInfo(scen, time_delta, rand_shift))
        elif event == Event.SILENCE:
            self._silence.append(WaitScenInfo(scen, time_delta, rand_shift))

    def __getitem__(self, key):
        if not isinstance(key, Event):
            raise TypeError
        elif key == Event.START:
            return self._start
        elif key == Event.ADDFRIEND:
            return self._addfriend
        elif key == Event.ANSWER:
            return self._answer
        elif key == Event.POSTPROC:
            return self._postproc
        elif key == EventType.TIME:
            return self._time
        elif key == Event.IDLE:
            return self._idle
        elif key == Event.SILENCE:
            return self._silence