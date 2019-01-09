import threading
import datetime

from .others import left_seconds

    def select_wait_event(last_time, scens, global_scens, run, interlocutors, all_names):
        for scen_info in scens:
            if scen_info.deltatime < (datetime.datetime.now() - last_time):
                is_suit = scen_info.scn_type.suitable(
                    None, None, interlocutors, None, None)
                global_status = find_element(
                    global_scens, 
                    lambda sc: sc.scn_type == scen_info.scn_type
                ).status
                if is_suit and scen_info.status and global_status:
                    # print('run scenario ' + str(scen_info.scn_type))
                    scen = scen_info.scn_type(interlocutors, all_names)
                    scen_info.calculate_next()
                    new_id = 'all'
                    _add(run, new_id, scen)
                    yield scen

    def select_time_event(scens, global_scens, run, interlocutors, all_names):
        for scen_info in scens:
            if scen_info.next_time() < datetime.datetime.now():
                scen_info.calculate_next()
                is_suit = scen_info.scn_type.suitable(
                    None, None, interlocutors, None, None)
                global_status = find_element(
                    global_scens, 
                    lambda sc: sc.scn_type == scen_info.scn_type
                ).status
                if is_suit and scen_info.status and global_status:
                    # print('run scenario ' + str(scen_info.scn_type))
                    scen = scen_info.scn_type(interlocutors, all_names)
                    new_id = 'all'
                    _add(run, new_id, scen)
                    yield scen


    def select_answer(
            scens, global_scens, run, sender_id, sender, message,
            interlocutors, is_personal, name, all_names, answer=None
        ):
        _check_idle_timeout(run)
        index = 0
        while index != len(run) + len(scens):
            scen = None
            if index < len(run):
                item = run[index]
                if item['target'] == ('all' or sender_id):
                    scen = item['scen']
            else:
                scen_info = scens[index - len(run)]
                is_suit = scen_info.scn_type.suitable(
                    message, sender, interlocutors, is_personal, name, answer
                )
                find_run = _is_scen_run(run, scen_info.scn_type, sender_id)
                index += 1
                global_status = find_element(
                    global_scens, 
                    lambda sc: sc.scn_type == scen_info.scn_type
                ).status
                if is_suit and not find_run and scen_info.status and global_status:
                    # print('run scenario ' + str(scen_info.scn_type))
                    scen = scen_info.scn_type(interlocutors, all_names)
                    new_id = 'all' if not sender_id or scen.with_all else sender_id
                    _add(run, new_id, scen)
            index += 1
            if scen:
                yield scen
    
    def select_postproc(
            scens, global_scens, run, sender_id, sender, message,
            interlocutors, is_personal, name, all_names, answer
        ):
        select_answer(scens, global_scens, run, sender_id, sender,
        message, interlocutors, is_personal, name, all_names, answer)

    def _check_idle_timeout(run):
        i = 0
        while i != len(run):
            if run[i]['scen'].max_idle_time:
                if left_seconds(run[i]['time']) >= run[i]['scen'].max_idle_time:
                    run.remove(run[i])
                    i -= 1
            elif run[i]['scen'].replic_count == run[i]['scen'].max_replicas:
                run.remove(run[i])
                i -= 1
            i += 1

    def _add(to, target, scen):
        run_scen_info = {}
        run_scen_info['target'] = target

        def _scen_wrap(scen_respond):
            run_scen_info['scen'].replic_count += 1
            run_scen_info['time'] = datetime.datetime.now()
            return scen_respond()

        scen.respond = _scen_wrap(scen.respond)
        run_scen_info['scen'] = scen
        to.append(run_scen_info)

    def _is_scen_run(run, scn_type, sender_id):
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

  