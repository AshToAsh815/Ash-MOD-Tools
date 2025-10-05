# Copyright (C) 2025 AshToAsh815
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer

from BatchReplaceFiles import FileReplacerApp
from BatchRenameFiles import MainWindow as BatchRenameApp

import resources  # 内嵌资源

class SplashScreen(QLabel):
    """启动动画：淡入显示 LogoBig.png，1 秒后淡出"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 使用内嵌资源加载图片
        pixmap = QPixmap(":/LogoBig.png")
        self.setPixmap(pixmap)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)
        self.setWindowOpacity(0.0)  # 初始透明

    def fade_in(self, duration=500, finished_callback=None):
        self.anim_in = QPropertyAnimation(self, b"windowOpacity")
        self.anim_in.setDuration(duration)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)
        if finished_callback:
            self.anim_in.finished.connect(finished_callback)
        self.anim_in.start()

    def fade_out(self, duration=500, finished_callback=None):
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(duration)
        self.anim_out.setStartValue(self.windowOpacity())
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        if finished_callback:
            self.anim_out.finished.connect(finished_callback)
        self.anim_out.start()


class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        # ----------------- 窗口属性 -----------------
        self.setWindowTitle("Ash-MOD-Tools-v1.3")
        self.setGeometry(100, 100, 1000, 800)
        self.center_window()

        # ----------------- 主布局 -----------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tab_widget)

        # ----------------- 添加子程序 Tab -----------------
        self.file_replacer = FileReplacerApp(self)
        self.batch_rename = BatchRenameApp(self)
        self.tab_widget.addTab(self.file_replacer, "批量替换")
        self.tab_widget.addTab(self.batch_rename, "批量重命名")
        self.tab_widget.setCurrentIndex(0)

        # ----------------- 动画属性 -----------------
        self.fade_in = None
        self.fade_out = None
        self._closing = False

        # 初始透明
        self.setWindowOpacity(0.0)

    # ----------------- 居中窗口 -----------------
    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        geo = self.frameGeometry()
        geo.moveCenter(screen_geometry.center())
        self.move(geo.topLeft())

    # ----------------- 主窗口淡入 -----------------
    def fade_in_window(self, duration=500):
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(duration)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_in.start()

    # ----------------- 主窗口淡出 -----------------
    def closeEvent(self, event):
        if self._closing:
            return super().closeEvent(event)
        self._closing = True
        event.ignore()  # 阻止立即关闭

        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(500)
        self.fade_out.setStartValue(self.windowOpacity())
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.InCubic)

        def finish_close():
            self.fade_out = None
            self.hide()
            QApplication.instance().quit()

        self.fade_out.finished.connect(finish_close)
        self.fade_out.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置窗口图标，使用内嵌资源
    app.setWindowIcon(QIcon(":/icon.ico"))

    # ----------------- 启动动画 -----------------
    splash = SplashScreen()
    splash.resize(300, 300)  # 可根据 LogoBig.png 调整尺寸
    splash.move(
        QApplication.primaryScreen().availableGeometry().center() - splash.rect().center()
    )
    splash.show()

    main_app = MainApplication()

    # 先淡入 splash
    splash.fade_in(duration=500, finished_callback=lambda:
        # 1 秒后淡出 splash，同时主窗口淡入显示
        QTimer.singleShot(500, lambda: splash.fade_out(
            finished_callback=lambda: (
                splash.hide(),
                main_app.fade_in_window(),
                main_app.show()
            )
        ))
    )

    sys.exit(app.exec_())
