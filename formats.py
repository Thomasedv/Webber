from collections import namedtuple
from collections import namedtuple
from functools import partial

from PyQt5.QtWidgets import QDialog, QApplication, QFormLayout, QLabel, QLineEdit, QPushButton
from more_itertools import consume
from more_itertools.recipes import grouper

from dialog import Dialog
from utils import color_text, get_stylesheet

encoding = namedtuple('Encoding', ['ext', 'f', 'commands'])
passes = namedtuple('commandset', ['all', 'first', 'second'])
format_spec = {}

webm_params = passes([
    '-c:v', 'libvpx-vp9',
    '-tile-columns', '2',
    '-tile-rows', '1',
    '-threads', '12',
    '-row-mt', '1',
    '-static-thresh', '0',
    '-frame-parallel', '0',
    '-auto-alt-ref', '6',
    '-lag-in-frames', '25',
    '-g', '120',
    '-crf', '30',
    '-pix_fmt', 'yuv420p'
], [
    '-cpu-used', '1'
], [
    '-cpu-used', '1'
])

format_spec['Webm'] = encoding('webm', 'webm', webm_params)

av1_params = passes([
    '-c:v', 'libaom-av1',
    '-tiles', '2x1',
    '-threads', '12',
    '-pix_fmt', 'yuv420p',
    '-row-mt', '1',
    '-auto-alt-ref', '1',
    '-lag-in-frames', '25',
    '-strict', 'experimental',
    '-static-thresh', '0',
    '-frame-parallel', '0',
], [
    '-cpu-used', '8',
], [
    '-cpu-used', '6',
])

format_spec['AV1'] = encoding('webm', 'webm', av1_params)


class Tweaker(QDialog):
    def __init__(self, spec: str):
        super(Tweaker, self).__init__()
        self.enc = format_spec[spec]
        self.setWindowTitle(spec)

        self.ok_button = QPushButton('Ok', self)
        # self.ok_button.setFixedSize(self.ok_button.sizeHint())
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton('Cancel', self)
        # self.cancel_button.setFixedSize(self.cancel_button.sizeHint())
        self.cancel_button.clicked.connect(self.reject)

        self.setStyleSheet(get_stylesheet())
        self.all_pass = self.enc.commands.all
        self.first_pass = self.enc.commands.first
        self.second_pass = self.enc.commands.second

        self.all_pass_pairs = {k: v for k, v in grouper(self.all_pass, 2)}
        self.first_pass_pairs = {k: v for k, v in grouper(self.first_pass, 2)}
        self.second_pass_pairs = {k: v for k, v in grouper(self.second_pass, 2)}

        self.create_form()

    def add_row(self, pass_dict: dict):
        idx = self.form.indexOf(self.sender())
        dia = Dialog(self, 'Pick a parameter!', 'Select the name of the option to add!')
        if dia.exec() != QDialog.Accepted:
            return

        key = dia.answer()
        if key in pass_dict:
            return

        value = QLineEdit('')
        value.textChanged.connect(partial(self.update_pair, pass_dict, key))
        self.form.insertRow(idx, key, value)
        # TODO: Duplicate detection

    def update_pair(self, pair_map: dict, key: str, value: str):
        if not key.startswith('-'):
            key = '-' + key

        pair_map.update({key: value})

    def create_form(self):
        self.form = form = QFormLayout()
        for pass_name, pass_dict in zip(('All passes', 'First Pass', 'Second Pass'),
                                        (self.all_pass_pairs, self.first_pass_pairs, self.second_pass_pairs)):

            add_btn = QPushButton('Add')
            add_btn.clicked.connect(partial(self.add_row, pass_dict))

            form.addRow(QLabel(color_text(pass_name, color='limegreen')), add_btn)
            for key, value in pass_dict.items():
                value_field = QLineEdit(value)
                value_field.textChanged.connect(partial(self.update_pair, pass_dict, key))
                form.addRow(key, value_field)
            form.addRow(self.ok_button, self.cancel_button)

        self.setLayout(form)

    def get_encoding(self):
        for pass_list, pass_pair in zip([self.all_pass, self.first_pass, self.second_pass],
                                        [self.all_pass_pairs, self.first_pass_pairs, self.second_pass_pairs]):
            pass_list.clear()
            consume(pass_list.extend([k, v]) for k, v in pass_pair.items())

        p = passes(self.all_pass, self.first_pass, self.second_pass)
        return encoding(self.enc.ext, self.enc.f, p)


if __name__ == '__main__':
    app = QApplication([])
    t = Tweaker('Webm')
    if t.exec() == QDialog.Accepted:
        print(t.get_encoding())
