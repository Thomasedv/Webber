import os
import traceback
from collections import deque

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent
from PyQt5.QtWidgets import *

from player_widget import VideoWindow
from utils import get_logger, color_text, FileHandler
from worker import Conversion


class GUI(QMainWindow):
    def __init__(self):
        super(GUI, self).__init__()

        # Internal variables

        # TODO: Make settings file, get path from settings
        self._debug = False
        self._active_prog = None
        self._resolution = None
        self._queue = deque()
        self._log = get_logger('Webber.MainWindow')
        self._fh = FileHandler()
        self._settings = self._fh.load_settings()
        self.validate_settings()

        self.toggle_debug = QShortcut(QKeySequence('Ctrl+P'), self)
        self.toggle_debug.activated.connect(self.debug_switch)

        self.worker = QThreadPool(self)
        self.worker.setMaxThreadCount(1)

        # GUI setup

        self.current_file = QLineEdit('')
        self.current_file.setReadOnly(True)

        self.setAcceptDrops(True)
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setFocusPolicy(Qt.NoFocus)

        self.out_name = QLineEdit()
        self.start_time = QLineEdit('00:00.00')
        self.end_time = QLineEdit()

        self.bitrate = QLineEdit('8')
        self.playback_rate = QLineEdit('1.0')

        self.sound = QCheckBox('Sound')
        self.sound.setLayoutDirection(Qt.RightToLeft)

        self.trim = QCheckBox('Split')
        self.trim.setToolTip('Splits video into 3 parts using start/end\nDoes not re-encode if video is not cropped')
        self.trim.setLayoutDirection(Qt.RightToLeft)
        self.trim.stateChanged.connect(self._disable)

        self.cut = QCheckBox('Cut')
        self.cut.setToolTip('Cuts video at start/end mark.\nDoes not re-encode if video is not cropped')
        self.cut.setLayoutDirection(Qt.RightToLeft)
        self.cut.stateChanged.connect(self._disable)

        self.startbtn = QPushButton('Convert')
        self.startbtn.clicked.connect(self.start)
        self.startbtn.clicked.connect(self.start_button_timer)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.startbtn.setDisabled(False))

        self.cancelbtn = QPushButton('Cancel')
        self.cancelbtn.clicked.connect(self.stop)
        self.cancelbtn.setDisabled(True)

        self.mediaplayer = VideoWindow(self)
        self.mediaplayer.setFocusPolicy(Qt.NoFocus)
        self.mediaplayer.trim_btn.clicked.connect(self.get_start)
        self.mediaplayer.trim2_btn.clicked.connect(self.get_end)

        self.mediaplayer.mediaPlayer.setNotifyInterval(100)
        self.mediaplayer.mediaPlayer.positionChanged.connect(self.update_timestamp)

        self.filetype = QComboBox()
        # TODO include more filetypes here!
        self.filetype.addItems(['webm', 'mp4'])

        self.layout = QGridLayout()
        self.layout.addWidget(self.current_file, 0, 0, 1, 3)
        self.layout.addWidget(self.textbox, 1, 0, 1, 3)
        self.layout.addWidget(QLabel('Length mul.'))
        self.layout.addWidget(self.playback_rate, 2, 1, 1, 1)

        self.layout.addWidget(self.trim, 2, 2, 1, 1)

        self.layout.addWidget(QLabel('Target Name:'), 3, 0, 1, 1)
        self.layout.addWidget(self.out_name, 3, 1, 1, 1)
        self.layout.addWidget(self.filetype, 3, 2, 1, 1)

        self.layout.addWidget(QLabel('Start time:'))
        self.layout.addWidget(self.start_time, 4, 1, 1, 2)
        self.layout.addWidget(QLabel('End time:'))
        self.layout.addWidget(self.end_time, 5, 1, 1, 2)
        self.layout.addWidget(QLabel('Size MB:'))
        self.layout.addWidget(self.bitrate, 6, 1, 1, 1)
        self.layout.addWidget(self.cut, 6, 2, 1, 1)

        self.layout.addWidget(self.sound, 7, 0, Qt.AlignRight)
        self.layout.addWidget(self.startbtn, 7, 1, 1, 1)
        self.layout.addWidget(self.cancelbtn, 7, 2, 1, 1)
        self.layout.setColumnStretch(0, 0)
        self.layout.setColumnStretch(1, 0)
        self.layout.setColumnStretch(2, 0)
        self.layout.setColumnStretch(3, 2)
        self.layout.addWidget(self.mediaplayer, 0, 3, 7, 4)

        self.w = QWidget(self)
        self.setCentralWidget(self.w)
        self.w.setLayout(self.layout)

        self.setWindowTitle('Webber')
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)

        self.showMaximized()

    def validate_settings(self):
        if self._settings['destination'] is None:
            self.get_folder()

    def get_folder(self):
        if self._settings['destination'] is None:
            folder = QFileDialog.getExistingDirectory(self)
            if folder:
                self._settings['destination'] = folder

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.hide()
        self._fh.force_save = True
        self._fh.save_settings(self._settings)
        a0.accept()

    def debug_switch(self, *_):
        self._debug = not self._debug

    def update_timestamp(self):
        self.mediaplayer.errorLabel.setText(self.get_player_time())

    def stop(self):
        if self._active_prog is not None:
            self._queue.clear()
            if self._active_prog.isRunning():
                self._active_prog.abort = True

    def get_player_time(self, override=None):
        if override is None:
            time_ms = self.mediaplayer.mediaPlayer.position()
        else:
            time_ms = override
        time_s = time_ms // 1000
        time_min = time_s // 60
        remaining_s = time_s % 60
        remaining_ms = time_ms % 1000
        return f'{time_min:02d}:{remaining_s:02d}.{remaining_ms:03d}'

    @staticmethod
    def get_millisecond_time(string_time):
        m, sms = string_time.split(':')
        s, ms = sms.split('.')

        t1 = float(m) * 1000 * 60
        t2 = float(s) * 1000

        return t1 + t2 + int(ms)

    def get_start(self):
        self.start_time.setText(self.get_player_time())

    def get_end(self):
        self.end_time.setText(self.get_player_time())

    def _gen_split_commands(self, start, end):
        """
        Generates commands for splitting file into 3 parts.
        There the cut points are start/end mark.
        If the video is not cropped, there is no reencoding.
        """

        filename = self.current_file.text()
        cuts_rel = self.mediaplayer.overlay.get_cropped_area()
        if cuts_rel is not None:
            x = int(int(self._resolution[0]) * cuts_rel[0])
            y = int(int(self._resolution[1]) * cuts_rel[1])
            w = int(int(self._resolution[0]) * cuts_rel[2])
            h = int(int(self._resolution[1]) * cuts_rel[3])

            conversion_style = ['-crf', '18', '-filter:v', f'crop={w}:{h}:{x}:{y}', '-acodec', 'copy']
        else:
            conversion_style = ['-vcodec', 'copy', '-acodec', 'copy']

        commands = list()
        for i in range(3):
            command = list()
            command.append('-hide_banner')
            command.append('-nostdin')
            command.append('-i')

            command.append(f'{filename}')
            command.append('-y')
            command.extend(['-strict', '-2'])

            if i == 0:
                command.append('-to')
                command.append(f'{start}')
                command.extend(conversion_style)
            elif i == 1:
                command.append('-ss')
                command.append(f'{start}')
                command.append('-to')
                command.append(f'{end}')

                command.extend(conversion_style)

                # trim_part.extend(['-filter:v', f'setpts=4*PTS', '-af', 'atempo=0.5,atempo=0.5'])
            else:
                command.extend(conversion_style)
                command.append('-ss')
                command.append(f'{end}')

            out_path = self._settings['destination'] + '\\' + f'trim_{i}' + '.mp4'

            command.append(f'{out_path}')
            commands.append(command)

        return commands, f'Cutting {filename.split("/")[-1]}', 0

    def _disable(self):
        if self.sender() is self.trim and self.trim.isChecked():
            self.cut.setChecked(False)
        elif self.sender() is self.cut and self.cut.isChecked():
            self.trim.setChecked(False)

        state = self.trim.isChecked() or self.cut.isChecked()
        # self.out_name.setDisabled(state)
        self.bitrate.setDisabled(state)
        self.playback_rate.setDisabled(state)
        self.sound.setDisabled(state)

    def _gen_cut(self, start, end):
        """
        Generates command for splitting a file like the regular option.
        If the video is not cropped, there is no reencoding.
        """
        filename = self.current_file.text()
        cuts_rel = self.mediaplayer.overlay.get_cropped_area()
        out_path = self._settings['destination'] + '\\' + self.out_name.text() + '.mp4'

        if self._fh.is_file(out_path):
            result = self.alert_message('Warning!', 'File already exists!', 'Do you want to overwrite it?', True)
            if result != QMessageBox.Yes:
                raise InterruptedError('Can\'t overwrite file!')

        command = list()

        command.append('-hide_banner')
        command.append('-nostdin')
        command.append('-i')
        command.append(f'{filename}')
        command.append('-y')
        command.append('-ss')
        command.append(f'{start}')
        command.append('-to')
        command.append(f'{end}')

        if cuts_rel is not None:
            x = int(int(self._resolution[0]) * cuts_rel[0])
            y = int(int(self._resolution[1]) * cuts_rel[1])
            w = int(int(self._resolution[0]) * cuts_rel[2])
            h = int(int(self._resolution[1]) * cuts_rel[3])

            command.extend(['-crf', '18', '-filter:v', f'crop={w}:{h}:{x}:{y}', '-acodec', 'copy'])
        else:
            command.extend(['-vcodec', 'copy', '-acodec', 'copy'])

        command.append(f'{out_path}')

        return [command], filename, 0

    def _gen_commands(self, start_timestamp, end_timestamp):

        filename = self.current_file.text()
        target_size = float(self.bitrate.text())
        filetype = self.filetype.currentText()
        target_name = self.out_name.text()
        length_multipler = self.playback_rate.text()
        start = self.get_player_time(int(self.get_millisecond_time(start_timestamp) * float(length_multipler)))
        end = self.get_player_time(int(self.get_millisecond_time(end_timestamp) * float(length_multipler)))
        crop_area = self.mediaplayer.overlay.get_cropped_area()
        out_path = self._settings['destination'] + '\\' + target_name + '.' + filetype

        if os.path.isfile(out_path) or any([target_name + '.' + filetype == i.name for i in self._queue]):
            result = self.alert_message('Warning!', 'File already exists or is in the queue!',
                                        'Do you want to overwrite it?', True)
            if result != QMessageBox.Yes:
                raise InterruptedError('Can\'t overwrite file!')
        t0 = self.get_millisecond_time(start) / 1000
        tf = self.get_millisecond_time(end) / 1000

        duration = tf - t0  # In seconds!
        bitrate = int(target_size * 8 * 1024 // duration)

        if self.sound.isChecked():
            bitrate -= 320

        if bitrate < 1:
            raise InterruptedError('Too small target filesize, too low bitrate')
        else:
            print('Bitrate', bitrate)

        self._log.debug(f"""
File: {filename}
Target name: {target_name}
Target destination: {out_path}
Target size: {target_size}
Target filetype: {filetype}
Length multiplier: {length_multipler}
Start: {start_timestamp} ({t0:.3f} seconds)
Start: {end_timestamp} ({tf:.3f} seconds)
""")

        commands = []

        command_1 = []
        command_2 = []

        command_1.append('-hide_banner')
        command_1.append('-nostdin')

        checked = False
        for i in (command_1, command_2):
            i.extend(['-i', f'{filename}'])
            i.extend(['-y'])

            if start != '':
                i.extend(['-ss', f'{start}'])
            if end != '':
                i.extend(['-to', f'{end}'])

            i.extend(['-map', '0:v:0', '-threads', '12'])

            if filetype == 'webm':
                i.extend(['-c:v', 'libvpx-vp9'])
                i.extend(['-tile-columns', '6'])
                i.extend(['-frame-parallel', '0', '-auto-alt-ref', '1'])
                i.extend(['-lag-in-frames', '25', '-g', '128', '-pix_fmt', 'yuv420p'])

            i.extend(['-row-mt', '1'])
            i.extend(['-b:v', f'{bitrate:.2f}k', '-crf', '28'])

            if self.sound.isChecked():
                i.extend(['-map', '0:a:0', '-c:a', 'libopus', '-b:a', '320k'])
                if float(length_multipler) != 1 and not checked:
                    result = self.alert_message('Warning!',
                                                'No sound allowed with changed duration!\n'
                                                'Ignoring the duration change.',
                                                'Do you want to stop encoding?',
                                                True)
                    if result == QMessageBox.Yes:
                        raise InterruptedError('Stopped on command!')
                    length_multipler = 1
                    checked = True  # In multi pass, this prevents repeatedly asking
            else:
                i.append('-an')

                if crop_area is not None:
                    x = int(int(self._resolution[0]) * crop_area[0])
                    y = int(int(self._resolution[1]) * crop_area[1])
                    w = int(int(self._resolution[0]) * crop_area[2])
                    h = int(int(self._resolution[1]) * crop_area[3])
                    crop = f',crop={w}:{h}:{x}:{y}'
                else:
                    crop = ''
                i.extend(['-filter:v', f'setpts={length_multipler}*PTS{crop}'])

        command_1.extend(['-f', 'null', '-pass', '1', 'NUL'])
        command_2.extend(['-f', f'{filetype}', '-pass', '2', '-metadata', f'title={target_name}'])

        # com_2.extend(['-vf', f'minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me=umh:vsbmc=1'])

        command_2.append(f'{out_path}')

        commands.extend([command_1, command_2])

        return commands, self.out_name.text() + '.' + filetype, duration

    def alert_message(self, title, text, info_text, question=False, allow_cancel=False):
        warning_window = QMessageBox(parent=self)
        warning_window.setText(text)
        warning_window.setIcon(QMessageBox.Warning)
        warning_window.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
        warning_window.setWindowTitle(title)

        if info_text:
            warning_window.setInformativeText(info_text)
        if question and allow_cancel:
            warning_window.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        elif question:
            warning_window.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        return warning_window.exec()

    def start(self, *_):
        try:
            if self.out_name.text() in ('', ' ', '  '):
                self.textbox.append(color_text('INVALID FILENAME!'))
                return

            self.startbtn.setDisabled(True)
            self.cancelbtn.setDisabled(False)

            start = self.start_time.text()
            end = self.end_time.text()

            try:
                if self.trim.isChecked():
                    commands, name, duration = self._gen_split_commands(start, end)
                elif self.cut.isChecked():
                    commands, name, duration = self._gen_cut(start, end)
                else:
                    commands, name, duration = self._gen_commands(start, end)

            except InterruptedError as e:
                traceback.print_exc()
                return

            process = Conversion(commands=commands, target_name=name, file_name=self.current_file.text(),
                                 duration=duration)
            process.finished.connect(self._deplete_queue)
            process.finished.connect(self.done)
            process.process_output.connect(self.append_to_tb)

            self._queue.append(process)
            self._deplete_queue()
        except:
            traceback.print_exc()

    def done(self, *_):
        self.append_to_tb('Finished')

    def _deplete_queue(self):
        if self._active_prog is not None and self._active_prog.isRunning():
            return

        if self._queue:
            self._active_prog = self._queue.popleft()
            self._active_prog.start()
        else:
            self._active_prog = None

    def start_button_timer(self, state):
        if not state:
            self.timer.start(1000)

    def append_to_tb(self, text):
        if not text:
            return

        self.textbox.setText(text)

        if self._queue:
            self.textbox.append('\n\nIn queue:\n' +
                                '\n'.join([f'{idx}. {i.name}' for idx, i in enumerate(self._queue, 1)]))

            if self._debug:
                if self._active_prog is not None:
                    self.textbox.append('\n\n')
                    self.textbox.append(f'Current pass:\n{self._active_prog.current}')
                    self.textbox.append('\n')
                    for line in self._active_prog.queue:
                        self.textbox.append(f'{" ".join(line)}\n\n')

                self.textbox.append('\n\n')
                if self._queue:
                    for program in self._queue:
                        self.textbox.append(f'{program.name}')
                        for line in program.queue:
                            self.textbox.append('\n')
                            self.textbox.append(f'{" ".join(line)}\n')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls and len(event.mimeData().urls()) == 1:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.add_url(event.mimeData().urls()[0])
        else:
            event.ignore()

    def add_url(self, file):
        p = QProcess()
        p.start(
            f'ffprobe "{file.toString().replace("file:///", "")}" '
            f'-v 0 -select_streams v:0 -show_entries '
            f'stream=width,height -of csv=s=x:p=0')
        p.waitForStarted()
        p.waitForFinished()
        self._resolution = p.readAll().data().decode('utf-8', 'replace').strip().split('x')

        self.mediaplayer.mediaPlayer.setMedia(QMediaContent(file))

        self.mediaplayer.playButton.setEnabled(True)
        self.mediaplayer.trim_btn.setDisabled(False)
        self.mediaplayer.trim2_btn.setDisabled(False)
        self.current_file.setText(str(file.toLocalFile()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.mediaplayer.play()
        elif event.key() == Qt.Key_M:
            self.mediaplayer.mediaPlayer.setMuted(not self.mediaplayer.mediaPlayer.isMuted())
        elif event.key() == Qt.Key_Left:
            self.mediaplayer.skip(-5000)
        elif event.key() == Qt.Key_Right:
            self.mediaplayer.skip(5000)
        else:
            super(GUI, self).keyPressEvent(event)
