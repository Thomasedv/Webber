from __future__ import annotations

import json
import logging
import os
import sys
from copy import deepcopy
from functools import wraps, partial
from typing import Tuple

from PyQt5.QtCore import QThreadPool, QTimer, Qt, QRunnable
from PyQt5.QtGui import QColor

LOG_FILE = 'Webber.log'


log = logging.getLogger('Webber')
log.setLevel(logging.DEBUG)

formatter = logging.Formatter('{name:<15}:{levelname:<7}:{lineno:4d}: {message}', style="{")
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


def except_hook(cls, exception, tb):
    import traceback
    log = get_logger('Webber.FATAL')
    log.error(f'Fatal error:\n {traceback.format_exception(cls, exception, tb)}')
    sys.__excepthook__(cls, exception, tb)


# If not frozen as .exe, crashes show here
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
    def wrapper(self, *args):

        if not hasattr(self, 'threadpool'):
            raise AttributeError(f'{self.__class__.__name__} instance does not have a threadpool attribute.')

        if not hasattr(self, 'force_save'):
            raise AttributeError(f'{self.__class__.__name__} instance does not have a force_save attribute.')

        worker = Task(func, self, *args)

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


def color_text(text: str, color: str = 'darkorange', weight: str = 'bold', sections: Tuple[int, int] = None) -> str:
    """
    Formats a piece of string to be colored/bolded.
    Also supports having a just a section of the string colored.
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

    def __init__(self, settings='webber_settings.json'):
        self.settings_path = settings
        self.work_dir = os.getcwd().replace('\\', '/')

        self.force_save = False
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)

    @threaded_cooldown
    def save_settings(self, settings):
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, sort_keys=True)
                return True
        except (OSError, IOError) as e:
            log = get_logger('Webber.FileHandler')
            log.error('Fatal error:\n' + str(e))
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


stylesheet = """
QWidget {{
    background-color: {background_light};
    color: {text_normal};
}}
QMainWindow {{
    background-color: {background_dark};
    color: red;
}}
QMenu::separator {{
    height: 2px;
}}
QFrame#line {{
    color: {background_dark};
}}
QLabel {{
    background: {background_light};
    padding: 2px;
    border-radius: 2px;
    outline: 0;    
}}

QTabWidget::pane {{
    border: none;
}}

QMenu::item {{
    border: none;
    padding: 3px 20px 3px 5px
}}

QMenu {{
    border: 1px solid {background_dark};
}}

QMenu::item:selected {{
    background-color: {background_dark};
}}

QMenu::item:disabled {{
    color: #808080;
}}

QMenuBar::item {{
    border: none;
    padding: 3px 20px 3px 5px
}}

QMenuBar::item:selected {{
    background-color: {background_dark};
}}

QMenuBar::item:disabled {{
    color: #808080;
}}

QTabWidget {{
    background-color: {background_dark};
}}

QTabBar {{
    color: {background_dark};
    background: {background_dark};
}}

QTabBar::tab {{
    color: {text_shaded};
    background-color: {background_lightest};
    border-bottom: none;
    border-left: 1px solid #00000000;
    min-width: 15ex;
    min-height: 7ex;
}}

QTabBar::tab:selected {{
    color: white;
    background-color: {background_light};
}}
QTabBar::tab:!selected {{
    margin-top: 6px;
    background-color: {background_lightest}
}}

QTabWidget::tab-bar {{
    border-top: 1px solid {background_dark};
}}

QLineEdit {{
    background-color: {background_dark};
    color: {text_shaded};
    border-radius: 0px;
    padding: 0 3px;
}}

QLineEdit:disabled {{
    background-color: {background_dark};
    color: #505050;
    border-radius: none;
}}

QTextEdit {{
    background-color: {background_light};
    color: {text_shaded};
    border: red solid 1px;
}}

QTextEdit#TextFileEdit {{
    background-color: {background_dark};
    color: {text_shaded};
    border: red solid 1px;
    border-radius: 2px;
}}

QListWidget {{
    outline: none;
    outline-width: 0px;
    background: {background_dark};
    border: 1px solid {background_dark};
    border-radius: 2px;
}}

QScrollBar::vertical {{
    border: none;
    background-color: transparent;
    width: 10px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::vertical#main {{
    background-color: {background_dark};
}}
QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {{
    border: none;
    background: none;
    width: 0px;
    height: 0px;
}}

QScrollBar::handle:vertical {{
    background: {background_dark};
    min-height: 20px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical#main {{
    background: {background_darkest};
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical  {{
    background: none;
}}

QPushButton {{
    background-color: {background_dark};
    color: white;
    border: 1px solid transparent;
    border-radius: none;
    width: 60px;
    height: 20px;
}}

QPushButton:disabled {{
    border: 1px solid {background_dark};
    background-color: transparent;
    color: #757575;
}}

QPushButton:pressed {{
    background-color: #101010;
    color: white;
}}

QTreeWidget {{
    selection-color: red;
    border: none;
    outline: none;
    outline-width: 0px;
    selection-background-color: blue;
}}      

QTreeWidget::item {{
    height: 16px;
}}

QTreeWidget::item:disabled {{
    color: grey;
}}

QTreeWidget::item:hover, QTreeWidget::item:selected {{
    background-color: transparent;
    color: white;
}}

QComboBox {{
    border: 1px solid {background_dark};
    border-radius: 0px;
    background-color: {background_dark};
    color: {text_shaded};
    padding-right: 5px;
    padding-left: 5px;
}}


QComboBox::drop-down {{
    border: 0px;
    background: none;
}}                        

QComboBox::disabled {{
    color: {background_light};
}}

QCheckBox::disabled {{
    color: {text_shaded};
}}


"""


def is_file(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)


def find_file(relative_path, exist=True):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    path = os.path.join(base_path, relative_path).replace('\\', '/')

    if FileHandler.is_file(path) or not exist:
        return path
    else:
        return None


def darken(color: QColor):
    return color.darker(150)


def lighten(color: QColor):
    return color.lighter(150)


surface = QColor('#484848')
text = QColor('white')

default_style = {'background_light': surface,
                 'background_dark': darken(surface),
                 'background_darkest': darken(darken(surface)),
                 'background_lightest': lighten(surface),
                 'text_shaded': darken(text),
                 'text_normal': text}


def qcolorToStr(color_map: dict):
    return {k: v.name(QColor.HexRgb) for k, v in color_map.items()}


def get_stylesheet(**kwargs):
    global default_style
    styles = default_style.copy()
    styles.update(kwargs)
    return stylesheet.format(**qcolorToStr(styles))
