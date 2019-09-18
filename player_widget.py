# PyQt5 Video player
# !/usr/bin/env python
import sys
import traceback
import typing

from PyQt5.QtCore import Qt, QSizeF
from PyQt5.QtGui import QShowEvent
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel,
                             QSizePolicy, QSlider, QStyle, QVBoxLayout, QGraphicsScene, QProxyStyle)
from PyQt5.QtWidgets import QWidget, QPushButton

from video import VideoOverlay, GraphicsView


class VideoWindow(QWidget):

    def __init__(self, parent=None):
        super(VideoWindow, self).__init__(parent=parent)

        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        self._scene = QGraphicsScene(self)

        self.videoWidget = QGraphicsVideoItem()
        self.videoWidget.setSize(QSizeF(1920, 1080))

        self.overlay = VideoOverlay(self.videoWidget, self.mediaPlayer)

        self._gv = GraphicsView(self._scene, parent=self)
        self._gv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._gv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._scene.addItem(self.videoWidget)
        self._scene.addWidget(self.overlay)

        def temp1(*_):
            if not self.mediaPlayer.media().isNull():
                is_full = self.videoWidget.isFullScreen()
                self.videoWidget.setFullScreen(not is_full)

                if self.mediaPlayer.state() in (QMediaPlayer.PausedState, QMediaPlayer.StoppedState):
                    self.mediaPlayer.play()
                else:
                    self.mediaPlayer.pause()

        self.videoWidget.mouseDoubleClickEvent = temp1

        # def temp2(*_):
        #     if not self.mediaPlayer.media().isNull() and _[0].button() == Qt.LeftButton:
        #         if self.mediaPlayer.state() in (QMediaPlayer.PausedState, QMediaPlayer.StoppedState):
        #             self.mediaPlayer.play()
        #         else:
        #             self.mediaPlayer.pause()
        #     else:
        #         super().mousePressEvent(*_)
        #
        # self.videoWidget.mousePressEvent = temp2
        class SliderProxy(QProxyStyle):
            def styleHint(self, hint: QStyle.StyleHint, option=..., widget: typing.Optional[QWidget] = ...,
                          returnData=...) -> int:
                if hint == QStyle.SH_Slider_AbsoluteSetButtons:
                    return Qt.LeftButton | Qt.MidButton | Qt.RightButton
                return super(SliderProxy, self).styleHint(hint, option, widget, returnData)

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.positionSlider = QSlider(Qt.Horizontal)
        # self.positionSlider
        self.positionSlider.setStyle(SliderProxy(self.positionSlider.style()))
        self.positionSlider.setRange(0, 0)
        self.positionSlider.valueChanged.connect(self.setPosition)
        self.positionSlider.sliderPressed.connect(self.slider_pressed)
        self.positionSlider.sliderReleased.connect(self.slider_released)

        # self.positionSliderF = QSlider(Qt.Horizontal)
        # self.positionSliderF.setRange(0, 0)
        # # self.positionSliderF.sliderMoved.connect(self.setPosition)
        # self.positionSlider.valueChanged.connect(self.setPosition)
        # self.positionSliderF.hide()

        self.errorLabel = QLabel()
        self.errorLabel.setSizePolicy(QSizePolicy.Preferred,
                                      QSizePolicy.Maximum)

        # # Create new action
        # openAction = QAction(QIcon('open.png'), '&Open', self)
        # openAction.setShortcut('Ctrl+O')
        # openAction.setStatusTip('Open movie')
        # openAction.triggered.connect(self.openFile)
        #
        # # Create exit action
        # exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        # exitAction.triggered.connect(self.exitCall)
        #
        # # Create menu bar and add action
        # menuBar = self.menuBar()
        # fileMenu = menuBar.addMenu('&File')
        # # fileMenu.addAction(newAction)
        # fileMenu.addAction(openAction)
        # fileMenu.addAction(exitAction)

        # Create a widget for window contents
        # wid = self
        # self.setCentralWidget(wid)

        # Create layouts to place inside widget

        self.trim_btn = QPushButton('Start')
        self.trim2_btn = QPushButton('End')
        self.trim_btn.setDisabled(True)
        self.trim2_btn.setDisabled(True)

        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.positionSlider)
        controlLayout.addWidget(self.trim_btn)
        controlLayout.addWidget(self.trim2_btn)
        # controlLayout.addWidget(self.positionSliderF)

        layout = QVBoxLayout()
        layout.addWidget(self._gv)
        layout.addLayout(controlLayout)
        layout.addWidget(self.errorLabel)

        # Set widget to contain window contents
        self.setLayout(layout)
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.mediaStatusChanged.connect(self.media_status_change)
        self.mediaPlayer.error.connect(self.handleError)

        self.was_playing = False

        # TODO: Arrow keys for fine control!

    def slider_pressed(self, *event):
        self.was_playing = not self.mediaPlayer.state() in (QMediaPlayer.PausedState, QMediaPlayer.StoppedState)
        self.mediaPlayer.pause()

    def slider_released(self, *event):
        if self.was_playing:
            self.mediaPlayer.play()

    def media_status_change(self, status):
        if status == QMediaPlayer.LoadedMedia:
            rect = self._scene.itemsBoundingRect()
            self._scene.setSceneRect(rect)
            self._gv.fitInView(self.videoWidget, Qt.KeepAspectRatio)
            try:
                self.mediaPlayer.blockSignals(True)
                self.mediaPlayer.setMuted(True)
                self.mediaPlayer.play()
                self.mediaPlayer.pause()
                self.mediaPlayer.setMuted(False)
                self.mediaPlayer.setPosition(0)
                self.mediaPlayer.blockSignals(False)
            except:
                traceback.print_exc()

    def skip(self, time_ms):
        if not self.mediaPlayer.media().isNull():
            self.mediaPlayer.blockSignals(True)
            self.mediaPlayer.pause()
            self.mediaPlayer.setPosition(self.mediaPlayer.position() + time_ms)
            self.mediaPlayer.play()
            self.mediaPlayer.blockSignals(False)

    def resizeEvent(self, event) -> None:
        super(VideoWindow, self).resizeEvent(event)
        try:
            rect = self._scene.itemsBoundingRect()
            self._scene.setSceneRect(rect)
            self._gv.fitInView(self.videoWidget, Qt.KeepAspectRatio)
            self.overlay.resize(self.videoWidget.size().toSize())
        except:
            traceback.print_exc()

    # def moveEvent(self, a0: QMoveEvent) -> None:
    #     super(VideoWindow, self).moveEvent(a0)
    #     print('as')
    #     self.overlay.move(self.mapToGlobal(self.videoWidget.pos()))
    #
    # def eventFilter(self, a0, a1) -> bool:
    #     if a1.type() == QEvent.Move:
    #         print('moved')
    #
    # def closeEvent(self, a0: QCloseEvent) -> None:
    #     self.overlay.hide()
    #     self.overlay.close()
    #     self.overlay = None
    #     a0.accept()
    # super(VideoWindow, self).resizeEvent(a0)
    # def openFile(self):
    #     fileName, _ = QFileDialog.getOpenFileName(self, "Open Movie",
    #                                               QDir.homePath())
    #
    #     if fileName != '':
    #         self.mediaPlayer.setMedia(
    #             QMediaContent(QUrl.fromLocalFile(fileName)))
    #         self.playButton.setEnabled(True)
    #
    # def exitCall(self):
    #     sys.exit(app.exec_())
    def showEvent(self, a0: QShowEvent) -> None:
        super(VideoWindow, self).showEvent(a0)

    # @pyqtSlot(QMediaPlayer.State)
    # def on_stateChanged(self, state):
    #     if state == QMediaPlayer.PlayingState:
    #         self._gv.fitInView(self._videoitem, Qt.KeepAspectRatio)

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.blockSignals(True)
        self.positionSlider.setValue(position)
        self.positionSlider.blockSignals(False)

    def durationChanged(self, duration):
        self.positionSlider.blockSignals(True)
        self.positionSlider.setRange(0, duration)
        self.positionSlider.blockSignals(False)

    def setPosition(self, position):
        self.positionSlider.blockSignals(True)
        self.mediaPlayer.setPosition(position)
        print(self.mediaPlayer.position())
        self.positionSlider.blockSignals(False)

    def handleError(self):
        self.playButton.setEnabled(False)
        self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())

    def wheelEvent(self, event):
        if not self.mediaPlayer.media().isNull():
            change = event.angleDelta().y()
            if change:
                self.mediaPlayer.setVolume(self.mediaPlayer.volume() + change // 24)
        else:
            super(VideoWindow, self).wheelEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        player = VideoWindow()

        player.resize(640, 480)

        player.show()
    except Exception as e:
        traceback.print_exc()
    sys.exit(app.exec_())
