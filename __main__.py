from __future__ import annotations

import os
import sys

from PyQt5.QtWidgets import QApplication

cwd_was_sys32 = False
if os.getcwd().lower() == r'c:\windows\system32'.lower():  # Bit of a hack, but if you have this, your fault
    cwd_was_sys32 = True
    # Check if running as script, or executable.
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(__file__)
    os.chdir(os.path.realpath(application_path))

from core import GUI
from utils import get_logger


def main():
    log = get_logger('Webber')

    app = QApplication(sys.argv)
    log.info('Starting GUI...')
    program = GUI()

    exit_code = app.exec()

    program = None
    log.info(f'Exiting with exit code {exit_code}')
    return exit_code

# TODO: Require picking a folder
# TODO: Prevent start until all require options are there.


if __name__ == '__main__':
    log = get_logger('Webber')
    log.info('Webber has been started...')

    if cwd_was_sys32:
        log.warning(f'Working dir was system32, changed to {os.getcwd()}')

    exit_code = main()
    sys.exit(exit_code)

