import threading
import datetime

class ScSelector:

    def __init__(self, scens, global_scens, run):
        self._scens = scens
        self._global_scens = global_scens
        self._run = run
        self._index = 0

    def select(self, sender_id, message, interlocutors, is_personal, name, all_names):
        self._check_idle_timeout()
        self._index = 0
        sender = self._get_message_sender(sender_id)
        while index != len(self._run) + len(self._scens):
            scen = None
            if index < len(self._run):
                item = self._run[self._index]
                if item['target'] == ('all' or sender_id):
                    scen = item['scen']
            else:
                scen_info = self._scens[self._index - len(self._run)]
                is_suit = scen_info.scn_type.suitable(
                    message, sender, interlocutors, is_personal, name
                )
                find_run = self._is_scen_run(self._run, scen_info.scn_type, sender_id)
                self._index += 1
                global_status = find_element(self._global_scens, 
                                             lambda sc: sc.scn_type == scen_info.scn_type)
                )
                if is_suit and not find_run and scen_info.status and global_status:
                    # print('run scenario ' + str(scen_info.scn_type))
                    scen = scen_info.scn_type(interlocutors, all_names)
                    new_id = 'all' if not sender_id or scen.with_all else sender_id
                    self._add(new_id, scen)
            self._index += 1
            if scen:
                yield scen
    
    def _check_idle_timeout(self):
        i = 0
        while i != len(self._run):
            if self._run[i]['scen'].max_idle_time:
                left_time = (datetime.datetime.now() - self._run[i]['time']).seconds / 60
                if left_time >= self._run[i]['scen'].max_idle_time:
                    self._run.remove(self._run[i])
                    i -= 1
            elif self._run[i]['scen'].replic_count == self._run[i]['scen'].max_replicas:
                self._run.remove(self._run[i])
                i -= 1
            i += 1

    # memory leak?
    def _add(self, target, scen):
        run_scen_info = {}
        run_scen_info['target'] = target

        def _scen_wrap(scen_respond):
            run_scen_info['scen'].replic_count += 1
            run_scen_info['time'] = datetime.datetime.now()
            return scen_respond()

        scen.respond = _scen_wrap(scen.respond)
        run_scen_info['scen'] = scen
        self._run.append(run_scen_info)

    def _get_message_sender(self, sender_id):
        return find_element(
            self._intrs,
            lambda i: i.id == sender_id
        )
  
    def _is_scen_run(self, run, scn_type, sender_id):
        return find_element(
            run, lambda item: 
                type(item['scen']) == scn_type and
                item['target'] == ('all' or sender_id)
        )


class Running:
    
    # {"party"(id/all): Scenario class object}    
    _run_scen = []

    # list of pair [["party"(id/all): Postproc scenario class object]]
    _run_post_scen = []

    def __init__(self):
        self._run_scen = []
        self._run_post_scen = []
    
    @property
    def answer(self):
        return self._run_scen

    @property
    def post(self):
        return self._run_post_scen
    
    def add_answer(self, target, scen):
        _add(target, scen, self._run_scen)

    def add_postproc(self, target, scen):
        _add(target, scen, self._run_post_scen)

  