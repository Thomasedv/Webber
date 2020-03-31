import sys
import traceback

from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class GraphicsView(QGraphicsView):
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.parent().play()
        return super(GraphicsView, self).mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.parent().keyPressEvent(event)
        pass

    def wheelEvent(self, event: QWheelEvent) -> None:
        pass

    def dragEnterEvent(self, event):
        try:
            return self.parent().dragEnterEvent(event)
        except:
            traceback.print_exc()

    def dragMoveEvent(self, event):
        try:
            return self.parent().dragMoveEvent(event)
        except:
            traceback.print_exc()


class VideoOverlay(QWidget):
    def __init__(self, video: QGraphicsVideoItem, media, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.begin = QPoint()
        self.end = QPoint()
        self.qp = QPainter()
        self.video = video
        self.mediaPlayer = media
        self.setStyleSheet('background: transparent;')
        self.current = QRect()

    def get_cropped_area(self):
        if not self.mediaPlayer.media().isNull():
            if self.begin == self.end == QPoint():
                return None

            vid = self.video.boundingRect().toRect()
            vid: QRect()
            a = QRect(self.begin, self.end)
            sel_tlx = a.x() - vid.topLeft().x() if a.x() - vid.topLeft().x() >= vid.topLeft().x() else 0
            sel_tly = a.y() - vid.topLeft().y() if a.y() - vid.topLeft().y() >= vid.topLeft().y() else 0
            # sel_blx = sel_tlx + a.width() if sel_tlx + a.width() <= vid.width() else vid.width()
            # sel_bly = sel_tly + a.height() if sel_tly + a.height() <= vid.height() else vid.height()

            # print(f'-----------\n'
            #       f'Brekt {vid}\n'
            #       f'vid br x {vid.bottomRight().x()}')
            # print(f'vid br y {vid.bottomRight().y()}')
            # print(f'tl x {sel_tlx}\ntl y {sel_tly}'
            #       f'\nbl x {sel_blx}\nbl y {sel_bly}')
            return sel_tlx / vid.width(), sel_tly / vid.height(), a.width() / vid.width(), a.height() / vid.height()
        else:
            return None

    def gen_square(self):
        if not self.mediaPlayer.media().isNull():
            try:
                area = QRegion(self.video.boundingRect().toRect())
                squre = QRegion(QRect(self.begin, self.end))
                to_draw = area.subtracted(squre)
                self.qp.setClipRegion(to_draw)

                # print(f'---------\n'
                #       f'Begin {self.begin}\nEnd {self.end}\nVideo pos {self.video.boundingRect()}\nVideo size {self.video.size()}'
                #       f'\n---------')

                if self.begin == self.end == QPoint():
                    return QRect()

                return self.video.boundingRect().toRect()
            except:
                traceback.print_exc()

        # self.qp.setClipRegion()

        return QRect()

    def paintEvent(self, event):
        super(VideoOverlay, self).paintEvent(event)

        # if self.current != QRect:
        br = QBrush(QColor(250, 250, 250, 70))
        self.qp.begin(self)
        self.qp.setBrush(br)
        self.qp.setPen(Qt.NoPen)
        self.current = self.gen_square()
        if self.current == QRect():
            self.qp.end()
            return
        self.qp.fillRect(self.current, br)
        self.qp.end()
        # super(Player, self).paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # cursor = QCursor()
            # pos = cursor.pos()
            # print(pos)
            self.begin = event.pos()
            self.end = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.RightButton:
            # print(event.pos())
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.end = event.pos()
            sel = QRect(self.begin, self.end)
            if sel.width() < 10 or sel.height() < 10:
                self.end = QPoint()
                self.begin = QPoint()
            self.update()
    # TODO: Use Qrect.isvalid to check if coordinates are valid
    # IF they are NOT, try changing them such that they are;
    # to allow dragging from other corners than the top left


if __name__ == '__main__':
    pass
    # app = QApplication(sys.argv)
    # player = Player()
    # player.show()
    # sys.exit(app.exec_())
