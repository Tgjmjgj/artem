import re
import enum
import types
import traceback

from . import artem_core
from .scenario import find_element

class CommandType(enum.Enum):
    INFO = 1
    ADD_DEL = 2
    ON_OFF = 3
    SET = 4

class ArgType(enum.Enum):
    WORD = 1
    WORDS = 2
    INTEGER = 3
    FLOAT = 4
    STRING = 5
    ON_OFF = 6
    MESSAGE = 7

class ArgRole(enum.Enum):
    VALUE = 1
    KEY = 2
    ARG = 3
    APPEND = 4
    FUNC_ARG = 5

class AdminClass(enum.Enum):
    NONE = 1
    LOCAL = 2
    GLOBAL = 3

class Control(object):

    class Command(object):

        class Action(object):

            command_pattern = {
                CommandType.INFO: '',
                CommandType.ADD_DEL: ' (add|del)',
                CommandType.ON_OFF: ' (on|off)',
                CommandType.SET: ' set'
            }

            arg_pattern = {
                ArgType.WORD: ' ([_a-zа-я]){1,20}',
                ArgType.WORDS: ' ([_ a-zа-я](?!global)){1,40}',
                ArgType.INTEGER: ' ([0-9]){1,10}',
                ArgType.FLOAT: ' ([0-9]){1,5}(.([0-9]){1,10}){0,1}',
                ArgType.STRING: ' ([_ a-zа-я0-9](?!global)){1,20}',
                ArgType.ON_OFF: '',
                ArgType.MESSAGE: '.+'
            }

            def __init__(self, command, cmd_type, need_admin, args, func, glob):
                self._command = command
                self._cmd_type = cmd_type
                self._need_admin = need_admin
                self._args = args
                self._func = func
                self._glob = glob
                self._create_pattern()

            def _create_pattern(self):
                self.pattern = '^/' + self._command
                self.pattern += self.command_pattern[self._cmd_type]
                self.help = self.pattern[1:]
                for arg in self._args:
                    self.pattern += self.arg_pattern[arg[0]]
                    if arg[0] != ArgType.ON_OFF:
                        self.help += ' ' + arg[0].name
                if self._glob:
                    self.pattern += ' global'
                    self.help += ' global'
                if self._cmd_type != (ArgType.WORDS and ArgType.STRING):
                    self.pattern += '$'

            @property
            def pattern(self):
                return self._pattern
                
            @pattern.setter
            def pattern(self, value):
                self._pattern = value

            def Do(self, cmd, some_id, admin):
                if (self._need_admin == AdminClass.GLOBAL and
                        admin != AdminClass.GLOBAL):
                    answer = ('To allow this command you need global admin ' +
                        'privileges')
                    return answer, False
                elif (self._need_admin == AdminClass.LOCAL and
                        admin == AdminClass.NONE):
                    answer = 'To allow this command you need admin privileges'
                    return answer, False
                else:
                    args_val = []
                    l = len(self._command)
                    if self._cmd_type == CommandType.INFO:
                        begin = l + 1
                        subcmd = None
                    else:
                        subcmd = cmd[l + 2 : l + 5]
                    if self._cmd_type == CommandType.ADD_DEL:
                        begin = l + 5
                    elif self._cmd_type == CommandType.ON_OFF:
                        begin = l + (4 if cmd[l + 2 : l + 4] == 'on' else 5)
                    elif self._cmd_type == CommandType.SET:
                        begin = l + 5
                        
                    for arg in self._args:
                        if arg[0] != ArgType.ON_OFF:
                            cmd = cmd[begin:]
                            if cmd.startswith(' global'):
                                break
                            reg = re.match(self.arg_pattern[arg[0]], cmd)
                            beg = reg.regs[0][0]
                            val = cmd[beg : beg + reg.regs[0][1]]
                            begin = len(val)
                            val = val[1:]
                            if arg[0] == ArgType.FLOAT:
                                val = float(val)
                            elif arg[0] == ArgType.INTEGER:
                                val = int(val)
                            args_val.append([val, arg[1]])
                        else:
                            args_val.append([
                                    True if subcmd[0:2] == 'on' else False,
                                    arg[1]
                                ])
                    res = None
                    func_args = [
                        a[0] for a in args_val if a[1] == ArgRole.FUNC_ARG
                        ]
                    try:
                        if self._glob:
                            if func_args:
                                res = self._func(*func_args)
                            elif isinstance(self._func, types.FunctionType):
                                res = self._func()
                            else:
                                res = self._func
                        else:
                            if func_args:
                                res = self._func(some_id, *func_args)
                            elif isinstance(self._func, types.FunctionType):
                                res = self._func(some_id)
                            else:
                                res = self._func
                    except Exception:
                        print(traceback.format_exc())
                        return 'Wrond arguments or lambda expression', False

                    if self._cmd_type == CommandType.INFO:
                        save = False
                    else:
                        save = True
                    try:
                        fargs = []
                        for i in range(0, len(args_val)):
                            if args_val[i][1] == ArgRole.ARG:
                                fargs.append(args_val[i][0])
                                if i != len(args_val) - 1:
                                    if args_val[i + 1][1] != ArgRole.ARG:
                                        res = res(*fargs)
                                else:
                                    res = res(*fargs)
                            elif args_val[i][1] == ArgRole.KEY:
                                if i != len(args_val) - 1:
                                    if args_val[i + 1][1] == ArgRole.VALUE:
                                        res[args_val[i][0]] = args_val[i+1][0]
                                        break
                                res = res[args_val[i][0]]
                            elif args_val[i][1] == ArgRole.VALUE:
                                res.val = args_val[i][0]
                                break
                            elif args_val[i][1] == ArgRole.APPEND:
                                have = (True if find_element(
                                        res, lambda n: n == args_val[i][0])
                                    else False)
                                if not have and subcmd == 'add':
                                    res.append(args_val[i][0])
                                elif have and subcmd == 'del':
                                    res.remove(args_val[i][0])
                                elif not have and subcmd == 'del':
                                    return (args_val[i][0] +
                                    ' is not in the list'), False
                                else:
                                    return (args_val[i][0] +
                                    ' already in the list'), False
                                break
                    except Exception:
                        return 'Wrong arguments', False
                    else:
                        if self._cmd_type == CommandType.INFO and res:
                            return res, save
                        else:
                            return 'Success', save


        def __init__(self, command_name, help_):
            self.command = command_name
            self.description = help_
            self._actions = []

        def action(self, cmd_type, need_admin, args, func, glob=False):


            self._actions.append(Control.Command.Action(
                    self.command, cmd_type, need_admin, args, func, glob))
            return self

        def execute(self, command_string, some_id, admin):
            for act in self._actions:
                if re.match(act.pattern, command_string):
                    return act.Do(command_string, some_id, admin)
            return 'Incorrect syntaxis', False

        def get_help(self):
            return [act.help for act in self._actions]


    def __init__(self):
        self._commands = []

    def add(self, command_name, help_):
        new_cmd = Control.Command(command_name, help_)
        self._commands.append(new_cmd)
        return new_cmd

    def execute(self, command_string, some_id, admin):

        if command_string == '/help':
            hlp = ['/' + c.command + '\n' + c.description for c in self._commands]
            hlp.append('/help (command)\nGet help')
            hlp.sort()
            return '\n\n'.join(hlp), False
        elif re.match('^/help ([_a-zа-я]){1,20}$', command_string):
            cmd = find_element(
                    self._commands,
                    lambda c: c.command == command_string[6:]
                )
            if cmd:
                hlp = cmd.description + ':\n\n'
                hlp += '\n'.join(cmd.get_help())
                return hlp, False

        if ' ' in command_string:
            for index in range(1, len(command_string)):
                if command_string[index] == ' ':
                    break
            command_name = command_string[1:index]
        else:
            command_name = command_string[1:]
        cmd = find_element(self._commands, 
                           lambda cmd: cmd.command == command_name)
        if cmd:
            answer, save = cmd.execute(command_string, some_id, admin)
        else:
            answer, save = 'Unknown command', False
        return answer, save

