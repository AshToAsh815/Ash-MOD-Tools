# Copyright (C) 2025 AshToAsh815
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
import os
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout)
from PyQt5.QtCore import Qt

# Import the existing applications
from BatchReplaceFiles import FileReplacerApp
from BatchRenameFiles import MainWindow as BatchRenameApp

class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("Ash-MOD-Tools-v1.1")
        self.setGeometry(100, 100, 1000, 800) # 调整默认高度
        self.center_window() # 居中窗口
        
        # Create the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tab_widget)
        
        # Add the applications as tabs
        self.file_replacer = FileReplacerApp(self)
        self.batch_rename = BatchRenameApp(self)
        
        self.tab_widget.addTab(self.file_replacer, "批量替换")
        self.tab_widget.addTab(self.batch_rename, "批量重命名")
        
        # Set the default tab to File Replacer
        self.tab_widget.setCurrentIndex(0)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon (from resources.py)
    import resources
    app.setWindowIcon(QIcon(":/icon.ico"))
    
    main_app = MainApplication()
    main_app.show()
    sys.exit(app.exec_())