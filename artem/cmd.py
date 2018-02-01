import re
import enum

from . import artem_core


class Control(object):

    def __init__(self, artem):
        self._artem = artem

    def execute(self, command, user_id, source_id):
        answer = ''
        need_save = False
        if command == '/help':
            answer = '''List of available commands:\n\n
                /admins     (add|del [id])                  
                    Information and administration of a group of admins\n
                /discourse_interval (local) [number]        
                    Get or set maximal time between two discourse\n
                /events [event]                             
                    Get information about event types and their scenarios\n
                /help                                       
                    Get help\n
                /names      (add|del (local) [name])        
                    Information and administration of Artem respond names\n
                /pooling_interval   [number]                
                    Get or set time between secondary 
                    pooling (all except messages)\n    
                /scenario (on|off (local)) [event] [name]   
                    Enable or disable a specific scenario\n
                /session_duration   [number]                
                    Get or set duration of session\n
                /sessions   (true|false (local))            
                    Inclusions of sessions\n
                /version                                    
                    Information about Artem version\n'''

        elif command == '/version':
            answer = ('ArtemCore v' + artem_core.VERSION + 
                      '\nRelease: ' + artem_core.RELEASE)

        elif re.match(
                '^/pooling_interval( [0-9](.([0-9]){1,10}){0,1}){0,1}$',
                command):

            if command == '/pooling_interval':
                answer = ('secondary_pooling_interval = ' + 
                        str(self._artem._secondary_pooling_interval) + ' sec')
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                        ' does not have admin permissions')
            else:
                self._artem._secondary_pooling_interval = float(command[18:])
                need_save = True
                answer = ('secondary_pooling_interval was set on ' +
                        str(self._artem._secondary_pooling_interval) + ' sec')

        elif re.match(
                '^/admins( (add|del) ([0-9]){5,15}){0,1}$',
                command):

            if command == '/admins':
                answer = ('admins: ' + 
                        ', '.join([str(a) for a in self._artem._admins]))
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                        ' does not have admin permissions')
            elif 'add' in command:
                new_id = int(command[12:])
                if new_id in self._artem._admins:
                    answer = ('User \"' + str(new_id) +
                            '\" already admin')
                else:
                    self._artem._admins.append(new_id)
                    need_save = True
                    answer = ('User \"' + str(new_id) +
                            '\" was added to admins group')
            elif 'del' in command:
                new_id = int(command[12:])
                if new_id not in self._artem._admins:
                    answer = ('User \"' + str(new_id) +
                            '\" not in admins group')
                else:
                    self._artem._admins.remove(new_id)
                    need_save = True
                    answer = ('User \"' + str(new_id) +
                            '\" was removed from admins group')

        elif re.match(
                '^/names( (add|del)( local){0,1} ([_ a-zа-я0-9]){1,20}){0,1}$',
                command):

            if command == '/names':
                answer = ('Artem default names: ' +
                        ', '.join(self._artem._names))
                answer += ('\nArtem local names: ' +
                           ', '.join(self._artem._dialog_threads[source_id]
                                     .names))
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                    ' does not have admin permissions')
            else:
                new_name = (command[11:] if 'local' not in command 
                        else command[17:])
                if 'add' in command:
                    if 'local' in command:
                        if (new_name in
                                self._artem._dialog_threads[source_id].names):
                            answer = ('Artem already responded in current' +
                                     'chat to the name of \"' +
                                     new_name + '\"')
                        else:
                            (self._artem._dialog_threads[source_id]
                                    .names.append(new_name))
                            self._artem._dialog_threads[source_id].names.sort()
                            need_save = True
                            answer = ('Now you can call Artem \"' +
                                    new_name + '\" in current chat')
                    else:
                        if new_name not in self._artem._names:
                            self._artem._names.append(new_name)
                            self._artem._names.sort()
                        for id in self._artem._dialog_threads:
                            if (new_name not in 
                                    self._artem._dialog_threads[id].names):
                                (self._artem._dialog_threads[id]
                                        .names.append(new_name))
                                self._artem._dialog_threads[id].names.sort()
                        need_save = True
                        answer = ('Now you can call Artem \"' +
                                new_name + '\" anywhere')
                else:
                    if 'local' in command:
                        if (new_name not in 
                                self._artem._dialog_threads[source_id].names):
                            answer = ('Artem not have name \"' +
                                    new_name + '\" in local chat')
                        else:
                            (self._artem._dialog_threads[source_id]
                                    .names.remove(new_name))
                            need_save = True
                            answer = ('Name \"' + new_name +
                                    '\" was removed from Artem' +
                                    ' names in current chat')
                    else:
                        if new_name in self._artem._names:
                            self._artem._names.remove(new_name)
                        for id in self._artem._dialog_threads:
                            if (new_name in 
                                    self._artem._dialog_threads[id].names):
                                (self._artem._dialog_threads[id]
                                        .names.remove(new_name))
                        need_save = True
                        answer = ('Name \"' + new_name +
                                '\" was removed from Artem global names')

        elif re.match(
                '^/sessions(( local){0,1} (true|false)){0,1}$',
                command):

            if command == '/sessions':
                default_s = ('enabled'
                        if self._artem._default_enabled_session
                        else 'disabled')
                local_s = ('enabled' 
                        if self._artem._dialog_threads[source_id].enabled_session
                        else 'disabled')
                answer = ('Default: Sessions ' + default_s +
                        '\nLocal: Sessions ' + local_s)
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                        ' does not have admin permissions')
            elif command == '/sessions true':
                self._artem._default_enabled_session = True
                for id in self._artem._dialog_threads:
                    self._artem._dialog_threads[id].enabled_session = True
                need_save = True
                answer = 'Sessions are included everywhere'
            elif command == '/sessions local true':
                self._artem._dialog_threads[source_id].enabled_session = True
                need_save = True
                answer = 'Sessions are included in the local chat'
            elif command == '/sessions false':
                self._artem._default_enabled_session = False
                for id in self._artem._dialog_threads:
                    self._artem._dialog_threads[id].enabled_session = False
                need_save = True
                answer = 'Sessions are disabled everywhere'
            else:
                self._artem._dialog_threads[source_id].enabled_session = False
                need_save = True
                answer = 'Sessions are disabled in the local chat'

        elif re.match(
                '^/session_duration(( local){0,1} ([0-9]){1,5}(.([0-9]){1,3}){0,1}){0,1}$',
                command):
                
            if command == '/session_duration':
                answer = ('default session_duration = ' +
                        self._artem._default_session_duration + ' sec\n')
                answer += ('local session_duration = ' +
                        (self._artem._dialog_threads[source_id]
                            .session_duration) + ' sec')
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                        ' does not have admin permissions')
            elif 'local' in command:
                self._artem._dialog_threads[source_id].session_duration = (
                        float(command[24:]))
                need_save = True
                answer = ('session_duration was set on ' +
                        str(self._artem._dialog_threads[source_id]
                            .session_duration) + ' sec in a local chat')
            else:
                new_dur = float(command[18:])
                self._artem._default_session_duration = new_dur
                for id in self._artem._dialog_threads:
                    self._artem._dialog_threads[id].session_duration = new_dur
                need_save = True
                answer = ('session_duration was set on ' +
                        str(new_dur) + ' sec in all chats')

        elif re.match(
                '^/discourse_interval(( local){0,1} ([0-9]){2,6}){0,1}$',
                command):

            if command == '/discourse_interval':
                answer = ('default max_discourse_interval = ' +
                        str(self._artem._default_discourse_interval_max) +
                        ' sec\n')
                answer += ('local max_discourse_interval = ' +
                        str(self._artem._dialog_threads[source_id]
                            .discourse_interval_max) + ' sec')
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                        ' does not have admin permissions')
            elif 'local' in command:
                (self._artem._dialog_threads[source_id]
                        .discourse_interval_max) = float(command[26:])
                need_save = True
                answer = ('max_discourse_interval was set on ' +
                        str(self._artem._dialog_threads[source_id]
                            .discourse_interval_max) + 
                        ' sec in a local chat')
            else:
                new_dur = float(command[20:])
                self._artem._default_discourse_interval_max = new_dur
                for id in self._artem._dialog_threads:
                    self._artem._dialog_threads[id].discourse_interval_max = (
                            new_dur)
                need_save = True
                answer = ('max_discourse_interval was set on ' +
                        str(new_dur) + ' sec in all chats')
        elif re.match(
                '^/events( ([a-z]){4,15}){0,1}$',
                command):

            if command == '/events':
                for event in Event:
                    answer += (event.name + ': ' +
                            str(len(self._artem._lib[event])) + ', ')
                answer = answer[0:len(answer)-2]
            else:
                evt_name = command[8:].upper()
                evt = Event[evt_name]
                if evt:
                    answer = (evt.name + ' scenarios:\n' +
                        '  \n'.join(p.scn_type.__name__ 
                                    for p in self._artem._lib[evt]))
                else:
                    answer = ('Invalid event name: \"' +
                            evt_name + '\"(See /events)')

        elif re.match(
                '^/scenario( (on|off)( local){0,1}){0,1} ([a-z]){4,15} ([_a-zа-я0-9]){1,20}$',
                command):

            spl = command.split(' ')
            evt_name = spl[len(spl)-2].upper()
            evt = Event[evt_name]
            if not evt:
                answer = ('Invalid event name: \"' +
                        evt_name + '\"(See /events)')
            scn_name = spl[len(spl)-1]
            if not self._artem._lib.exists(evt, scn_name):
                answer = ('Event \"' + evt_name + '\" does not contain ' +
                        'a scenario with name \"' + scn_name + '\"')
            elif 'on' not in command and 'off' not in command:
                answer = ('Default status: ' + 
                        self._artem._lib.get_status(evt, scn_name))
                answer += ('\nLocal status: ' + 
                        self._artem._dialog_threads[source_id]
                            .lib.get_status(evt, scn_name))
            elif user_id not in self._artem._admins:
                answer = ('User ' + str(user_id) +
                        ' does not have admin permissions')
            elif 'local' in command:
                current_status = (self._artem._dialog_threads[source_id]
                        .lib.get_status(evt, scn_name))
                if 'on' in command:
                    if current_status == 'on':
                        answer = ('Scenario \"' + scn_name +
                                '\" is already activated in a local chat')
                    else:
                        (self._artem._dialog_threads[source_id]
                                .lib.set_status(evt, scn_name, 'on'))
                        need_save = True
                        answer = ('Scenario \"' + scn_name +
                                '\" now activated in a local chat')
                else:
                    if current_status == 'off':
                        answer = ('Scenario \"' + scn_name +
                                '\" is already deactivated in a local chat')
                    else:
                        (self._artem._dialog_threads[source_id]
                                .lib.set_status(evt, scn_name, 'off'))
                        (self._artem._dialog_threads[source_id]
                                .stop_scenario(evt, scn_name))
                        need_save = True
                        answer = ('Scenario \"' + scn_name +
                                '\" now deactivated in a local chat')
            else:
                new_status = 'on' if 'on' in command else 'off'
                self._artem._lib.set_status(evt, scn_name, new_status)
                for id in self._artem._dialog_threads:
                    (self._artem._dialog_threads[id].lib
                            .set_status(evt, scn_name, new_status))
                    if new_status == 'off':
                        (self._artem._dialog_threads[id]
                                .stop_scenario(evt, scn_name))
                need_save = True
                if new_status == 'on':
                    answer = ('Scenario \"' + scn_name +
                            '\" is activated in all chats')
                else:
                    answer = ('Scenario \"' + scn_name +
                            '\" is deactivated in all chats')

        else:
            answer = 'Unknown commands or incorrect syntaxis'

        return need_save, answer
