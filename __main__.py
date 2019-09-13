from __future__ import annotations

import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from core import GUI
from utils import get_logger


def main():
    log = get_logger('Webber')
    log.info('Webber has been started...')

    log.info('Checking working directory...')

    if os.getcwd().lower() == r'c:\windows\system32'.lower():  # Bit of a hack, but if you have this, your fault
        log.info('Working directory is system32!')

        # Check if running as script, or executable.
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(__file__)
        os.chdir(os.path.realpath(application_path))

        log.info(f'Working directory is set to {application_path}')
    else:
        log.info('Working directory is ok')

    app = QApplication(sys.argv)
    log.info('Starting GUI...')
    program = GUI(r'D:\Clips')
    exit_code = app.exec()
    log.info(f'Exiting with exit code {exit_code}')
    exit(exit_code)


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    main()
