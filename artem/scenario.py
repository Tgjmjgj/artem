import random

class Scenario(object):

    # list of others.interlocutor
    interlocutors = None
    # list of message
    messages_history = None
    # list of Artem names
    names = None

    max_replicas = 5
    max_idle_time = 20
    with_all = False

    message = None
    i_sender = None
    is_personal = None
    answer = None
        
    # return boolean
    @staticmethod
    def suitable(message, i_sender, interlocutors, is_personal, name):
        return True

    # function(self, message)
    # return answers [{message: 'str', sleep: 1.0, attach: 'photo'}]
    respond = lambda self: [u'Тест сценария ' + self.__class__.__name__]

def wrapup(func):
    def wrap(self):
        ret = func()
        self.respond = None
        return ret
    return wrap

def m(text, sleep=0.0, attach=None):
    if sleep == 0.0:
        sleep = 1.0 + 2 * round(random.random(), 3)
    return {'message': text, 'sleep': sleep, 'attach': attach}    

def set_env(scen, interlocutors, names):
    scen.messages_history = []
    scen.interlocutors = interlocutors
    scen.names = names

def update_env(scen, message, i_sender, is_personal=True, answer=None):
    scen.message = message
    scen.i_sender = i_sender
    scen.is_personal = is_personal
    scen.answer = answer

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
        message.lstrip()
        if message[0] == ',' or message[0] == '.' or message == '!':
            message = message[1:len(message)]
        message.lstrip()
    return message
