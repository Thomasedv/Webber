from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QSlider


class RelayPushButton(QPushButton):
    def keyPressEvent(self, a0) -> None:
        if a0.key() == Qt.Key_Space:
            self.parent().keyPressEvent(a0)
        else:
            super(RelayPushButton, self).keyPressEvent(a0)


class RelaySlider(QSlider):
    def keyPressEvent(self, a0) -> None:
        self.parent().keyPressEvent(a0)

