import random

DEFAULT_MAX_REPLICAS = 5
DEFAULT_MAX_IDLE_TIME = 20
DEFAULT_WITH_ALL_MODE = False
DEFAULT_DESCRIPTION = 'Scenario without description'

class Scenario(object):
    """[summary]
    
    Attributes
    ----------
    description : str
        Scenario description that can be viewed from CLI commands.
        Fill by creator.
        By default {DEFAULT_DESCRIPTION}.
    max_replicas : int
        The maximum number of replicas that can be processed by a single instance of this scenario.
        Fill by creator.
        By default {DEFAULT_MAX_REPLICAS}.
    max_idle_time : int
        The maximum lifetime for this scenario instance between his invocations.
        When this time is expired the instance will be destroyed.
        Fill by creator.
        By default {DEFAULT_MAX_IDLE_TIME}.
    with_all : bool
        Only an initiator of the scenario, or any chat interlocutor can interact with the running scenario.
        Fill by creator.
        By default {DEFAULT_WITH_ALL_MODE}.

    interlocutors : list of `artem.others.Interlocutor`
        List of chat members, represented by the special Interlocutor classes.
        Auto fill.
    messages_history : list of str
        Llist of all previous messages to the current instance of this scenario.
        Auto fill.
    names : list of str
        List of names that are acceptable for a direct invocation of the bot.
        Auto fill.

    message : str
        Text of the incoming message (if presented in event).
        Auto fill.
    i_sender : `artem.others.Interlocutor`
        Interlocutor from interlocutors list who send the message.
        Auto fill.
    is_personal : bool
        The message is considered personal if it comes from personal chat, or
        sender wrote the name from list of bot names in the message prefix
        Auto fill.
    answer : str
        Only for "POSTPOC" scenarios. Answer that comes from the main scenario (handler).
        Auto fill
    answers_left : int
        Only for "POSTPROC" scenarios. The main scenario can generate multiple answers for
        single message. And this property indicates how many answers will be further
        processed for the current message.
        Auto fill.
    """

    # Override in derived classes
    description = DEFAULT_DESCRIPTION
    max_replicas = DEFAULT_MAX_REPLICAS
    max_idle_time = DEFAULT_MAX_IDLE_TIME
    with_all = DEFAULT_WITH_ALL_MODE

    # Consistent values for all invocation of the running scenario (instance)
    interlocutors = None
    messages_history = None
    names = None

    # New values in every invocation
    message = None
    i_sender = None
    is_personal = None
    answer = None
    answers_left = 0
        
    # return boolean
    @staticmethod
    def suitable(message, i_sender, interlocutors, is_personal, name, answer):
        return True

    # function(self, message)
    # return answers [{message: 'str', sleep: 1.0, attach: 'photo'}]
    respond = lambda self: ['Тест сценария ' + self.__class__.__name__]

    def __init__(self, interlocutors, names):
        self.messages_history = []
        self.interlocutors = interlocutors
        self.names = names
        self.replic_count = 0

    def update_env(self, message, i_sender, is_personal=True, answer=None):
        self.message = message
        self.i_sender = i_sender
        self.is_personal = is_personal
        self.answer = answer

def m(text, sleep=0.0, attach=None, sticker=None):
    if sleep == 0.0:
        sleep = 1.0 + 4 * round(random.random(), 3)
    return {'message': text, 'sleep': sleep,
            'attach': attach, 'sticker' : sticker}    

def find_element(enumerate_, predicate):
    ret_value = None
    for item in enumerate_:
        if predicate(item):
            ret_value = item
            break
    return ret_value

def remove_name(message, name):
    if not message or not name:
        return None
    message = message.replace(name, '', 1)
    if len(message) != 0:
        message = message.lstrip()
        if message[0] == ',' or message[0] == '.' or message == '!':
            message = message[1:len(message)]
        message = message.lstrip()
    return message
