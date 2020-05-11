from PyQt5.QtWidgets import QGridLayout, QPushButton, QLabel, QLineEdit, QDialog

from utils import color_text


class Dialog(QDialog):
    def __init__(self, parent=None, name: str = '', description: str = ''):
        super(Dialog, self).__init__(parent)
        self.option = QLineEdit()

        self.label = QLabel(color_text('Insert option:', 'limegreen'))
        self.name_label = QLabel(color_text(name + ':', 'limegreen'))
        self.tooltip = QLabel(description)

        self.ok_button = QPushButton('Ok', self)
        self.ok_button.setFixedSize(self.ok_button.sizeHint())
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.setFixedSize(self.cancel_button.sizeHint())
        self.cancel_button.clicked.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.name_label, 0, 0, 1, 3)
        layout.addWidget(self.tooltip, 1, 0, 1, 3)

        layout.addWidget(self.label, 2, 0, 1, 3)
        layout.addWidget(self.option, 3, 0, 1, 3)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)
        layout.addWidget(self.ok_button, 4, 1)
        layout.addWidget(self.cancel_button, 4, 2)

        self.setFixedHeight(self.sizeHint().height())
        self.setFixedWidth(self.sizeHint().width())
        self.option.setFocus()

    def answer(self):
        return self.option.text()
