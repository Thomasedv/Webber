import json
import logging
import os

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
