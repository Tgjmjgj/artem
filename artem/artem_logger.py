import os
import sys
import logging
import datetime
import logging.handlers

from .version import VERSION

ERROR_LOG_FILE = (('log\\' if sys.platform == 'win32' else 'log/') +
    'artem_' + VERSION + '_' + datetime.datetime.now().strftime('%m.%d.%Y_%I.%M%p') + '.log')
    
if not os.path.exists('log'):
    os.makedirs('log')

class ArtemLogger:

    def __init__(self):
        self._logger = logging.getLogger()
        self._logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
                ERROR_LOG_FILE, maxBytes=1048576, backupCount=2)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def log(self, message):
        self._logger.error(message)

        