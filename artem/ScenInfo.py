from datetime import datetime, timedelta
from random import randint

from .scenario import Scenario

class ScenInfo(object):
            
    def __init__(self, scen_class_type):
        self.scn_type = scen_class_type
        self.status = True

    @property
    def scn_type(self):
        return self._scn_type

    @scn_type.setter
    def scn_type(self, value):
        if (isinstance(value, Scenario)):
            self._scn_type = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if isinstance(value, bool):
            self._status = value

class PriorScenInfo(ScenInfo):

    def __init__(self, scen_class_type, priority):
        super().__init__(scen_class_type)
        self._priority = priority

    @property
    def priority(self):
        return self._priority

    @property.setter
    def priority(self, value):
        if (isinstance(value, (int, float))):
            self._priority = value


class TimeScenInfo(ScenInfo):

    def __init__(self, scen_class_type, first_time, second_time, rand_shift, static_time):
        super().__init__(scen_class_type)
        self._is_static_time = static_time
        self._rand_shift = rand_shift
        self._interval = None if second_time is None else second_time - first_time
        half = rand_shift / 2
        rand_delta = timedelta(seconds=randint(-half, half))
        if self._interval is not None:
            while first_time + rand_delta < datetime.now():
                first_time += self._interval
        self._next_time = first_time + rand_delta

class WaitScenInfo(ScenInfo):

    def __init__(self, scen_class_type, time_delta, rand_shift):
        super().__init__(scen_class_type)
        self._delta = time_delta
        self._rand_shift = rand_shift
    