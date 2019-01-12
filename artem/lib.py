from sortedcontainers import SortedList

from .artevent import ArtEvent
from .scen_info import *
from .scenario import find_element

class Lib(object):

    def __init__(self):
        self._start = []
        self._addfriend = []
        self._answer = SortedList(key=lambda x: x.priority)
        self._postproc = []
        self._time = []
        self._idle = []
        self._silence = []
        # LIFO

    def add_event(self, event, scen, prior=0, time_delta=None,
        time1=None, time2=None, rand_shift=0, static_time=False):
        
        if ArtEvent[event] == ArtEvent.START:
            self._start.append(ScenInfo(scen))
        elif ArtEvent[event] == ArtEvent.ADDFRIEND:
            self._addfriend.append(ScenInfo(scen))
        elif ArtEvent[event] == ArtEvent.ANSWER:
            self._answer.add(PriorScenInfo(scen, prior))
        elif ArtEvent[event] == ArtEvent.POSTPROC:
            self._postproc.append(ScenInfo(scen))
        elif ArtEvent[event] == ArtEvent.TIME:
            self._time.append(TimeScenInfo(scen, time1, time2, rand_shift, static_time))
        elif ArtEvent[event] == ArtEvent.IDLE:
            self._idle.append(WaitScenInfo(scen, time_delta, rand_shift))
        elif ArtEvent[event] == ArtEvent.SILENCE:
            self._silence.append(WaitScenInfo(scen, time_delta, rand_shift))

    def __getitem__(self, key):
        key = ArtEvent[key]
        if key == ArtEvent.START:
            return self._start
        elif key == ArtEvent.ADDFRIEND:
            return self._addfriend
        elif key == ArtEvent.ANSWER:
            return self._answer
        elif key == ArtEvent.POSTPROC:
            return self._postproc
        elif key == ArtEvent.TIME:
            return self._time
        elif key == ArtEvent.IDLE:
            return self._idle
        elif key == ArtEvent.SILENCE:
            return self._silence

    def _get_scenarios(self, event):
        if isinstance(event, str):
            event = ArtEvent[event.upper()]
        elif not isinstance(event, ArtEvent):
            raise TypeError(str(event) + ' event not defined')
        return find_element(self._all_scenarios, lambda s: s.event == event)

    def get_status(self, event, scen_name):
        scens = self._get_scenarios(event)
        scen_info = find_element(scens, lambda sc: sc.scn_type.__name__.lower() == scn_name)
        return scen_info.status if scen_info else None
    
    def set_status(self, event, scen_name, value):
        scens = self._get_scenarios(event)
        scen_info = find_element(scens, lambda sc: sc.scn_type.__name__.lower() == scn_name)
        if scen_info:
            scen_info.status = value