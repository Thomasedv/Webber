import logging
import sys
from copy import deepcopy
import json
import os
import sys
from functools import wraps, partial

from PyQt5.QtCore import QThreadPool, QTimer, Qt, QRunnable

LOG_FILE = 'Webber.log'

log = logging.getLogger('Webber')
log.setLevel(logging.DEBUG)

formatter = logging.Formatter('{name:<15}:{levelname:<7}: {message}', style="{")

filehandler = logging.FileHandler(LOG_FILE, encoding='utf-8')
filehandler.setFormatter(formatter)
filehandler.setLevel(logging.DEBUG)
log.addHandler(filehandler)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
log.addHandler(ch)


def get_logger(string):
    return logging.getLogger(string)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


# If not frozen as .exe, crashes show here
if not getattr(sys, 'frozen', False):
    sys.excepthook = except_hook


class Task(QRunnable):
    def __init__(self, func, *args):
        super(Task, self).__init__()
        self.fn = func
        self.args = args

    def run(self):
        self.fn(*self.args)


def threaded_cooldown(func):
    """ A decorator that makes it so the decorate function will run
     in a thread, but prevents the same function from being rerun for a given time.
     After give time, the last call not performed will be executed.

     Purpose of this is to ensure writing to disc does not happen all too often,
     avoid IO operations reducing GUI smoothness.

     A drawback is that if a user "queues" a save, but reloads the file before the last save,
     they will load a version that is not up to date. This is not a problem for Grabber, as the
     settings are only read on startup. However, it's a drawback that prevents a more general use.

     This decorator requires being used in an instance which has a threadpool instance.
     """

    timer = QTimer()
    timer.setInterval(5000)
    timer.setSingleShot(True)
    timer.setTimerType(Qt.VeryCoarseTimer)

    @wraps(func)
    def wrapper(self, *args, **kwargs):

        if not hasattr(self, 'threadpool'):
            raise AttributeError(f'{self.__class__.__name__} instance does not have a threadpool attribute.')

        if not hasattr(self, 'force_save'):
            raise AttributeError(f'{self.__class__.__name__} instance does not have a force_save attribute.')

        worker = Task(func, self, *args, **kwargs)

        if timer.receivers(timer.timeout):
            timer.disconnect()

        if self.force_save:
            timer.stop()
            self.threadpool.start(worker)
            self.threadpool.waitForDone()
            return

        if timer.isActive():
            timer.timeout.connect(partial(self.threadpool.start, worker))
            timer.start()
            return

        timer.start()
        self.threadpool.start(worker)
        return

    return wrapper


def color_text(text: str, color: str = 'darkorange', weight: str = 'bold', sections: tuple = None) -> str:
    """
    Formats a piece of string to be colored/bolded.
    Also supports having a section of the string colored.
    """
    text = text.replace('\n', '<br>')

    if not sections:
        string = ''.join(['<span style=\"color:', color,
                          '; font-weight:', weight,
                          """;\" >""", text,
                          "</span>"]
                         )
    else:
        work_text = text[sections[0]:sections[1]]
        string = ''.join([text[:sections[0]],
                          '<span style=\"color:', color,
                          '; font-weight:', weight,
                          """;\" >""", work_text,
                          "</span>",
                          text[sections[1]:]]
                         )
    return string


class FileHandler:
    """
    A class to handle finding/loading/saving to files. So, IO operations.
    """

    # TODO: Implement logging, since returned values from threaded functions are discarded.
    # Need to know if errors happen!

    def __init__(self, settings='settings.json'):
        self.settings_path = settings
        self.work_dir = os.getcwd().replace('\\', '/')

        self.force_save = False
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)

    @threaded_cooldown
    def save_settings(self, settings):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=4, sort_keys=True)
                return True
        except (OSError, IOError) as e:
            # TODO: Logging!
            return False

    def load_settings(self, reset=False):
        """ Reads settings, or writes them if absent, or if instructed to using reset. """

        def get_file(path):
            """  """
            if FileHandler.is_file(path):
                with open(path, 'r') as f:
                    return json.load(f)
            else:
                return {}

        if reset:
            return get_base_settings()

        else:
            settings = get_file(self.settings_path)
            if settings:
                return settings
            else:
                return self.load_settings(reset=True)

    @staticmethod
    def is_file(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)


base_settings = {
    'destination': None
}


def get_base_settings():
    return deepcopy(base_settings)
