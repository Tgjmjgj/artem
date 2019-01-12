
from .cmd import Control, CommandType, AdminClass, ArgType, ArgRole
from .version import VERSION, RELEASE

class Commands:

    def execute(self, message, some_id, admin):
        return self._cmd.execute(message, some_id, admin)

    def __init__(self, artem):
        self._cmd = Control()
        self._cmd.add('version', 'Information about Artem version'
            ).action(
                CommandType.INFO, 
                AdminClass.NONE, 
                [],
                lambda some_id:
                    'ArtemCore v' + VERSION + '\nRelease: ' + RELEASE
            )
        self._cmd.add('scenario', 'Enable or disable a specific scenario'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.FUNC_ARG],
                 [ArgType.WORD, ArgRole.FUNC_ARG]],
                lambda some_id, *args: 
                    ('Local scenario status: ' + 
                    ('ON' if artem._dialog_threads[some_id].lib.get_status(args[0], args[1])
                          else 'OFF'))
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.FUNC_ARG],
                 [ArgType.WORD, ArgRole.FUNC_ARG]],
                lambda *args:
                    ('Global scenario status: ' + 
                    ('ON' if artem._lib.get_status(args[0], args[1]) else 'OFF')),
                glob=True
            ).action(
                CommandType.ON_OFF,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.ARG],
                 [ArgType.WORD, ArgRole.ARG],
                 [ArgType.ON_OFF, ArgRole.ARG]],
                lambda some_id:
                    artem._dialog_threads[some_id].lib.set_status
            ).action(
                CommandType.ON_OFF,
                AdminClass.GLOBAL,
                [[ArgType.WORD, ArgRole.ARG],
                 [ArgType.WORD, ArgRole.ARG],
                 [ArgType.ON_OFF, ArgRole.ARG]],
                lambda:
                    artem._lib.set_status,
                glob=True
            )
        self._cmd.add('polling_interval',
            'Get or set time between secondary polling (all except messages)'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Secondary polling interval = ' +
                        str(artem._secondary_polling_interval.val) + ' sec')
            ).action(
                CommandType.SET,
                AdminClass.GLOBAL,
                [[ArgType.FLOAT, ArgRole.VALUE]],
                lambda some_id:
                    artem._secondary_polling_interval
            )
        self._cmd.add('admins',
            'Information and administration of a group of admins'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Local admins: ' + ', '.join(
                        [str(a) for a in artem._dialog_threads[some_id].local_admins]))
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda:
                    ('Global admins: ' + ', '.join(
                        [str(a) for a in artem._global_admins])),
                glob=True
            ).action(
                CommandType.ADD_DEL,
                AdminClass.LOCAL,
                [[ArgType.INTEGER, ArgRole.APPEND]],
                lambda some_id:
                    artem._dialog_threads[some_id].local_admins
            ).action(
                CommandType.ADD_DEL,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.APPEND]],
                lambda:
                    artem._global_admins,
                glob=True
            )
        self._cmd.add('names',
            'Information and administration of Artem respond names'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Artem local names: ' + ', '.join(
                        [str(a) for a in artem._dialog_threads[some_id].local_names]))
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda:
                    ('Artem global names: ' + ', '.join(
                        [str(a) for a in artem._global_names])),
                glob=True
            ).action(
                CommandType.ADD_DEL,
                AdminClass.LOCAL,
                [[ArgType.STRING, ArgRole.APPEND]],
                lambda some_id:
                    artem._dialog_threads[some_id].local_names
            ).action(
                CommandType.ADD_DEL,
                AdminClass.GLOBAL,
                [[ArgType.STRING, ArgRole.APPEND]],
                lambda:
                    artem._global_names,
                glob=True
            )
        self._cmd.add('sessions', 'Enabled or disabled sessions'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    'Sessions ' + ('enabled'
                        if artem._dialog_threads[some_id].enabled_session.val
                        else 'disabled') +' in local chat'
            ).action(
                CommandType.ON_OFF,
                AdminClass.LOCAL,
                [[ArgType.ON_OFF, ArgRole.VALUE]],
                lambda some_id:
                    artem._dialog_threads[some_id].enabled_session
            )
        self._cmd.add('session_duration', 'Get or set duration of session'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Session duration = ' +
                        str(artem._dialog_threads[some_id].session_duration.val) + ' sec')
            ).action(
                CommandType.SET,
                AdminClass.GLOBAL,
                [[ArgType.FLOAT, ArgRole.VALUE]],
                lambda some_id:
                    artem._dialog_threads[some_id].session_duration
            )
        self._cmd.add('events',
            'Get information about event types and their scenarios'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [],
                lambda some_id:
                    ', '.join([(e.name + ': ' + str(len(artem._lib[e])))
                            for e in Event])
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.WORD, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    args[0].upper() + ' scenarios:\n' +
                        '\n'.join(p.scn_type.__name__
                                  for p in artem._lib[args[0]])
            )
        self._cmd.add('info',
            'Get description and information about existing scenarios'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    '\n'.join(
                        [str(i) + '.------[' + str(scen.scn_type.description) + ']'
                            for i, scen in enumerate(
                                reduce(lambda x, y: x + y, artem._lib)
                        )]
                    )
            )
        self._cmd.add('dialogs',
            'Provide information about Artem\'s dialogs'
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [],
                lambda some_id:
                    'Chats with Artem: ' + ', '.join(
                        str(id_) for id_ in artem._dialog_threads)
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    ('Interlocutors of dialog ' + str(args[0]) + ':\n' +
                        '\n'.join(
                            (str(i.id) + ' - ' + i.first_name + ' ' + i.last_name)
                            for i in artem._dialog_threads[args[0]][0].interlocutors
                        )
                    )
            )
        self._cmd.add('id', 'Get id of current Artem account'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [],
                lambda some_id:
                    'ID of current Artem:  ' + str(artem._id)
            )
        self._cmd.add('sendto', 'Forcing a message to the specified id'
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.FUNC_ARG],
                 [ArgType.MESSAGE, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    artem._send_queue.put(ToSend(
                        args[0], args[1][0].upper() + args[1][1:], 2.0))
            )
        self._cmd.add('stop', 'Stop responding to incoming messages'
            ).action(
                CommandType.CALL,
                AdminClass.LOCAL,
                [],
                lambda some_id:
                    artem._stop_artem(some_id)
            ).action(
                CommandType.CALL,
                AdminClass.GLOBAL,
                [],
                artem._stop_artem,
                glob=True
            )
        self._cmd.add('resume', 'Resume responding of incoming messages'
            ).action(
                CommandType.CALL,
                AdminClass.LOCAL,
                [],
                lambda some_id:
                    artem._resume_artem(some_id)
            ).action(
                CommandType.CALL,
                AdminClass.GLOBAL,
                [],
                artem._resume_artem,
                glob=True
            )
        self._cmd.add('sleep', 'Stop Artem for a while'
            ).action(
                CommandType.INFO,
                AdminClass.LOCAL,
                [[ArgType.INTEGER, ArgRole.FUNC_ARG]],
                lambda some_id, *args:
                    artem._sleep_artem(args[0], some_id)
            ).action(
                CommandType.INFO,
                AdminClass.GLOBAL,
                [[ArgType.INTEGER, ArgRole.FUNC_ARG]],
                artem._sleep_artem,
                glob=True
            )
        self._cmd.add('status', 'Information on the health of Artem'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                lambda some_id:
                    ('Local status: ' + 
                    ('RUNNING' if artem._dialog_threads[some_id].isEnabled()
                        else 'SUSPENDED') +
                    '\nGlobal status: ' +
                    ('RUNNING' if artem._run else 'SUSPENDED'))
            )
        self._cmd.add('new', 'Last release features'
            ).action(
                CommandType.INFO,
                AdminClass.NONE,
                [],
                """
1. TIME, IDLE and SILENCE events have been added.
2. Scenario API changed, required function parameters removed.
                """
            )