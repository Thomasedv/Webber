import os
import re
import sys
import textwrap
import time
import traceback
from collections import deque

import psutil
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent
from PyQt5.QtWidgets import *

from formats import format_spec, Tweaker
from player_widget import VideoWindow
from utils import get_logger, color_text, FileHandler, get_stylesheet, find_file
from worker import Conversion


# TODO: Check for ffmpeg! Warn user.

class GUI(QMainWindow):
    def __init__(self):
        super(GUI, self).__init__()

        # Internal variables

        # TODO: Make settings file, get path from settings
        self._debug = False
        self._active_prog = None
        self._resolution = None
        self.is_paused = False
        self.last_message = ''
        self.audio_bitrate = 320

        self._queue = deque()
        self._log = get_logger('Webber.GUI')
        self._fh = FileHandler()
        self._settings = self._fh.load_settings()

        self.validate_settings()
        self._log.info(f'Current dest folder: {self._settings["destination"]}')

        self.toggle_debug = QShortcut(QKeySequence('Ctrl+P'), self)
        self.toggle_debug.activated.connect(self.debug_switch)

        self.open_tweaker = QShortcut(QKeySequence('Ctrl+E'), self)
        self.open_tweaker.activated.connect(self.tweak_options)

        self.pause_shourtcut = QShortcut(QKeySequence('Ctrl+Space'), self)
        self.pause_shourtcut.activated.connect(self.pause)
        self.worker = QThreadPool(self)
        self.worker.setMaxThreadCount(1)

        # GUI setup
        menubar = QMenuBar(self)

        menu = QMenu('Options', menubar)

        select_dest = QAction('Select destination', menu)
        select_dest.triggered.connect(self.get_folder)
        menu.addAction(select_dest)
        menubar.addMenu(menu)
        self.setMenuBar(menubar)

        self.current_file = QLineEdit('')
        self.current_file.setReadOnly(True)
        self.tutorial_text = textwrap.dedent(f"""\
        Drag a file to this window to open!
        Mute video with M-key, or adjust with scroll wheel on video.
        \n\n\
        {color_text('Short Tutorial:', 'white','bold')}
        
        1. After dragging the video into the window, find the positions in the video you want to cut the video to.
        
        2. Use the start/stop buttons to set the timestamp. Give the file a name, use the webm option, check box for\
         sound sound and pick a target filesize if you want a different size.
        
        2a. (Optional) Right-click and drag down and right on video if you want to crop it.
        
        2b. (Optional) Increase length-multiplier to slow down video. [Has limited use]
        
        4. Press convert to add the video to the conversion queue. Monitor progress here.
        
        The conversion can be paused and unpaused by pressing Ctrl+Space. 
        """)
        # Needed for Rich text
        self.tutorial_text = self.tutorial_text.replace('\n', '<br>')

        self.setAcceptDrops(True)
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setObjectName('TextFileEdit')
        self.textbox.setText(self.tutorial_text)
        self.textbox.setFocusPolicy(Qt.NoFocus)

        self.out_name = QLineEdit()
        self.start_time = QLineEdit('00:00.00')
        self.end_time = QLineEdit()

        self.bitrate = QLineEdit('8')
        self.playback_rate = QLineEdit('1.0')

        self.sound = QCheckBox('Sound')
        self.sound.setLayoutDirection(Qt.LeftToRight)
        self.sound.stateChanged.connect(self._disable)

        self.merge = QCheckBox('Merge Audio')
        self.merge.setLayoutDirection(Qt.LeftToRight)

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
        self.cancelbtn.setFocusPolicy(Qt.NoFocus)
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
        self.filetype.addItems(format_spec.keys())

        self.top_layout = QHBoxLayout()

        self.infobox = QGridLayout()
        self.infobox.addWidget(QLabel('Path:'))
        self.infobox.addWidget(self.current_file, 0, 1, 1, 2)
        self.infobox.addWidget(self.textbox, 1, 0, 1, 3)
        self.infobox.addWidget(QLabel('Length mul.'))
        self.infobox.addWidget(self.playback_rate, 2, 1, 1, 1)

        self.infobox.addWidget(self.trim, 2, 2, 1, 1)

        self.infobox.addWidget(QLabel('Target Name:'), 3, 0, 1, 1)
        self.infobox.addWidget(self.out_name, 3, 1, 1, 1)
        self.infobox.addWidget(self.filetype, 3, 2, 1, 1)

        self.infobox.addWidget(QLabel('Start time:'))
        self.infobox.addWidget(self.start_time, 4, 1, 1, 2)
        self.infobox.addWidget(QLabel('End time:'))
        self.infobox.addWidget(self.end_time, 5, 1, 1, 2)
        self.infobox.addWidget(QLabel('Size MB:'))
        self.infobox.addWidget(self.bitrate, 6, 1, 1, 1)
        self.infobox.addWidget(self.cut, 6, 2, 1, 1)

        self.infobox.addWidget(self.sound, 7, 0, Qt.AlignLeft)
        self.infobox.addWidget(self.startbtn, 7, 1, 1, 1)
        self.infobox.addWidget(self.cancelbtn, 7, 2, 1, 1)

        self.infobox.addWidget(self.merge, 8, 0, 1, 1, Qt.AlignLeft)

        # self.layout = QGridLayout()
        # self.layout.addWidget(QLabel('Path:'))
        # self.layout.addWidget(self.current_file, 0, 1, 1, 2)
        # self.layout.addWidget(self.textbox, 1, 0, 1, 3)
        # self.layout.addWidget(QLabel('Length mul.'))
        # self.layout.addWidget(self.playback_rate, 2, 1, 1, 1)
        #
        # self.layout.addWidget(self.trim, 2, 2, 1, 1)
        #
        # self.layout.addWidget(QLabel('Target Name:'), 3, 0, 1, 1)
        # self.layout.addWidget(self.out_name, 3, 1, 1, 1)
        # self.layout.addWidget(self.filetype, 3, 2, 1, 1)
        #
        # self.layout.addWidget(QLabel('Start time:'))
        # self.layout.addWidget(self.start_time, 4, 1, 1, 2)
        # self.layout.addWidget(QLabel('End time:'))
        # self.layout.addWidget(self.end_time, 5, 1, 1, 2)
        # self.layout.addWidget(QLabel('Size MB:'))
        # self.layout.addWidget(self.bitrate, 6, 1, 1, 1)
        # self.layout.addWidget(self.cut, 6, 2, 1, 1)
        #
        # self.layout.addWidget(self.sound, 7, 0, Qt.AlignRight)
        # self.layout.addWidget(self.startbtn, 7, 1, 1, 1)
        # self.layout.addWidget(self.cancelbtn, 7, 2, 1, 1)

        # self.video_box = QVBoxLayout(self)
        # self.video_box.addWidget(self.mediaplayer)

        self.top_layout.addLayout(self.infobox, stretch=0)
        self.top_layout.addWidget(self.mediaplayer, stretch=1)

        self.w = QWidget(self)
        self.setCentralWidget(self.w)
        self.w.setLayout(self.top_layout)

        unchecked_icon = find_file('GUI\\Icon_unchecked.ico')
        checked_icon = find_file('GUI\\Icon_checked.ico')
        alert_icon = find_file('GUI\\Alert.ico')
        down_arrow_icon = find_file('GUI\\down-arrow2.ico')
        down_arrow_icon_clicked = find_file('GUI\\down-arrow2-clicked.ico')

        style_with_options = get_stylesheet() + f"""
        QCheckBox::indicator:unchecked {{
            image: url({unchecked_icon});
        }}

        QCheckBox::indicator:checked {{
            image: url({checked_icon});
        }}
        QComboBox::down-arrow {{
            border-image: url({down_arrow_icon});
            height: {self.filetype.iconSize().height()}px;
            width: {self.filetype.iconSize().width()}px;
        }}

        QComboBox::down-arrow::on {{
            image: url({down_arrow_icon_clicked});
            height: {self.filetype.iconSize().height()}px;
            width: {self.filetype.iconSize().width()}px;
        }}"""

        self.setStyleSheet(style_with_options)
        self.setWindowTitle('Webber')
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)
        self.showMaximized()

    def tweak_options(self):
        spec = self.filetype.currentText()
        t = Tweaker(spec)
        extra_options = {'-audio bitrate:': self.audio_bitrate}
        t.extend(extra_options)
        if t.exec() == QDialog.Accepted:
            format_spec[spec] = t.get_encoding()
            extra_results = t.get_extended_results()
            self.audio_bitrate = float(extra_results['-audio bitrate:'])

    def validate_settings(self):
        # TODO: Check for errors here
        intro = True
        while self._settings['destination'] is None:
            if intro:
                self.alert_message('Hello!', 'You will now be asked to pick  Destination folder',
                                   'This is where the converted clips are placed.')
                intro = False

            self.get_folder()
            if self._settings['destination'] is None:
                result = self.alert_message('Error', 'You need to select a destionation folder!',
                                            'Do you want to try again?', True)
                if result != QMessageBox.Yes:
                    sys.exit(1)

    def get_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Pick a destination folder:', '.')
        if folder:
            self._settings['destination'] = folder
            self._log.info(f'Current dest folder: {self._settings["destination"]}')

    def closeEvent(self, a0) -> None:
        if self._active_prog is not None:
            self.alert_message('Error!', 'Can not quit while conversion is in progress!',
                               'Cancel converison before closing.')
            a0.ignore()
            return
        self.hide()
        self.stop()

        self.mediaplayer.disconnect()
        self.mediaplayer.mediaPlayer.disconnect()
        self._fh.force_save = True
        self._fh.save_settings(self._settings)
        self._fh.threadpool.waitForDone()

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

            self.is_paused = False
            self.update_textbox()

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

    def _gen_split_commands(self, state):
        """
        Generates commands for splitting file into 3 parts.
        There the cut points are start/end mark.
        If the video is not cropped, there is no reencoding.
        """

        if state["crop_area"] is not None:
            x = int(int(self._resolution[0]) * state["crop_area"][0])
            y = int(int(self._resolution[1]) * state["crop_area"][1])
            w = int(int(self._resolution[0]) * state["crop_area"][2])
            h = int(int(self._resolution[1]) * state["crop_area"][3])
            # TODO: Use regular encoding options here.
            conversion_style = ['-crf', '18', '-filter:v', f'crop={w}:{h}:{x}:{y}']
        else:
            conversion_style = ['-vcodec', 'copy']

        if self.sound.isChecked():
            conversion_style.extend(['-acodec', 'copy'])
        else:
            conversion_style.extend(['-an'])

        commands = list()
        for i in range(3):
            command = list()
            command.append('-hide_banner')
            command.append('-nostdin')
            command.extend(['-i', f'{state["filename"]}', '-y'])
            command.extend(['-strict', '-2'])

            if i == 0:
                command.append('-to')
                command.append(f'{state["ts_start"]}')
                command.extend(conversion_style)
            elif i == 1:
                command.extend(['-ss', f'{state["ts_start"]}'])
                command.extend(['-to', f'{state["ts_end"]}'])

                command.extend(conversion_style)

                # trim_part.extend(['-filter:v', f'setpts=4*PTS', '-af', 'atempo=0.5,atempo=0.5'])
            else:
                command.extend(conversion_style)
                command.extend(['-ss', f'{state["ts_end"]}'])

            out_path = self._settings['destination'] + '\\' + f'trim_{i}' + '.mp4'

            command.append(f'{out_path}')
            commands.append(command)

        return commands, f'Cutting {state["filename"].split("/")[-1]}', 0

    def _disable(self):
        if self.sender() is self.trim and self.trim.isChecked():
            self.cut.setChecked(False)
        elif self.sender() is self.cut and self.cut.isChecked():
            self.trim.setChecked(False)

        state = self.trim.isChecked() or self.cut.isChecked()
        # self.out_name.setDisabled(state)
        self.bitrate.setDisabled(state)
        self.playback_rate.setDisabled(state)

        # Disable sound for trim option
        self.sound.setDisabled(self.trim.isChecked())
        if self.trim.isChecked():
            self.sound.setChecked(False)

        # Disable audio merge for sound off
        self.merge.setDisabled(not self.sound.isChecked())

        # Uncheck when audio off
        if not self.sound.isChecked() or not self.sound.isEnabled():
            self.merge.setChecked(False)

    def _gen_cut_commands(self, state):
        """
        Generates command for splitting a file like the regular option.
        If the video is not cropped, there is no reencoding.
        """
        out_path = self._settings['destination'] + '\\' + self.out_name.text() + '.mp4'

        if self._fh.is_file(out_path):
            result = self.alert_message('Warning!', 'File already exists!', 'Do you want to overwrite it?', True)
            if result != QMessageBox.Yes:
                raise InterruptedError('Can\'t overwrite file!')

        command = list()

        command.extend(
            ['-hide_banner', '-nostdin', '-y',
             '-i', f'{state["filename"]}',
             '-ss', f'{state["ts_start"]}',
             '-to', f'{state["ts_end"]}'])

        if state["crop_area"] is not None:
            x = int(int(self._resolution[0]) * state["crop_area"][0])
            y = int(int(self._resolution[1]) * state["crop_area"][1])
            w = int(int(self._resolution[0]) * state["crop_area"][2])
            h = int(int(self._resolution[1]) * state["crop_area"][3])
            # TODO: Use regular encoding options here.

            command.extend(['-crf', '18', '-filter:v', f'crop={w}:{h}:{x}:{y}', '-acodec', 'copy'])
        else:
            command.extend(['-vcodec', 'copy'])

        if self.sound.isChecked():
            command.extend(['-acodec', 'copy'])
        else:
            command.extend(['-an'])

        command.append(f'{out_path}')

        return [command], state["filename"], 0

    def load_options(self):
        state = dict(
            ts_start=self.start_time.text(),
            ts_end=self.end_time.text(),
            filename=re.sub(r'^[^\\/:"*?<>|]+$', '', self.current_file.text()),
            merge_audio=self.merge.isChecked(),
            target_size=float(self.bitrate.text()),
            filetype=self.filetype.currentText(),
            target_name=self.out_name.text(),
            multiplier=self.playback_rate.text(),
            crop_area=self.mediaplayer.overlay.get_cropped_area()
        )

        valid_name = re.match(r'(^ *$)', state['filename']) is None
        if not valid_name:
            self.alert_message('No Target file!', 'The target filename is not selected or incorrect!', '')
            raise InterruptedError('Filename not valid')

        stamp = 'start'
        try:
            start = self.get_player_time(int(self.get_millisecond_time(state['ts_start']) * float(state['multiplier'])))
            state['start'] = start
            stamp = 'end'
            end = self.get_player_time(int(self.get_millisecond_time(state['ts_end']) * float(state['multiplier'])))
            state['end'] = end
        except Exception:
            self.alert_message('Invalid timestamp',
                               f'The {stamp} timestamp is not valid!',
                               f'"{state[f"ts_{stamp}"]}" is not valid for Webber!')
            raise InterruptedError('Timestamp not valid')

        self._log.debug(textwrap.dedent(f"""
        File: {state["filename"]}
        Target name: {state["target_name"]}
        Target size: {state['target_size']}
        Target filetype: {state["filetype"]}
        Length multiplier: {state["multiplier"]}
        Audio bitrate: {self.audio_bitrate}
        """))

        return state

    def _gen_conversion_commands(self, state):
        encoding = format_spec[state["filetype"]]

        rand_passfilename = f'ffmpeg2pass{str(time.time())[-5:]}'

        out_path = self._settings['destination'] + '\\' + state["target_name"] + '.' + encoding.ext

        if os.path.isfile(out_path) or any(
                [state["target_name"] + '.' + encoding.ext == i.name for i in self._queue]):
            result = self.alert_message('Warning!', 'File already exists or is in the queue!',
                                        'Do you want to overwrite it?', True)
            if result != QMessageBox.Yes:
                raise InterruptedError('Can\'t overwrite file!')

        t0 = self.get_millisecond_time(state["start"]) / 1000
        tf = self.get_millisecond_time(state["end"]) / 1000

        duration = tf - t0  # In seconds!
        if duration <= 0:
            self.alert_message('Timestamps are incorrect!',
                               'The end timestamp is before the start timestamp!', '')
            raise InterruptedError('Too small target filesize, too low bitrate')

        # Assume 1kb = 1000 bit because it's ffmpeg standard?
        video_bitrate = int(state["target_size"] * 8 * 1024 // duration)

        if self.sound.isChecked():
            video_bitrate -= self.audio_bitrateavclear

        if video_bitrate < 1:
            self.alert_message('Target size too small!',
                               'The video is too long for the target bitrate!', '')
            raise InterruptedError('Too small target filesize, too low bitrate')
        elif video_bitrate < 512:
            result = self.alert_message('Warning!',
                                        'The current bitrate is very low, and will probably not work well.',
                                        'Do you want to stop encoding?',
                                        True)
            if result == QMessageBox.Yes:
                raise InterruptedError('Stopped on command! Too low bitrate selected.')

        self._log.debug(textwrap.dedent(f"""
                            Working dir: {os.getcwd()}
                            Target bitrate: {video_bitrate} kbps
                            Target destination: {out_path}
                            Start: {state['ts_start']} ({t0:.3f} seconds)
                            Start: {state['ts_end']} ({tf:.3f} seconds)
                            """))
        commands = []

        command_1 = []
        command_2 = []

        def convert_to_h(string):
            parts = string.split(':')
            if int(parts[0]) > 59:
                return ':'.join([str(int(parts[0]) // 60), str(int(parts[0]) % 60)] + parts[1:])
            else:
                return string

        start_formatted = convert_to_h(state["start"])
        end_formatted = convert_to_h(state["end"])
        checked = False

        for p, i in enumerate([command_1, command_2]):
            i.append('-hide_banner')
            i.append('-nostdin')

            i.extend(['-y'])

            # TODO: Make this option??
            # i.extend(['-hwaccel', 'cuda'])
            if state["start"] != '':
                i.extend(['-ss', f'{start_formatted}'])
            if state["end"] != '':
                i.extend(['-to', f'{end_formatted}'])

            i.extend(['-i', f'{state["filename"]}'])

            i.extend(['-map', '0:v:0', '-map', '0:s?'])

            i.extend(encoding.commands.all)

            if p == 0:
                i.extend(encoding.commands.first)
            elif p == 1:
                i.extend(encoding.commands.second)

            i.extend(['-b:v', f'{video_bitrate:.2f}k',
                      '-maxrate', f'{video_bitrate:.2f}k',
                      '-bufsize', f'{video_bitrate * 4:.2f}k'
                      ])

            if self.sound.isChecked() and p == 1:
                if state['merge_audio']:
                    command_2.extend(['-filter_complex', '[0:a:0][0:a:1]amerge=inputs=2[a]', '-map', "[a]",
                                      '-c:a', 'libopus', '-ac', '2', '-b:a', f'{self.audio_bitrate}k'])
                else:
                    command_2.extend(['-map', '0:a?', '-c:a', 'libopus', '-b:a', f'{self.audio_bitrate}k'])

                if float(state["multiplier"]) != 1 and not checked:
                    result = self.alert_message('Warning!',
                                                'No sound allowed with changed duration!\n'
                                                'Ignoring the duration change.',
                                                'Do you want to stop encoding?',
                                                True)
                    if result == QMessageBox.Yes:
                        raise InterruptedError('Stopped on command!')
                    state["multiplier"] = 1
                    checked = True  # In multi pass, this prevents repeatedly asking
            elif p == 1:
                command_2.append('-an')
            elif p == 0:
                command_1.append('-an')

            if state["crop_area"] is not None:
                x = state["crop_area"][0]
                y = state["crop_area"][1]
                # y = max(int(self._resolution[1]) - state["crop_area"][1], 0)
                w = state["crop_area"][2]
                h = state["crop_area"][3]
                crop = f'crop={w}:{h}:{x}:{y}'
            else:
                crop = ''

            if state["multiplier"]:
                if crop:
                    crop = ',' + crop
                i.extend(['-filter:v', f'setpts={state["multiplier"]}*PTS{crop}'])

            elif crop:
                i.extend(['-filter:v', crop])

        command_1.extend(['-f', f'{encoding.f}', '-passlogfile', f'{rand_passfilename}', '-pass', '1', 'NUL'])
        command_2.extend(['-f', f'{encoding.f}', '-passlogfile', f'{rand_passfilename}', '-pass', '2',
                          '-metadata', f'title={state["target_name"]}'])

        # com_2.extend(['-vf', f'minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me=umh:vsbmc=1'])

        command_2.append(f'{out_path}')

        commands.extend([command_1, command_2])

        return commands, self.out_name.text() + '.' + encoding.ext, duration, rand_passfilename

    def remove_pass_file(self, passlogfile):
        for file in os.listdir('.'):
            # print((passlogfile))
            if file.startswith(str(passlogfile)) and file.endswith('.log'):
                os.remove(file)
                break

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
                self.last_message = color_text('INVALID FILENAME!')
                self.update_textbox()
                return

            self.startbtn.setDisabled(True)
            self.cancelbtn.setDisabled(False)

            state = self.load_options()
            try:
                passfile = None
                if self.trim.isChecked():
                    commands, name, duration = self._gen_split_commands(state)
                elif self.cut.isChecked():
                    commands, name, duration = self._gen_cut_commands(state)
                else:
                    commands, name, duration, passfile = self._gen_conversion_commands(state)

            except InterruptedError as e:
                self._log.info(f'User error: {e}')
                return
            for i in commands:
                print(' '.join(i))
            process = Conversion(commands=commands, target_name=name, file_name=state['filename'],
                                 duration=duration)
            process.finished.connect(self._deplete_queue)
            process.done.connect(self.done)
            if passfile is not None:
                process.done.connect(lambda _, f=passfile: self.remove_pass_file(f))
            process.process_output.connect(self.update_last_message)

            self._queue.append(process)
            self._deplete_queue()
            self.update_textbox()
        except:
            traceback.print_exc()

    def pause(self):
        process = self._active_prog

        if process is not None:
            pid = process.get_pid()
            if pid is None:
                return

            p = psutil.Process(pid)
            if self.is_paused:
                p.resume()
                self.is_paused = False
            else:
                p.suspend()
                self.is_paused = True
            self.update_textbox()

    def done(self, code):
        if code == 123:
            self.last_message = 'Process stopped by user!'
        elif code:
            self.last_message = f'Process encountered an error with code {code}.'
        else:
            self.last_message = 'Finished successfully!'
        self.is_paused = False
        self.update_textbox()

    def _deplete_queue(self):
        if self._active_prog is not None and self._active_prog.isRunning():
            return

        if self._queue:
            self._active_prog = self._queue.popleft()
            self._active_prog.start()
        else:
            self._active_prog = None
            self.is_paused = False

    def start_button_timer(self, state):
        if not state:
            self.timer.start(1000)

    def update_last_message(self, text):
        self.last_message = text
        self.update_textbox()

    def update_textbox(self):
        self.textbox.setText(self.last_message)
        if self.is_paused:
            self.textbox.append(color_text('\nCONVERSION PAUSED\n') + 'Press Ctrl+Space to Resume!\n')

        if self._queue:
            self.textbox.append(color_text('\n\nIn queue:\n', color='white'))
            self.textbox.append('\n'.join([f'{idx}. {i.name}' for idx, i in enumerate(self._queue, 1)])+'\n\n')

        self.textbox.append('<br><br>'+self.tutorial_text)

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
            f'ffprobe "{file.toLocalFile().replace("file:///", "")}" '
            f'-v 0 -select_streams v:0 -show_entries '
            f'stream=width,height -of csv=s=x:p=0')
        p.waitForStarted()
        p.waitForFinished()
        print(p.exitCode())
        self.mediaplayer.overlay.reset()
        self._resolution = p.readAll().data().decode('utf-8', 'replace').strip().split('x')
        self.mediaplayer.videoWidget.setSize(QSizeF(float(self._resolution[0]), float(self._resolution[1])))

        try:
            self._log.debug(f'Resolution of video is {self._resolution[0]}x{self._resolution[1]}')
        except:
            traceback.print_exc()

        self.mediaplayer.mediaPlayer.setMedia(QMediaContent(file))

        self.mediaplayer.playButton.setEnabled(True)
        self.mediaplayer.trim_btn.setDisabled(False)
        self.mediaplayer.trim2_btn.setDisabled(False)
        self.current_file.setText(str(file.toLocalFile()))
        self.mediaplayer.mediaPlayer.mediaStatusChanged.connect(self.set_end_time)
        self.mediaplayer.resizeEvent(None)

    def set_end_time(self):
        self.end_time.setText(self.get_player_time(self.mediaplayer.mediaPlayer.duration()))

    def keyPressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if event.key() == Qt.Key_Space:
            self.mediaplayer.play()
        elif event.key() == Qt.Key_M:
            self.mediaplayer.mediaPlayer.setMuted(not self.mediaplayer.mediaPlayer.isMuted())
        elif event.key() == Qt.Key_Left:
            if modifiers == Qt.ControlModifier:
                step = 500
            else:
                step = 5000
            self.mediaplayer.skip(-step)
        elif event.key() == Qt.Key_Right:
            if modifiers == Qt.ControlModifier:
                step = 1000
            else:
                step = 5000
            self.mediaplayer.skip(step)
        else:
            super(GUI, self).keyPressEvent(event)
