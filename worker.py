import time
import traceback
import math
from collections import deque
from functools import partial

import subprocess
import re

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from utils import get_logger

progress_pattern = re.compile(
    r'(frame|fps|size|time|bitrate|speed)\s*\=\s*(\S+)'
)


class Conversion(QThread):
    process_output = pyqtSignal(str)
    done = pyqtSignal(int)

    def __init__(self, commands: list, target_name, file_name, duration):
        super(Conversion, self).__init__()

        self.name = target_name
        self.file_name = file_name
        self.dur = duration
        self._log = get_logger('Webber.Convert')
        self._log.info(f'Instanciated with target file {self.name}')
        self.queue = deque(commands)
        try:
            idx = self.queue[0].index('-b:v') + 1
        except Exception:
            idx = 0

        self.bitrate = self.queue[0][idx] if idx else None
        self.active_prog = None
        self.abort = False
        self.current = None

    def run(self):
        try:
            self._log.info('Fetching process framerate..')
            p = QProcess()
            p.start(
                f'ffprobe "{self.file_name}" -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate')
            p.waitForStarted()
            p.waitForFinished()

            info = p.readAll().data().decode('utf-8', 'replace').strip()
            self._log.debug(f'Given framerate info: {info}')
            try:
                x, y = info.split('/')
                framerate = int(x) / int(y)
            except Exception:
                framerate = float(info)
            self._log.info(f'Found framerate: {framerate:.4f}')
        except Exception:
            self._log.error('Failed to get info!')
            framerate = None

        cur_pass = 1
        workers = []
        while self.queue:
            self.current = commands = self.queue.popleft()
            worker = QProcess()
            workers.append(worker)
            worker.setWorkingDirectory('.')
            worker.setProcessChannelMode(QProcess.MergedChannels)
            worker.readyReadStandardOutput.connect(lambda *_: self.out_stream(worker, cur_pass, framerate))
            worker.start('ffmpeg', commands)
            self._log.info(f'Starting process, pass {cur_pass}')
            worker.waitForStarted()
            while not worker.waitForFinished(500):
                if self.abort:
                    self.queue.clear()
                    worker.kill()
                    self._log.info('Process terminated by user...')
                    self.done.emit(worker.exitCode())
                    return
            cur_pass += 1
            if worker.exitCode():
                self._log.error(f'Process closed with error code {worker.exitCode()}')
                continue
        self.done.emit(worker.exitCode())
        self._log.info('Finished all passes')
        self.current = None

    def out_stream(self, prog, cur_pass, framerate):
        data = prog.readAllStandardOutput().data()
        data: bytes
        text = data.decode('utf-8', 'replace').strip()
        print(text)
        text_list = text.split('\n')

        for i in reversed(text_list):
            items = {
                key: value for key, value in progress_pattern.findall(i)
            }
            if items:
                break
        else:
            return

            # frame=int(items['frame']),
            # fps=float(items['fps']),
            # size=int(items['size'].replace('kB', '')) // 1024,
            # time=items['time'],
            # bitrate=float(items['bitrate'].replace('kbits/s', '')),
            # speed=float(items['speed'].replace('x', '')),
        try:
            if framerate is not None and self.dur:
                percent = int(int(items['frame']) / (framerate * self.dur) * 100)
                percent = 100 if percent > 100 else percent

                output = f'\nWorking...\n' \
                         f'Target name: {self.name}\n' \
                         f'Target bitrate: {self.bitrate + "b" if self.bitrate is not None else "Nan"}\n' \
                         f'Pass: {cur_pass}\n' \
                         f'Progress: {percent}% \n'

                output += f'Frame {items["frame"]} of {math.ceil(framerate * self.dur)}' + '\n' + f'Time: {items["time"]}'

            else:
                output = f'\nWorking...\n' \
                         f'Target name: {self.name}\n' \
                         f'Target bitrate: {self.bitrate + "b" if self.bitrate is not None else "Nan"}\n' \
                         f'Pass: {cur_pass}\n'

        except Exception as e:
            self._log.error(f'Failed formatting with error: {e.with_traceback()}')
            traceback.print_exc()

        else:
            self.process_output.emit(output)
