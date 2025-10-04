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
import re
from pathlib import Path
from collections import deque
from typing import List, Tuple, Dict, Optional, Set
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTreeView, QPushButton, QSplitter, QGroupBox, QCheckBox, 
                             QLabel, QLineEdit, QSpinBox, QComboBox, QFileDialog, 
                             QMessageBox, QStatusBar, QFrame, QAbstractItemView,
                             QHeaderView, QStyledItemDelegate, QTreeWidgetItemIterator,
                             QDialog, QGridLayout, QColorDialog, QPushButton, QSizePolicy,
                             QFileIconProvider, QStyle, QMenu, QScrollArea, QButtonGroup,
                             QRadioButton, QAbstractSpinBox, QSlider)
from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtCore import Qt, QModelIndex, QRectF, QRect, QEvent, QMimeData, QSettings, QFileInfo, QUrl
from PyQt5.QtGui import (QPainter, QPainterPath, QBrush, QColor, QIcon, QPen,
                         QFontMetrics, QStandardItemModel,
                         QStandardItem, QDrag, QClipboard, QKeySequence, QDesktopServices)


"""自定义代理：绘制制圆角彩色块高亮"""
class HighlightDelegate(QStyledItemDelegate):
    """自定义代理：绘制制圆角彩色块高亮"""
    def __init__(self, colors, parent=None, is_right_side=False):
        super().__init__(parent)
        self.colors = colors
        self.highlight_enabled = True
        self.highlight_intensity = 0.7
        self.is_right_side = is_right_side  # 标识是否为右侧树视图

    def set_highlight_enabled(self, enabled):
        self.highlight_enabled = enabled

    def set_highlight_intensity(self, intensity):
        self.highlight_intensity = intensity

    def createEditor(self, parent, option, index):
        """创建编辑器，保持原始高度避免偏移"""
        editor = QLineEdit(parent)
        # 使用原始高度，避免偏移
        editor.setFixedHeight(option.rect.height())
        
        # 重写上下文菜单，翻译为中文
        def contextMenuEvent(event):
            menu = editor.createStandardContextMenu()
            
            # 翻译菜单项
            actions = menu.actions()
            for action in actions:
                text = action.text()
                # 映射英文到中文
                translations = {
                    "&Undo": "撤销(&U)",
                    "&Redo": "重做(&R)",
                    "Cu&t": "剪切(&T)",
                    "&Copy": "复制(&C)",
                    "&Paste": "粘贴(&P)",
                    "Delete": "删除",
                    "Select All": "全选"
                }
                
                for eng, chn in translations.items():
                    if eng in text:
                        action.setText(text.replace(eng, chn))
                        break
            
            menu.exec_(event.globalPos())
        
        # 替换原来的上下文菜单方法
        editor.contextMenuEvent = contextMenuEvent
        
        return editor

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何位置，确保与绘制时一致"""
        # 路径列（第3列）使用不同的位置计算，避免向右偏移
        if index.column() == 3:
            # 路径列直接使用option.rect.x()，与paint方法一致
            x = option.rect.x()
            width = option.rect.width()
        else:
            # 文件名列（第2列）使用与paint方法一致的位置计算
            margin = 4  # 与paint方法中的边距一致
            icon_size = option.decorationSize
            if icon_size.isEmpty():
                icon_size = QSize(16, 16)
            
            if index.data(Qt.DecorationRole):
                # 有图标时的位置
                x = option.rect.x() + margin + icon_size.width() + 2
                width = option.rect.width() - margin - icon_size.width() - 2
            else:
                # 无图标时的位置
                x = option.rect.x() + margin
                width = option.rect.width() - margin * 2
        
        # 使用原始高度，避免偏移
        y = option.rect.y()
        height = option.rect.height()
        
        editor.setGeometry(QRect(x, y, width, height))

    def setEditorData(self, editor, index):
        """设置编辑器数据"""
        text = index.data(Qt.DisplayRole) or ""
        editor.setText(text)
        editor.selectAll()  # 全选文本，方便直接编辑

    def setModelData(self, editor, model, index):
        """将编辑器数据设置回模型"""
        model.setData(index, editor.text(), Qt.EditRole)

    def paint(self, painter, option, index):
        if not self.highlight_enabled:
            # 高亮禁用时调用父类方法
            super().paint(painter, option, index)
            return

        # 处理箭头列（第1列）
        if index.column() == 1:
            painter.save()
            
            # 绘制背景
            painter.fillRect(option.rect, Qt.white)  # 白色背景
            
            # 检查是否需要绘制菱形（右键菜单悬停状态）
            is_context_menu_hover = (option.state & QStyle.State_MouseOver) and (option.state & QStyle.State_Selected)
            
            # 同步悬停状态 - 如果另一侧树有悬停，当前树也显示菱形
            if not is_context_menu_hover and option.state & QStyle.State_Selected:
                current_row = index.row()
                # 获取主窗口对象
                main_window = None
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'left_hover_row') and hasattr(parent, 'right_hover_row'):
                        main_window = parent
                        break
                    parent = parent.parent()
                
                if main_window:
                    if self.is_right_side:
                        # 右侧树：检查左侧悬停行
                        if main_window.left_hover_row == current_row:
                            is_context_menu_hover = True
                    else:
                        # 左侧树：检查右侧悬停行
                        if main_window.right_hover_row == current_row:
                            is_context_menu_hover = True
            
            if option.state & QStyle.State_Selected or is_context_menu_hover:
                # 选中状态或右键菜单悬停状态绘制图形
                arrow_size = 16  # 恢复原来的箭头大小
                center_x = option.rect.x() + option.rect.width() // 2
                center_y = option.rect.y() + option.rect.height() // 2
                
                # 创建路径
                path = QPainterPath()
                
                if is_context_menu_hover:
                    # 右键菜单悬停状态绘制菱形
                    path.moveTo(center_x, center_y - arrow_size // 2)  # 上顶点
                    path.lineTo(center_x + arrow_size // 2, center_y)  # 右顶点
                    path.lineTo(center_x, center_y + arrow_size // 2)  # 下顶点
                    path.lineTo(center_x - arrow_size // 2, center_y)  # 左顶点
                    path.closeSubpath()
                else:
                    # 普通选中状态绘制三角箭头
                    path.moveTo(center_x - arrow_size // 2, center_y - arrow_size // 2)
                    path.lineTo(center_x + arrow_size // 2, center_y)
                    path.lineTo(center_x - arrow_size // 2, center_y + arrow_size // 2)
                    path.closeSubpath()
                
                # 填充图形 - 右侧树视图显示红色，左侧显示蓝色
                if self.is_right_side:
                    painter.setBrush(QBrush(QColor(220, 53, 69)))  # 红色
                else:
                    painter.setBrush(QBrush(QColor(0, 120, 215)))  # 蓝色
                painter.setPen(Qt.NoPen)
                painter.drawPath(path)
            
            painter.restore()
            return

        # 编号列、路径列、最右边的编号列不高亮显示
        if index.column() in [0, 3, 4]:
            # 这些列只绘制白色背景，不高亮
            painter.save()
            painter.fillRect(option.rect, Qt.white)
            
            # 绘制文本
            text = index.data() or ""
            if text:
                painter.setPen(QPen(Qt.black))
                painter.setFont(option.font)
                # 垂直居中绘制文本
                metrics = QFontMetrics(option.font)
                text_y = option.rect.y() + (option.rect.height() - metrics.height()) // 2
                painter.drawText(option.rect.x(), text_y + metrics.ascent(), text)
            
            painter.restore()
            return

        if index.column() == 2:  # 只处理文件名列（现在是第2列）
            # 获取高亮信息
            highlight_info = index.data(Qt.UserRole + 1)
            if not highlight_info:
                # 没有高亮信息，显示原始文本
                text = index.data() or ""
                if text:
                    highlight_info = [(text, None)]  # 将原始文本作为普通文本显示
                else:
                    # 没有文本，调用父类方法
                    super().paint(painter, option, index)
                    return

            painter.save()
            
            # 绘制背景 - 移除选中高亮，只保留鼠标悬停效果
            if option.state & QStyle.State_MouseOver:
                painter.fillRect(option.rect, QColor(240, 240, 240))
            else:
                painter.fillRect(option.rect, Qt.white)
            
            # 使用QStyle的标准方法来处理图标和文本布局，确保与编辑器一致
            # 获取标准图标大小和文本矩形
            icon_size = option.decorationSize
            if icon_size.isEmpty():
                icon_size = QSize(16, 16)  # 默认16x16
            
            # 使用QStyle的标准计算方式来确保与编辑器一致
            icon_rect = QRect()
            text_rect = QRect()
            
            # 获取标准边距，确保与Qt默认编辑器一致
            margin = 4  # Qt标准边距
            total_rect = option.rect
            
            if index.data(Qt.DecorationRole):
                # 有图标时，使用标准间距
                icon_rect = QRect(total_rect.x() + margin, 
                                total_rect.y() + (total_rect.height() - icon_size.height()) // 2,
                                icon_size.width(), icon_size.height())
                text_rect = QRect(total_rect.x() + margin + icon_size.width() + 2,  # 图标后加2像素间距
                                total_rect.y(),
                                total_rect.width() - margin - icon_size.width() - 2,
                                total_rect.height())
            else:
                # 无图标时，文本从标准位置开始
                text_rect = QRect(total_rect.x() + margin,
                                total_rect.y(),
                                total_rect.width() - margin * 2,
                                total_rect.height())
            
            # 绘制图标
            icon = index.data(Qt.DecorationRole)
            if icon and isinstance(icon, QIcon):
                icon.paint(painter, icon_rect)
            
            # 获取字体度量
            metrics = QFontMetrics(option.font)
            
            # 绘制高亮文本 - 使用与Qt编辑器一致的起始位置
            x = text_rect.x()
            y = text_rect.y()
            text_height = text_rect.height()
            
            # 预先计算所有文本段的宽度和位置，避免重叠间隙
            text_segments = []
            current_x = x
            for i, (text, role) in enumerate(highlight_info):
                if not text:
                    text_segments.append((text, role, current_x, 0))
                    continue
                    
                text_width = metrics.horizontalAdvance(text)
                text_segments.append((text, role, current_x, text_width))
                current_x += text_width
            
            # 绘制背景 - 先绘制所有背景，再绘制文本，避免重叠时的缺口
            # 将相邻的相同角色矩形合并绘制，消除缺口
            merged_segments = []
            i = 0
            while i < len(text_segments):
                text, role, seg_x, text_width = text_segments[i]
                if not text or not role or role not in self.colors:
                    merged_segments.append((text, role, seg_x, text_width, False, False))
                    i += 1
                    continue
                
                # 检查是否可以与下一个合并
                start_x = seg_x
                total_width = text_width
                can_merge_prev = False
                can_merge_next = False
                
                # 检查前一个是否相同角色
                if i > 0 and text_segments[i-1][1] == role:
                    can_merge_prev = True
                
                # 检查后一个是否相同角色并合并
                j = i + 1
                while j < len(text_segments):
                    next_text, next_role, next_seg_x, next_text_width = text_segments[j]
                    if next_role == role and next_text and next_role in self.colors:
                        total_width += next_text_width
                        j += 1
                    else:
                        break
                
                # 检查后一个是否相同角色
                if j < len(text_segments) and text_segments[j][1] == role:
                    can_merge_next = True
                
                merged_segments.append((text, role, start_x, total_width, can_merge_prev, can_merge_next))
                i = j
            
            # 绘制合并后的矩形
            for text, role, seg_x, total_width, can_merge_prev, can_merge_next in merged_segments:
                if not text or not role or role not in self.colors:
                    continue
                    
                # 垂直居中
                text_y = y + (text_height - metrics.height()) // 2
                current_text_rect = QRect(seg_x, text_y, total_width, metrics.height())
                
                # 绘制彩色背景
                base_color = self.colors[role]
                # 调整颜色强度
                alpha = int(self.highlight_intensity * 255)
                highlight_color = QColor(base_color)
                highlight_color.setAlpha(alpha)
                
                # 根据合并情况绘制矩形
                path = QPainterPath()
                if can_merge_prev and can_merge_next:
                    # 中间矩形，使用矩形
                    path.addRect(QRectF(current_text_rect))
                elif can_merge_prev:
                    # 右侧结束，左边直角右边圆角
                    rect = QRectF(current_text_rect)
                    path.moveTo(rect.left(), rect.top())
                    path.lineTo(rect.right() - 4, rect.top())
                    path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + 4)
                    path.lineTo(rect.right(), rect.bottom() - 4)
                    path.quadTo(rect.right(), rect.bottom(), rect.right() - 4, rect.bottom())
                    path.lineTo(rect.left(), rect.bottom())
                    path.closeSubpath()
                elif can_merge_next:
                    # 左侧开始，左边圆角右边直角
                    rect = QRectF(current_text_rect)
                    path.moveTo(rect.right(), rect.top())
                    path.lineTo(rect.left() + 4, rect.top())
                    path.quadTo(rect.left(), rect.top(), rect.left(), rect.top() + 4)
                    path.lineTo(rect.left(), rect.bottom() - 4)
                    path.quadTo(rect.left(), rect.bottom(), rect.left() + 4, rect.bottom())
                    path.lineTo(rect.right(), rect.bottom())
                    path.closeSubpath()
                else:
                    # 独立矩形，使用圆角
                    path.addRoundedRect(QRectF(current_text_rect), 4, 4)
                
                painter.setBrush(highlight_color)
                painter.setPen(Qt.NoPen)
                painter.drawPath(path)
            
            # 绘制文本 - 在所有背景绘制完成后统一绘制文本
            for text, role, seg_x, text_width in text_segments:
                if not text:
                    continue
                    
                # 垂直居中
                text_y = y + (text_height - metrics.height()) // 2
                current_text_rect = QRect(seg_x, text_y, text_width, metrics.height())
                
                if role and role in self.colors:
                    # 设置白色字体
                    painter.setPen(QPen(Qt.white))
                else:
                    # 普通文本使用黑色字体
                    painter.setPen(QPen(Qt.black))
                
                # 绘制文本
                painter.setFont(option.font)
                painter.drawText(current_text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
            
            painter.restore()
        else:
            # 其他列调用父类方法
            super().paint(painter, option, index)


class FolderDropDialog(QDialog):
    """文件夹拖放处理对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择处理模式")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self.selected_mode = None
        self.recursive_checked = False
        
        self._build_ui()
    
    def _build_ui(self):
        """构建对话框界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 第一行：询问文字
        label = QLabel("请选择要处理的内容：")
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(label)
        
        # 第二行：两个并列按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 文件名按钮
        self.file_button = QPushButton("文件名")
        self.file_button.setFixedHeight(35)
        self.file_button.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                padding: 8px 15px;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        button_layout.addWidget(self.file_button)
        
        # 文件夹名按钮
        self.folder_button = QPushButton("文件夹名")
        self.folder_button.setFixedHeight(35)
        self.folder_button.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                padding: 8px 15px;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        button_layout.addWidget(self.folder_button)
        
        layout.addLayout(button_layout)
        
        # 第三行：勾选框居中
        recursive_layout = QHBoxLayout()
        recursive_layout.addStretch()
        self.recursive_cb = QCheckBox("递归处理子文件夹")
        self.recursive_cb.setChecked(True)
        recursive_layout.addWidget(self.recursive_cb)
        recursive_layout.addStretch()
        layout.addLayout(recursive_layout)
        
        # 说明标签
        self.desc_label = QLabel("点击'文件名'按钮将导入文件夹内部的所有文件")
        self.desc_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 10px;")
        self.desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.desc_label)
        
        layout.addStretch()
        
        # 连接按钮点击事件
        self.file_button.clicked.connect(self._on_file_selected)
        self.folder_button.clicked.connect(self._on_folder_selected)
    
    def _update_description(self):
        """更新说明文字"""
        # 这个方法现在不需要了，因为按钮点击会直接处理
    
    # 移除了_on_ok方法，现在使用按钮直接选择
    
    def _on_file_selected(self):
        """选择文件名模式"""
        self.selected_mode = "files"
        self.recursive_checked = self.recursive_cb.isChecked()
        self.accept()
    
    def _on_folder_selected(self):
        """选择文件夹名模式"""
        self.selected_mode = "folders"
        self.recursive_checked = self.recursive_cb.isChecked()
        self.accept()


"""颜色配置对话框"""
class ColorConfigDialog(QDialog):
    """颜色配置对话框：允许用户自定义不同操作类型的高亮颜色"""
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高亮颜色配置")
        self.setModal(True)
        self.colors = colors.copy()
        self.color_buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建网格布局用于颜色配置
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        
        # 颜色配置项
        color_items = [
            ("prefix", "前缀"),
            ("suffix", "后缀"),
            ("replace", "替换"),
            ("number", "编号"),
            ("delete", "删除"),
            ("case", "大小写"),
            ("find", "查找")
        ]
        
        row = 0
        for role, label_text in color_items:
            # 创建标签
            label = QLabel(f"{label_text}颜色:")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.grid_layout.addWidget(label, row, 0)
            
            # 创建颜色显示按钮（菱形样式）
            color_btn = QPushButton()
            color_btn.setFixedSize(25, 25)
            color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors[role].name()};
                    border: 1px solid #666;
                    border-radius: 0px;
                }}
                QPushButton:hover {{
                    border: 2px solid #333;
                }}
            """)
            color_btn.setMask(self.create_diamond_mask(25))
            color_btn.clicked.connect(lambda checked, r=role: self._choose_color(r))
            self.color_buttons[role] = color_btn
            self.grid_layout.addWidget(color_btn, row, 1)
            
            # 创建颜色名称显示
            color_name = QLabel(self.colors[role].name())
            color_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            color_name.setStyleSheet("font-family: monospace;")
            self.grid_layout.addWidget(color_name, row, 2)
            
            row += 1
        
        layout.addLayout(self.grid_layout)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 恢复默认按钮
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # 确定和取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.resize(400, 300)

    def _choose_color(self, role):
        """选择颜色"""
        current_color = self.colors[role]
        color = QColorDialog.getColor(current_color, self, f"选择{self._get_role_name(role)}颜色")
        
        if color.isValid():
            self.colors[role] = color
            self.color_buttons[role].setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    border: 1px solid #666;
                    border-radius: 0px;
                }}
                QPushButton:hover {{
                    border: 2px solid #333;
                }}
            """)
            # 更新颜色名称显示
            color_name_label = self.grid_layout.itemAtPosition(list(self.color_buttons.keys()).index(role), 2).widget()
            color_name_label.setText(color.name())

    def _reset_defaults(self):
        """恢复默认颜色"""
        default_colors = {
            "prefix": QColor("#FFD700"),    # 金色 - 前缀
            "suffix": QColor("#87CEFA"),    # 浅蓝色 - 后缀
            "replace": QColor("#90EE90"),   # 浅绿色 - 替换
            "number": QColor("#FFB6C1"),    # 浅粉色 - 编号
            "delete": QColor("#FFFACD"),    # 浅黄色 - 删除
            "case": QColor("#F5F5DC"),      # 米色 - 大小写
            "find": QColor("#FFFF00")       # 黄色 - 查找
        }
        
        self.colors.update(default_colors)
        
        # 更新UI
        for role, color in default_colors.items():
            self.color_buttons[role].setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    border: 1px solid #666;
                    border-radius: 0px;
                }}
                QPushButton:hover {{
                    border: 2px solid #333;
                }}
            """)
            # 更新颜色名称显示
            color_name_label = self.grid_layout.itemAtPosition(list(self.color_buttons.keys()).index(role), 2).widget()
            color_name_label.setText(color.name())

    def create_diamond_mask(self, size):
        """创建菱形裁剪区域"""
        from PyQt5.QtGui import QPolygon, QRegion
        from PyQt5.QtCore import QPoint
        
        # 创建菱形多边形
        polygon = QPolygon([
            QPoint(size // 2, 0),           # 顶点
            QPoint(size, size // 2),        # 右点
            QPoint(size // 2, size),        # 底点
            QPoint(0, size // 2)            # 左点
        ])
        
        return QRegion(polygon)

    def _get_role_name(self, role):
        """获取角色的中文名称"""
        role_names = {
            "prefix": "前缀",
            "suffix": "后缀",
            "replace": "替换",
            "number": "编号",
            "number_prefix": "编号前缀",
            "number_suffix": "编号后缀",
            "delete": "删除",
            "case": "大小写",
            "find": "查找"
        }
        return role_names.get(role, role)

    def get_colors(self):
        """获取配置的颜色"""
        return self.colors.copy()


class BatchRenameWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.file_data: List[Tuple[str, str, Dict]] = []  # (src_path_str, original_name, processed_info)
        self.original_file_data: List[Tuple[str, str, Dict]] = []  # 备份原始文件数据
        self.removed_items = []
        self.last_undo_stack = deque(maxlen=20)
        self.sync_vertical_enabled = True
        self.sync_horizontal_enabled = True
        self.sync_column_enabled = True
        
        # 悬停行同步跟踪
        self.left_hover_row = -1
        self.right_hover_row = -1
        
        # 常量定义
        self.COLUMN_WIDTHS = [40, 290, 1400, 40]  # 列宽配置
        self.ICON_WIDTH = 20  # 图标宽度
        self.MIN_WIDGET_WIDTH = 120  # 最小控件宽度
        
        # 加载颜色配置
        self.load_color_config()

        self._setup_ui()

        # 同步滚动
        self.left_tree.verticalScrollBar().valueChanged.connect(self.sync_vertical)
        self.right_tree.verticalScrollBar().valueChanged.connect(self.sync_vertical)
        self.left_tree.horizontalScrollBar().valueChanged.connect(self.sync_horizontal)
        self.right_tree.horizontalScrollBar().valueChanged.connect(self.sync_horizontal)

        self.find_edit.textChanged.connect(self._update_find_highlight)
        self.match_mode.currentIndexChanged.connect(self._update_find_highlight)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 0)
        layout.setSpacing(0)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(5)

        # 左侧树
        self.left_tree = QTreeView()
        self.left_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.left_tree.setRootIsDecorated(False)
        self.left_tree.setIndentation(0)
        # 禁用自动滚动到最左侧
        self.left_tree.setAutoScroll(False)
        
        # 左侧模型 - 添加箭头列
        self.left_model = QStandardItemModel(0, 5)
        self.left_model.setHorizontalHeaderLabels(["编号", "", "原始目标名", "路径", "编号"])
        self.left_tree.setModel(self.left_model)
        
        # 设置列宽 - 箭头列宽度刚好放下箭头
        self.left_tree.setColumnWidth(0, 40)
        self.left_tree.setColumnWidth(1, 20)  # 箭头列，刚好放下三角箭头
        self.left_tree.setColumnWidth(2, 270)  # 原始目标名列稍微减小
        self.left_tree.setColumnWidth(3, 1400)
        self.left_tree.setColumnWidth(4, 40)
        
        # 设置列拉伸模式
        header = self.left_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 箭头列固定宽度
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setCascadingSectionResizes(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(2, 2, 2, 2)
        left_layout.setSpacing(0)
        left_buttons = QHBoxLayout()
        left_buttons.setContentsMargins(0, 0, 0, 0)
        btn_add_folder = QPushButton("添加文件夹")
        btn_add_files = QPushButton("添加文件")
        btn_clear = QPushButton("清空")
        # self.recursive_cb = QCheckBox("递归")
        # self.recursive_cb.setChecked(True)
        left_buttons.addWidget(btn_add_folder)
        left_buttons.addWidget(btn_add_files)
        left_buttons.addWidget(btn_clear)
        # left_buttons.addWidget(self.recursive_cb)
        left_layout.addLayout(left_buttons)
        left_layout.addWidget(self.left_tree)
        btn_add_folder.clicked.connect(self.on_add_folder)
        btn_add_files.clicked.connect(self.on_add_files)
        btn_clear.clicked.connect(self.on_clear)
        left_panel.setMinimumWidth(100)

        # 右侧树（预览）
        self.right_tree = QTreeView()
        self.right_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.right_tree.setRootIsDecorated(False)
        self.right_tree.setIndentation(0)
        # 禁用自动滚动到最左侧
        self.right_tree.setAutoScroll(False)
        
        # 右侧模型 - 添加箭头列
        self.right_model = QStandardItemModel(0, 5)
        self.right_model.setHorizontalHeaderLabels(["编号", "", "新目标名", "路径", "编号"])
        self.right_tree.setModel(self.right_model)
        
        # 设置自定义代理 - 右侧树视图使用红色箭头
        self.right_delegate = HighlightDelegate(self.colors, self, is_right_side=True)
        self.right_tree.setItemDelegate(self.right_delegate)
        
        # 为左侧树也设置相同的代理 - 左侧树视图使用蓝色箭头
        self.left_delegate = HighlightDelegate(self.colors, self, is_right_side=False)
        self.left_tree.setItemDelegate(self.left_delegate)
        
        # 连接选中行变化信号，实现箭头同步显示
        self.left_tree.selectionModel().selectionChanged.connect(self.on_left_selection_changed)
        self.right_tree.selectionModel().selectionChanged.connect(self.on_right_selection_changed)
        
        # 启用鼠标跟踪以支持悬停同步
        self.left_tree.setMouseTracking(True)
        self.right_tree.setMouseTracking(True)
        self.left_tree.viewport().setMouseTracking(True)
        self.right_tree.viewport().setMouseTracking(True)
        
        # 连接鼠标移动事件
        self.left_tree.viewport().installEventFilter(self)
        self.right_tree.viewport().installEventFilter(self)
        
        # 设置右键菜单策略
        self.left_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.right_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # 连接右键菜单信号
        self.left_tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        self.right_tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        
        # 设置列宽 - 箭头列宽度刚好放下箭头
        self.right_tree.setColumnWidth(0, 40)
        self.right_tree.setColumnWidth(1, 20)  # 箭头列，刚好放下三角箭头
        self.right_tree.setColumnWidth(2, 270)  # 新目标名列稍微减小
        self.right_tree.setColumnWidth(3, 1400)
        self.right_tree.setColumnWidth(4, 40)
        
        # 设置列拉伸模式
        header = self.right_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 箭头列固定宽度
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setCascadingSectionResizes(False)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(0)
        right_buttons = QHBoxLayout()
        right_buttons.setContentsMargins(0, 0, 0, 0)
        btn_apply_one = QPushButton("逐一应用")
        btn_apply_all = QPushButton("应用全部")
        btn_undo = QPushButton("撤销上一次")
        right_buttons.addWidget(btn_apply_one)
        right_buttons.addWidget(btn_apply_all)
        right_buttons.addWidget(btn_undo)
        right_layout.addLayout(right_buttons)
        right_layout.addWidget(self.right_tree)
        btn_apply_one.clicked.connect(self.on_apply_one)
        btn_apply_all.clicked.connect(self.on_apply_all)
        btn_undo.clicked.connect(self.on_undo)
        right_panel.setMinimumWidth(100)

        self.splitter.addWidget(left_panel)

        # 中间参数区 - 使用滚动区域
        self.center = QFrame()
        self.center.setMinimumWidth(300)  # 增加最小宽度以适应组框内容
        # 移除最大宽度限制，允许中间区域根据需要扩展
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用横向滚动条
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)   # 需要时显示竖向滚动条
        scroll_area.setFrameShape(QFrame.NoFrame)  # 移除边框
        
        # 设置滚动条样式 - 更细的滚动条
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 创建中间内容容器
        center_content = QWidget()
        center_layout = QVBoxLayout(center_content)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # 将滚动区域添加到中间框架
        center_frame_layout = QVBoxLayout(self.center)
        center_frame_layout.setContentsMargins(0, 0, 0, 0)
        center_frame_layout.setSpacing(0)
        center_frame_layout.addWidget(scroll_area)
        
        # 设置滚动区域的widget
        scroll_area.setWidget(center_content)

        # 定义辅助函数
        def create_group(title):
            group = QGroupBox(title)
            group.setAlignment(Qt.AlignCenter)  # 组标题居中
            # 设置组框的最小宽度，整体降低30以更紧凑
            group.setMinimumWidth(270)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(3, 3, 3, 3)
            group_layout.setSpacing(3)
            return group, group_layout

        def add_row(label_text, widgets, layout):
            row = QHBoxLayout()
            row.setSpacing(0)  # 间距设为0，紧贴布局
            row.setAlignment(Qt.AlignLeft)
            label = QLabel(label_text)
            label.setFixedWidth(80)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(label)
            for i, w in enumerate(widgets):
                row.addWidget(w)
                if isinstance(w, QLineEdit) or isinstance(w, QSpinBox) or isinstance(w, QComboBox):
                    w.setMinimumWidth(120)
                    if isinstance(w, QComboBox):
                        w.setMinimumWidth(160)
                    # 让所有输入控件扩展填充剩余空间
                    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addLayout(row)

        def add_color_row(label_text, widgets, color_btn, layout):
            """带颜色按钮的行布局，颜色按钮紧贴冒号，输入控件紧贴颜色按钮"""
            row = QHBoxLayout()
            row.setSpacing(0)  # 间距设为0，紧贴布局
            row.setAlignment(Qt.AlignLeft)
            
            # 创建标签和颜色按钮的容器
            label_container = QWidget()
            label_layout = QHBoxLayout(label_container)
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.setSpacing(0)  # 标签和颜色按钮之间无间距
            
            # 创建标签（统一长度以确保对齐）
            label_part = label_text.replace("：", "")
            # 统一标签长度，确保所有标签占用相同空间
            if len(label_part) == 2:  # 如"替换为"
                label_part = label_part + "　　"  # 添加2个全角空格
            elif len(label_part) == 3:  # 如"查找内容"
                label_part = label_part + "　"   # 添加1个全角空格
            
            label = QLabel(label_part + "：")  # 重新添加冒号
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # 不设置固定宽度，让标签根据文本长度自适应
            label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            label_layout.addWidget(label)
            
            # 添加颜色按钮（缩小到20x20）
            color_btn.setFixedSize(20, 20)
            label_layout.addWidget(color_btn)
            
            row.addWidget(label_container)
            
            # 添加输入控件
            for i, w in enumerate(widgets):
                row.addWidget(w)
                if isinstance(w, QLineEdit) or isinstance(w, QSpinBox) or isinstance(w, QComboBox):
                    w.setMinimumWidth(120)
                    if isinstance(w, QComboBox):
                        w.setMinimumWidth(160)
                    # 让输入控件扩展填充剩余空间
                    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addLayout(row)

        def add_indent_row(label_text, widgets, layout, color_btn=None):
            row = QHBoxLayout()
            row.setSpacing(0)  # 间距设为0，紧贴布局
            row.setAlignment(Qt.AlignLeft)
            row.addSpacing(0)
            
            if color_btn:
                # 创建标签和颜色按钮的容器
                label_container = QWidget()
                label_layout = QHBoxLayout(label_container)
                label_layout.setContentsMargins(0, 0, 0, 0)
                label_layout.setSpacing(0)  # 标签和颜色按钮之间无间距
                
                # 创建标签
                label = QLabel(label_text)
                label.setFixedWidth(80)
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                label_layout.addWidget(label)
                
                # 添加颜色按钮（缩小到20x20）
                color_btn.setFixedSize(20, 20)
                label_layout.addWidget(color_btn)
                
                row.addWidget(label_container)
            else:
                label = QLabel(label_text)
                label.setFixedWidth(80)
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                row.addWidget(label)
            
            for i, w in enumerate(widgets):
                row.addWidget(w)
                if isinstance(w, QLineEdit) or isinstance(w, QSpinBox) or isinstance(w, QComboBox):
                    w.setMinimumWidth(120)
                    if isinstance(w, QComboBox):
                        w.setMinimumWidth(150)
                    # 让所有输入控件扩展填充剩余空间
                    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addLayout(row)

        def add_connected_rows(label_text, top_widget, bottom_widget, layout):
            row = QHBoxLayout()
            row.setSpacing(0)  # 水平间距设为0，紧贴布局
            row.setAlignment(Qt.AlignLeft)
            label = QLabel(label_text)
            label.setFixedWidth(80)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(label)
            right_container = QWidget()
            right_layout = QVBoxLayout(right_container)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(3)  # 保持垂直间距为3
            right_layout.addWidget(top_widget)
            right_layout.addSpacing(3)  # 保持垂直间距为3
            right_layout.addWidget(bottom_widget)
            # 让输入控件扩展填充剩余空间
            if isinstance(top_widget, (QLineEdit, QComboBox)):
                top_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if isinstance(bottom_widget, (QLineEdit, QComboBox)):
                bottom_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(right_container)
            layout.addLayout(row)

        # 同步组
        sync_group = QGroupBox("同步")
        sync_group.setAlignment(Qt.AlignCenter)
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setContentsMargins(3, 3, 3, 3)
        sync_layout.setSpacing(3)

        # 使用add_row函数添加同步复选框
        self.sync_v_cb = QCheckBox("纵向")
        self.sync_v_cb.setChecked(True)
        self.sync_h_cb = QCheckBox("横向")
        self.sync_h_cb.setChecked(True)
        self.sync_column_cb = QCheckBox("列宽")
        self.sync_column_cb.setChecked(True)
        
        # 创建一个容器来放置三个复选框
        sync_container = QWidget()
        sync_container_layout = QHBoxLayout(sync_container)
        sync_container_layout.setContentsMargins(0, 0, 0, 0)
        sync_container_layout.setSpacing(10)
        sync_container_layout.addStretch()  # 左侧弹性空间
        sync_container_layout.addWidget(self.sync_v_cb)
        sync_container_layout.addWidget(self.sync_h_cb)
        sync_container_layout.addWidget(self.sync_column_cb)
        sync_container_layout.addStretch()  # 右侧弹性空间
        
        # 直接添加复选框容器，不显示标签
        sync_layout.addWidget(sync_container)
        # 创建统一的控件容器
        self.top_inputs = QWidget()
        top_inputs_layout = QVBoxLayout(self.top_inputs)
        top_inputs_layout.setAlignment(Qt.AlignTop)
        top_inputs_layout.setSpacing(3)
        
        # 将同步组添加到顶部容器
        top_inputs_layout.addWidget(sync_group)
        self.sync_v_cb.stateChanged.connect(self.on_sync_vertical_toggled)
        self.sync_h_cb.stateChanged.connect(self.on_sync_horizontal_toggled)
        self.sync_column_cb.stateChanged.connect(self.on_sync_column_toggled)

        # 功能控件
        self.inputs = QWidget()
        inputs_layout = QVBoxLayout(self.inputs)
        inputs_layout.setAlignment(Qt.AlignTop)
        inputs_layout.setSpacing(3)

        # 筛选目标
        filter_group = QGroupBox("筛选目标")
        filter_group.setAlignment(Qt.AlignCenter)
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setContentsMargins(3, 3, 3, 3)
        filter_layout.setSpacing(3)
        
        # 使用add_row函数添加筛选控件
        self.filter_mode_combo = QComboBox()
        self.filter_mode_combo.addItems(["前缀", "后缀", "包含关键词", "正则匹配"])
        add_row("筛选模式：", [self.filter_mode_combo], filter_layout)
        
        self.filter_pattern_edit = QLineEdit()
        self.filter_pattern_edit.setPlaceholderText("输入筛选模式内容")
        add_row("筛选内容：", [self.filter_pattern_edit], filter_layout)
        
        self.skip_mode_combo = QComboBox()
        self.skip_mode_combo.addItems(["前缀", "后缀", "包含关键词", "正则匹配"])
        add_row("跳过模式：", [self.skip_mode_combo], filter_layout)
        
        self.skip_pattern_edit = QLineEdit()
        self.skip_pattern_edit.setPlaceholderText("输入跳过模式内容")
        add_row("跳过内容：", [self.skip_pattern_edit], filter_layout)
        
        # 直接添加按钮到布局 - 占满整个组框宽度
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)
        
        self.apply_filter_btn = QPushButton("筛选")
        self.apply_filter_btn.clicked.connect(self.on_apply_new_filter)
        self.reset_filter_btn = QPushButton("重置")
        self.reset_filter_btn.clicked.connect(self.on_reset_filter)
        
        # 设置按钮扩展填充可用空间
        self.apply_filter_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_filter_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        btn_layout.addWidget(self.apply_filter_btn)
        btn_layout.addWidget(self.reset_filter_btn)
        
        # 添加到底部，占满整个宽度
        filter_layout.addLayout(btn_layout)
        filter_layout.addStretch()  # 添加弹性空间确保按钮在底部
        
        # 将筛选组也添加到顶部容器
        top_inputs_layout.addWidget(filter_group)

        # 高亮设置 - 移到筛选组后面，紧贴筛选组
        highlight_group, highlight_layout = create_group("高亮设置")
        self.highlight_enabled = QCheckBox()
        self.highlight_enabled.setChecked(True)
        
        # 创建启用行，勾选框与“启用”文字0距离紧贴
        enable_row = QHBoxLayout()
        enable_row.setSpacing(0)  # 间距设为0，紧贴布局
        enable_row.setAlignment(Qt.AlignLeft)
        enable_row.addWidget(self.highlight_enabled)
        label_enable = QLabel("启用")
        label_enable.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        enable_row.addWidget(label_enable)
        enable_row.addStretch()  # 添加弹性空间，让勾选框靠左
        highlight_layout.addLayout(enable_row)
        self.highlight_intensity = QSpinBox()
        self.highlight_intensity.setRange(30, 90)
        self.highlight_intensity.setValue(70)
        self.highlight_intensity.setSuffix("%")
        add_row("高亮强度：", [self.highlight_intensity], highlight_layout)
        # 查找高亮颜色按钮已移至查找内容输入框旁
        top_inputs_layout.addWidget(highlight_group)

        # 中间宽度滑条容器（纯 QWidget，无边框无标题）- 放在查找替换组上方
        self.width_group = QWidget()
        width_group_layout = QHBoxLayout(self.width_group)
        width_group_layout.setContentsMargins(3, 3, 3, 3)
        width_group_layout.setSpacing(0)
        width_label = QLabel("中间宽度：")
        width_label.setFixedWidth(80)
        width_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        width_group_layout.addWidget(width_label)
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(300, 675)  # 范围整体降低50
        self.width_slider.setValue(300)  # 默认启动时为最小值
        self.width_slider.setMinimumWidth(120)
        self.width_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # 设置滑条样式表，将手柄改窄并添加填充颜色效果
        self.width_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 10px;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #666, stop:1 #aaa);
                border: 1px solid #5c5c5c;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #666, stop:1 #aaa);
                border: 1px solid #5c5c5c;
                width: 8px;
                height: 20px;
                margin: -5px 0;
                border-radius: 0px;
            }
            
            /* 整体向下移动2像素以与文字对齐 */
            QSlider {
                margin-top: 2px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #888, stop:1 #ccc);
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #555, stop:1 #999);
            }
        """)
        width_group_layout.addWidget(self.width_slider)
        self.width_value_label = QLabel(str(self.width_slider.value()))
        self.width_value_label.setFixedWidth(40)
        self.width_value_label.setAlignment(Qt.AlignCenter)
        width_group_layout.addWidget(self.width_value_label)
        top_inputs_layout.addWidget(self.width_group)

        # 查找替换 - 移到顶部容器，紧挨着高亮设置组
        find_group, find_layout = create_group("查找替换")
        # 减小组内行距，让“匹配模式”和“配对数量”更紧贴
        find_layout.setSpacing(2)
        

        
        # 匹配模式（位于多目标之后）
        self.match_mode = QComboBox()
        self.match_mode.addItems(["普通匹配", "正则匹配"])
        add_row("匹配模式：", [self.match_mode], find_layout)
        
        # 创建配对数量行（默认跟随多目标选项显示隐藏），对齐并缩小行距

        # 自定义一行以便后续显隐控制
        self.pair_count_row_widget = QWidget()
        pair_count_row = QHBoxLayout(self.pair_count_row_widget)
        pair_count_row.setSpacing(0)
        # 关键修复：为该行布局设置零边距以与其他行完全左对齐
        pair_count_row.setContentsMargins(0, 0, 0, 0)
        pair_count_row.setAlignment(Qt.AlignLeft)
        # 尽量贴近上一行（匹配模式）
        self.pair_count_row_widget.setContentsMargins(0, 0, 0, 0)
        pair_label = QLabel("配对数量：")
        pair_label.setFixedWidth(80)
        pair_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        pair_count_row.addWidget(pair_label)
        # 数字输入框左侧与上面的下拉框对齐，右侧自动顶满

        # 紧贴匹配模式行
        find_layout.addWidget(self.pair_count_row_widget)
        # 初始未勾选多目标时隐藏该行
        self.pair_count_row_widget.setVisible(False)
        
        #（宽度滑条已移动到查找替换组上方的独立组框中）
        
        # 单目标查找替换控件（默认显示）
        self.single_target_widget = QWidget()
        single_target_layout = QVBoxLayout(self.single_target_widget)
        single_target_layout.setContentsMargins(0, 0, 0, 0)
        single_target_layout.setSpacing(3)
        
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("输入要查找的内容")
        # 添加查找颜色按钮（菱形样式）
        self.find_color_btn = QPushButton()
        self.find_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['find'].name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.find_color_btn.setMask(self.create_diamond_mask(20))
        self.find_color_btn.clicked.connect(lambda: self._choose_color_direct("find"))
        add_color_row("查找内容：", [self.find_edit], self.find_color_btn, single_target_layout)
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("输入替换后的内容")
        # 添加替换颜色按钮（菱形样式）
        self.replace_color_btn = QPushButton()
        self.replace_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['replace'].name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        # 使用裁剪区域创建菱形效果
        self.replace_color_btn.setMask(self.create_diamond_mask(20))
        self.replace_color_btn.clicked.connect(lambda: self._choose_color_direct("replace"))
        add_color_row("替换为：", [self.replace_edit], self.replace_color_btn, single_target_layout)
        
        find_layout.addWidget(self.single_target_widget)
        
        # 多目标查找替换控件（默认隐藏）

        
        # 创建多目标输入框容器



        
        # 连接信号

        self.width_slider.valueChanged.connect(self._on_width_slider_changed)
        
        # 初始化多目标输入框

        
        top_inputs_layout.addWidget(find_group)

        # 前后缀 - 移到顶部容器，紧挨着查找替换组
        prefix_suffix_group, ps_layout = create_group("前后缀")
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("输入前缀内容")
        # 添加前缀颜色按钮（菱形样式）
        self.prefix_color_btn = QPushButton()
        self.prefix_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['prefix'].name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.prefix_color_btn.setMask(self.create_diamond_mask(20))
        self.prefix_color_btn.clicked.connect(lambda: self._choose_color_direct("prefix"))
        add_color_row("添加前缀：", [self.prefix_edit], self.prefix_color_btn, ps_layout)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("输入后缀内容")
        # 添加后缀颜色按钮（菱形样式）
        self.suffix_color_btn = QPushButton()
        self.suffix_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['suffix'].name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.suffix_color_btn.setMask(self.create_diamond_mask(20))
        self.suffix_color_btn.clicked.connect(lambda: self._choose_color_direct("suffix"))
        add_color_row("添加后缀：", [self.suffix_edit], self.suffix_color_btn, ps_layout)
        top_inputs_layout.addWidget(prefix_suffix_group)

        # 编号 - 移到顶部容器，紧挨着前后缀组
        number_group, number_layout = create_group("编号")
        self.enable_number_cb = QCheckBox()
        self.enable_number_cb.setChecked(False)
        # 添加编号颜色按钮（菱形样式）到启用编号复选框同一行
        self.number_color_btn = QPushButton()
        self.number_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['number'].name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.number_color_btn.setMask(self.create_diamond_mask(20))
        self.number_color_btn.clicked.connect(lambda: self._choose_color_direct("number"))
        
        # 创建启用行，使用类似add_color_row的结构确保对齐
        enable_row = QHBoxLayout()
        enable_row.setSpacing(0)  # 间距设为0，紧贴布局
        enable_row.setAlignment(Qt.AlignLeft)
        
        # 创建标签和颜色按钮的容器
        label_container = QWidget()
        label_layout = QHBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)  # 标签和颜色按钮之间无间距
        
        # 添加复选框和启用文字（相当于标签），统一标签长度
        label_layout.addWidget(self.enable_number_cb)
        # "启用"只有2个字，需要添加2个全角空格来对齐其他4字标签
        label = QLabel("启用　　")  # 添加2个全角空格
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_layout.addWidget(label)
        
        # 添加颜色按钮（缩小到20x20）
        self.number_color_btn.setFixedSize(20, 20)
        label_layout.addWidget(self.number_color_btn)
        
        enable_row.addWidget(label_container)
        number_layout.addLayout(enable_row)
        
        self.insert_after_combo = QComboBox()
        self.insert_after_combo.addItems(["开头", "末尾", "关键词前", "关键词后"])
        self.insert_after_combo.setCurrentIndex(1)
        self.insert_after_edit = QLineEdit()
        self.insert_after_edit.setPlaceholderText("指定关键词")
        add_connected_rows("插入位置：", self.insert_after_combo, self.insert_after_edit, number_layout)
        
        # 为编号前缀添加调色板（可单独编辑）
        self.number_prefix_edit = QLineEdit()
        self.number_prefix_edit.setPlaceholderText("编号前的内容")
        self.number_prefix_color_btn = QPushButton()
        self.number_prefix_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.get('number_prefix', self.colors['number']).name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.number_prefix_color_btn.setMask(self.create_diamond_mask(20))
        self.number_prefix_color_btn.clicked.connect(lambda: self._choose_color_direct("number_prefix"))
        add_color_row("编号前缀：", [self.number_prefix_edit], self.number_prefix_color_btn, number_layout)
        
        # 为编号后缀添加调色板（可单独编辑）
        self.number_suffix_edit = QLineEdit()
        self.number_suffix_edit.setPlaceholderText("编号后的内容")
        self.number_suffix_color_btn = QPushButton()
        self.number_suffix_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.get('number_suffix', self.colors['number']).name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.number_suffix_color_btn.setMask(self.create_diamond_mask(20))
        self.number_suffix_color_btn.clicked.connect(lambda: self._choose_color_direct("number_suffix"))
        add_color_row("编号后缀：", [self.number_suffix_edit], self.number_suffix_color_btn, number_layout)
        
        self.start_spin = QSpinBox()
        self.start_spin.setValue(1)
        add_indent_row("起始编号：", [self.start_spin], number_layout)
        self.step_spin = QSpinBox()
        self.step_spin.setValue(1)
        add_indent_row("编号步长：", [self.step_spin], number_layout)
        self.pad_spin = QSpinBox()
        self.pad_spin.setValue(0)
        # 数字位数不再使用颜色按钮，改为纯文本行
        add_indent_row("数字位数：", [self.pad_spin], number_layout)
        top_inputs_layout.addWidget(number_group)

        # 删除范围 - 移到顶部容器，紧挨着编号组
        delete_group, delete_layout = create_group("删除范围")
        
        # 添加启用勾选框和调色板，使用类似编号区域的方式处理
        self.enable_delete_cb = QCheckBox()
        self.enable_delete_cb.setChecked(False)
        
        # 创建删除颜色按钮（菱形样式）
        self.delete_color_btn = QPushButton()
        self.delete_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['delete'].name()};
                border: 1px solid #666;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
        self.delete_color_btn.setMask(self.create_diamond_mask(20))
        self.delete_color_btn.clicked.connect(lambda: self._choose_color_direct("delete"))
        # 删除范围调色板始终可用，不依赖于启用状态
        
        # 创建启用行，使用类似编号区域的结构确保对齐
        enable_row = QHBoxLayout()
        enable_row.setSpacing(0)  # 间距设为0，紧贴布局
        enable_row.setAlignment(Qt.AlignLeft)
        
        # 创建标签和颜色按钮的容器
        label_container = QWidget()
        label_layout = QHBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)  # 标签和颜色按钮之间无间距
        
        # 添加复选框和启用文字（相当于标签），统一标签长度
        label_layout.addWidget(self.enable_delete_cb)
        # "启用"只有2个字，需要添加2个全角空格来对齐其他4字标签
        label = QLabel("启用　　")  # 添加2个全角空格
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_layout.addWidget(label)
        
        # 添加颜色按钮（缩小到20x20）
        self.delete_color_btn.setFixedSize(20, 20)
        label_layout.addWidget(self.delete_color_btn)
        
        enable_row.addWidget(label_container)
        delete_layout.addLayout(enable_row)
        
        self.remove_from = QSpinBox()
        self.remove_from.setMinimum(0)
        self.remove_from.setValue(0)
        self.remove_from.setEnabled(False)  # 初始状态为禁用
        add_indent_row("起始位置：", [self.remove_from], delete_layout)
        self.remove_to = QSpinBox()
        self.remove_to.setMinimum(0)
        self.remove_to.setValue(0)
        self.remove_to.setEnabled(False)  # 初始状态为禁用
        add_indent_row("结束位置：", [self.remove_to], delete_layout)
        top_inputs_layout.addWidget(delete_group)

        # 将顶部容器添加到主布局
        center_layout.addWidget(self.top_inputs)

        self.left_tree.header().sectionResized.connect(self.on_left_column_resized)
        self.right_tree.header().sectionResized.connect(self.on_right_column_resized)

        # 杂项 - 移到顶部容器，紧挨着删除范围组
        case_group, case_layout = create_group("杂项")
        self.case_combo = QComboBox()
        self.case_combo.addItems(["不变", "大写", "小写", "标题格式"])
        add_row("大小写：", [self.case_combo], case_layout)
        top_inputs_layout.addWidget(case_group)

        center_layout.addWidget(self.inputs)
        center_layout.addStretch()
        self.splitter.addWidget(self.center)
        self.splitter.addWidget(right_panel)

        # 设置中间区域固定宽度：初始锁定为滑条当前值（不随分割器拖动变化）
        initial_center_width = self.width_slider.value()
        self.center.setMinimumWidth(initial_center_width)
        self.center.setMaximumWidth(initial_center_width)
        
        self.splitter.setStretchFactor(0, 1)  # 左侧可拉伸
        self.splitter.setStretchFactor(1, 0)  # 中间固定宽度
        self.splitter.setStretchFactor(2, 1)  # 右侧可拉伸
        self.splitter.setSizes([400, 300, 400])  # 启动为最小中间宽度
        self.splitter.setChildrenCollapsible(False)
        
        # 安装分割器handle事件过滤器，智能处理分割器拖动
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        layout.addWidget(self.splitter)

        all_widgets = [
            self.find_edit, self.replace_edit, self.prefix_edit, self.suffix_edit,
            self.case_combo, self.number_prefix_edit, self.insert_after_combo,
            self.insert_after_edit, self.number_suffix_edit, self.start_spin, self.step_spin,
            self.pad_spin, self.remove_from, self.remove_to, self.match_mode, self.enable_number_cb,
            self.filter_pattern_edit, self.skip_pattern_edit, self.enable_delete_cb  # 添加启用删除复选框
        ]
        for w in all_widgets:
            if isinstance(w, QSpinBox):
                w.valueChanged.connect(self.on_preview)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.on_preview)
            elif isinstance(w, QLineEdit):
                w.textChanged.connect(self.on_preview)
            elif isinstance(w, QCheckBox):
                w.stateChanged.connect(self.on_preview)

        self.remove_from.valueChanged.connect(self._update_remove_to_min)
        self._update_remove_to_min()

        # 高亮设置连接
        self.highlight_enabled.stateChanged.connect(self._update_highlight_settings)
        self.highlight_intensity.valueChanged.connect(self._update_highlight_settings)

        # 启用删除功能连接
        self.enable_delete_cb.stateChanged.connect(self._on_delete_enabled_changed)

    def create_diamond_mask(self, size):
        """创建菱形裁剪区域"""
        from PyQt5.QtGui import QPolygon, QRegion
        from PyQt5.QtCore import QPoint
        
        # 创建菱形多边形
        polygon = QPolygon([
            QPoint(size // 2, 0),           # 顶点
            QPoint(size, size // 2),        # 右点
            QPoint(size // 2, size),        # 底点
            QPoint(0, size // 2)            # 左点
        ])
        
        return QRegion(polygon)

    def _update_remove_to_min(self):
        current_from = self.remove_from.value()
        current_to = self.remove_to.value()
        if current_to < current_from:
            self.remove_to.setValue(current_from)
        self.remove_to.setMinimum(current_from)

    def _on_delete_enabled_changed(self, state):
        """处理启用删除功能状态变化"""
        enabled = (state == Qt.Checked)
        # 控制删除相关控件的启用状态（调色板始终可用）
        self.remove_from.setEnabled(enabled)
        self.remove_to.setEnabled(enabled)
        self.on_preview()



    def _on_width_slider_changed(self, value):
        """宽度滑条值改变时的处理"""
        # 更新显示值
        self.width_value_label.setText(str(value))
        
        # 安全检查：确保分割器和中间框架存在
        if not hasattr(self, 'splitter') or not self.splitter:
            return
            
        # 确保新宽度在合理范围内（整体降低30）
        if value < 300:
            value = 300
        elif value > 675:
            value = 675

        # 锁定中间区域宽度为滑条值，防止分割器拖动修改
        if hasattr(self, 'center') and self.center:
            self.center.setMinimumWidth(value)
            self.center.setMaximumWidth(value)
            
        # 两侧同时调整：将剩余空间在左右两侧均分，以实现对称扩展/收缩
        current_sizes = self.splitter.sizes()
        total_width = sum(current_sizes)
        remaining = max(0, total_width - value)
        left_width = remaining // 2
        right_width = remaining - left_width

        # 设置分割器各部分的尺寸（中间为滑条值，左右等分剩余空间）
        self.splitter.setSizes([left_width, value, right_width])

        # 更新几何但不重新分配比例，避免布局跳变
        self.splitter.updateGeometry()

    def _on_splitter_moved(self, pos, index):
        """分割器handle移动时的处理，智能处理分割器拖动"""
        # 安全检查：确保分割器存在
        if not hasattr(self, 'splitter') or not self.splitter:
            return

        # 获取当前分割器尺寸
        current_sizes = self.splitter.sizes()

        if len(current_sizes) >= 3:
            # 获取中间部分的新宽度
            new_center_width = current_sizes[1]

            # 更新 width_slider 的值以反映中间部分的新宽度
            # 这将触发 _on_width_slider_changed 方法，从而正确调整布局
            self.width_slider.setValue(new_center_width)



    def on_apply_one(self):
        """逐一应用重命名 - 从上到下逐个重命名（无弹窗版）"""
        if not self.file_data:
            return

        # 获取当前选中的行，如果没有选中则从第一行开始
        current_row = 0
        selected_indexes = self.left_tree.selectedIndexes()
        if selected_indexes:
            current_row = selected_indexes[0].row()
        
        # 查找下一个需要重命名的文件
        start_row = current_row
        found = False
        target_row = -1
        
        # 从当前行开始查找
        for row in range(start_row, len(self.file_data)):
            src_path, original_name, processed_info = self.file_data[row]
            src = Path(src_path)
            if not src.exists():
                continue
                
            parts, _ = self.build_new_name(original_name, row)
            new_name = ''.join([text for text, _ in parts])
            dst = src.with_name(new_name)
            
            if src == dst:
                continue
                
            # 检查目标文件是否已存在，自动跳过不覆盖
            if dst.exists():
                continue
            
            found = True
            target_row = row
            break
        
        if not found:
            return

        # 执行单个重命名
        src_path, original_name, processed_info = self.file_data[target_row]
        src = Path(src_path)
        parts, _ = self.build_new_name(original_name, target_row)
        new_name = ''.join([text for text, _ in parts])
        dst = src.with_name(new_name)
        
        try:
            src.rename(dst)
            
            # 更新file_data中的路径
            self.file_data[target_row] = (str(dst), dst.name, processed_info)
            
            # 为撤销保存
            self.last_undo_stack.append([(dst, src)])
            
            # 重建左侧树并选中下一行
            self._rebuild_left_tree()
            
            # 选中下一行
            next_row = target_row + 1
            if next_row < len(self.file_data):
                index = self.left_model.index(next_row, 0)
                self.left_tree.setCurrentIndex(index)
                self.left_tree.scrollTo(index)
            
        except Exception as e:
            pass

        self.on_preview()  # 重新预览以更新显示

    def load_color_config(self):
        """加载颜色配置"""
        settings = QSettings("BatchRename", "HighlightColors")
        
        # 默认颜色配置
        default_colors = {
            "prefix": QColor("#FFD700"),    # 金色 - 前缀
            "suffix": QColor("#87CEFA"),    # 浅蓝色 - 后缀
            "replace": QColor("#90EE90"),   # 浅绿色 - 替换
            "number": QColor("#FFB6C1"),    # 浅粉色 - 编号
            "number_prefix": QColor("#FFB6C1"),  # 浅粉色 - 编号前缀
            "number_suffix": QColor("#FFB6C1"),  # 浅粉色 - 编号后缀
            "delete": QColor("#FFFACD"),    # 浅黄色 - 删除
            "find": QColor("#FFFF00")       # 黄色 - 查找
        }
        
        self.colors = {}
        for role, default_color in default_colors.items():
            color_str = settings.value(f"colors/{role}")
            if color_str and QColor.isValidColor(color_str):
                self.colors[role] = QColor(color_str)
            else:
                self.colors[role] = default_color

    def save_color_config(self):
        """保存颜色配置"""
        settings = QSettings("BatchRename", "HighlightColors")
        for role, color in self.colors.items():
            settings.setValue(f"colors/{role}", color.name())
        settings.sync()

    def _choose_color_direct(self, role):
        """直接选择颜色"""
        current_color = self.colors[role]
        color = QColorDialog.getColor(current_color, self, f"选择{self._get_role_name(role)}颜色")
        
        if color.isValid():
            self.colors[role] = color
            self.right_delegate.colors = self.colors
            self.left_delegate.colors = self.colors
            self.save_color_config()
            
            # 更新对应的颜色按钮
            btn_name = f"{role}_color_btn"
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color.name()};
                        border: 1px solid #666;
                        border-radius: 0px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #333;
                    }}
                """)
                # 确保按钮大小保持20x20
                btn.setFixedSize(20, 20)
            
            # 更新编号相关按钮（如果存在）
            if role in ["number_prefix", "number_suffix"]:
                btn_name = f"{role}_color_btn"
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {color.name()};
                            border: 1px solid #666;
                            border-radius: 0px;
                        }}
                        QPushButton:hover {{
                            border: 2px solid #333;
                        }}
                    """)
                    # 确保按钮大小保持20x20
                    btn.setFixedSize(20, 20)
            
            self.on_preview()

    def _get_role_name(self, role):
        """获取角色的中文名称"""
        role_names = {
            "prefix": "前缀",
            "suffix": "后缀",
            "replace": "替换",
            "number": "编号",
            "delete": "删除",
            "find": "查找"
        }
        return role_names.get(role, role)

    def show_color_config_dialog(self):
        """显示颜色配置对话框"""
        dialog = ColorConfigDialog(self.colors, self)
        if dialog.exec_() == QDialog.Accepted:
            self.colors = dialog.get_colors()
            self.right_delegate.colors = self.colors
            self.left_delegate.colors = self.colors
            self.save_color_config()
            
            # 更新所有颜色按钮
            color_buttons = ["prefix", "suffix", "replace", "number", "delete", "find", 
                           "number_prefix", "number_suffix"]
            for role in color_buttons:
                btn_name = f"{role}_color_btn"
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {self.colors[role].name()};
                            border: 1px solid #666;
                            border-radius: 0px;
                        }}
                        QPushButton:hover {{
                            border: 2px solid #333;
                        }}
                    """)
                    # 确保按钮大小保持20x20
                    btn.setFixedSize(20, 20)
            
            self.on_preview()

    def _update_highlight_settings(self):
        """更新高亮设置"""
        self.right_delegate.set_highlight_enabled(self.highlight_enabled.isChecked())
        self.right_delegate.set_highlight_intensity(self.highlight_intensity.value() / 100.0)
        self.left_delegate.set_highlight_enabled(self.highlight_enabled.isChecked())
        self.left_delegate.set_highlight_intensity(self.highlight_intensity.value() / 100.0)
        self.on_preview()
        
    def add_paths(self, paths, recursive=False):
        """添加文件路径 - 修复路径处理问题"""
        # 清除文件夹模式标志
        self.folder_mode = False
        if hasattr(self, 'folder_paths'):
            self.folder_paths.clear()
        
        added_count = 0
        duplicate_count = 0
        
        for path in paths:
            path_str = str(path)
            try:
                # 安全地检查路径是否存在
                path_obj = Path(path_str)
                if not path_obj.exists():
                    print(f"路径不存在，跳过: {path_str}")
                    continue
                    
                if path_obj.is_dir():
                    if recursive:
                        # 安全地遍历目录
                        try:
                            for root, _, files in os.walk(path_str):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        if self._add_file_to_trees(file_path):
                                            added_count += 1
                                        else:
                                            duplicate_count += 1
                                    except Exception as file_error:
                                        print(f"添加文件失败 {file_path}: {file_error}")
                                        continue
                        except Exception as walk_error:
                            print(f"遍历目录失败 {path_str}: {walk_error}")
                            continue
                    else:
                        # 非递归模式，安全地扫描当前目录
                        try:
                            for entry in os.scandir(path_str):
                                if entry.is_file():
                                    try:
                                        if self._add_file_to_trees(entry.path):
                                            added_count += 1
                                        else:
                                            duplicate_count += 1
                                    except Exception as file_error:
                                        print(f"添加文件失败 {entry.path}: {file_error}")
                                        continue
                        except Exception as scan_error:
                            print(f"扫描目录失败 {path_str}: {scan_error}")
                            continue
                elif path_obj.is_file():
                    if self._add_file_to_trees(path_str):
                        added_count += 1
                    else:
                        duplicate_count += 1
            except Exception as e:
                print(f"处理路径失败 {path_str}: {e}")
                continue  # 继续处理其他路径
                
        self.on_preview()
        
        # 备份原始文件数据
        self.original_file_data = self.file_data.copy()
        
        # 显示添加结果
        if duplicate_count > 0:
            QMessageBox.information(self, "添加完成", 
                f"成功添加 {added_count} 个文件，跳过 {duplicate_count} 个重复文件")

    def add_folder_names(self, folder_paths, recursive=False):
        """添加文件夹名称（用于重命名文件夹）"""
        # 设置文件夹模式标志
        self.folder_mode = True
        if not hasattr(self, 'folder_paths'):
            self.folder_paths = set()
        
        added_count = 0
        duplicate_count = 0
        
        for folder_path in folder_paths:
            folder_str = str(folder_path)
            try:
                if recursive:
                    # 递归模式：添加文件夹及其所有子文件夹
                    for root, dirs, _ in os.walk(folder_str):
                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            if self._add_folder_to_trees(dir_path):
                                self.folder_paths.add(dir_path)
                                added_count += 1
                            else:
                                duplicate_count += 1
                else:
                    # 非递归模式：只添加当前文件夹
                    if self._add_folder_to_trees(folder_str):
                        self.folder_paths.add(folder_str)
                        added_count += 1
                    else:
                        duplicate_count += 1
            except Exception as e:
                print(f"添加文件夹失败 {folder_str}: {e}")
        
        # 重建左侧树视图以显示文件夹
        self._rebuild_left_tree()
        
        self.on_preview()
        
        # 备份原始文件数据
        self.original_file_data = self.file_data.copy()
        
        # 显示添加结果
        if duplicate_count > 0:
            QMessageBox.information(self, "添加完成", 
                f"成功添加 {added_count} 个文件夹，跳过 {duplicate_count} 个重复文件夹")

    def _add_folder_to_trees(self, folder_path: str) -> bool:
        """添加文件夹到树形视图，返回是否成功添加"""
        if any(item[0] == folder_path for item in self.file_data):
            return False  # 文件夹已存在

        try:
            original_name = os.path.basename(folder_path)
            self.file_data.append((folder_path, original_name, {}))
            
            # 不要在这里立即重建，让调用者统一处理
            return True
        except Exception as e:
            print(f"添加文件夹失败 {folder_path}: {e}")
            return False

    def _get_duplicate_folder_names(self) -> set:
        """获取同名文件夹名称集合"""
        folder_names = {}
        duplicate_names = set()
        
        # 统计所有文件夹的名称出现次数
        for src_path, original_name, _ in self.file_data:
            if os.path.isdir(src_path):
                if original_name in folder_names:
                    duplicate_names.add(original_name)
                    folder_names[original_name] += 1
                else:
                    folder_names[original_name] = 1
        
        print(f"调试 - 文件夹统计: {folder_names}, 同名文件夹: {duplicate_names}")
        return duplicate_names

    def _get_relative_folder_path(self, folder_path: str) -> str:
        """获取文件夹的相对路径（从共同父级开始）"""
        try:
            # 找到所有文件夹路径的共同父级
            folder_paths = [item[0] for item in self.file_data if os.path.isdir(item[0])]
            if not folder_paths:
                return folder_path
            
            # 使用os.path.commonpath找到共同路径
            common_parent = os.path.commonpath(folder_paths)
            
            # 如果共同父级就是当前文件夹的父级，返回文件夹名
            if common_parent == os.path.dirname(folder_path):
                return os.path.basename(folder_path)
            
            # 否则返回从共同父级开始的相对路径
            relative_path = os.path.relpath(folder_path, common_parent)
            return relative_path
            
        except Exception as e:
            print(f"计算相对路径失败 {folder_path}: {e}")
            return folder_path

    def _add_file_to_trees(self, file_path: str) -> bool:
        """添加文件到树形视图，返回是否成功添加"""
        if any(item[0] == file_path for item in self.file_data):
            return False  # 文件已存在

        try:
            original_name = os.path.basename(file_path)
            self.file_data.append((file_path, original_name, {}))

            # 添加到左侧模型
            idx = len(self.file_data)
            item0 = QStandardItem(str(idx))
            item0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item0.setData(file_path, Qt.UserRole)
            
            item1 = QStandardItem("")  # 箭头列，空内容
            item1.setData(file_path, Qt.UserRole)
            
            item2 = QStandardItem(original_name)
            item2.setData(file_path, Qt.UserRole)
            
            # 根据是否是文件夹模式显示不同的路径
            display_path = file_path
            if hasattr(self, 'folder_mode') and self.folder_mode and file_path in getattr(self, 'folder_paths', set()):
                # 文件夹模式下，显示从共同父级开始的相对路径
                display_path = self._get_relative_folder_path(file_path)
            
            item3 = QStandardItem(display_path)
            item3.setData(file_path, Qt.UserRole)
            
            item4 = QStandardItem(str(idx))
            item4.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item4.setData(file_path, Qt.UserRole)
            
            row = [item0, item1, item2, item3, item4]
            self.left_model.appendRow(row)

            # 设置图标
            file_info = QFileInfo(file_path)
            icon_provider = QFileIconProvider()
            icon = icon_provider.icon(file_info)
            item2.setIcon(icon)
            
            return True
        except Exception as e:
            print(f"添加文件失败 {file_path}: {e}")
            return False

    def _rebuild_left_tree(self):
        """重建左侧树 - 添加异常处理和性能优化"""
        try:
            self.left_model.removeRows(0, self.left_model.rowCount())
            
            # 获取同名文件夹名称
            duplicate_folder_names = self._get_duplicate_folder_names()
            
            # 批量添加项目以提高性能
            items_to_add = []
            
            for idx, (src_path, original_name, _) in enumerate(self.file_data):
                try:
                    item0 = QStandardItem(str(idx + 1))
                    item0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item0.setData(src_path, Qt.UserRole)
                    
                    item1 = QStandardItem("")  # 箭头列，空内容
                    item1.setData(src_path, Qt.UserRole)
                    
                    item2 = QStandardItem(original_name)
                    item2.setData(src_path, Qt.UserRole)
                    
                    # 根据是否是文件夹模式显示不同的路径
                    display_path = src_path
                    if hasattr(self, 'folder_mode') and self.folder_mode and src_path in self.folder_paths:
                        # 文件夹模式下，显示从共同父级开始的相对路径
                        display_path = self._get_relative_folder_path(src_path)
                    
                    item3 = QStandardItem(display_path)
                    item3.setData(src_path, Qt.UserRole)
                    
                    # 如果是文件夹且名称重复，设置路径列为红色
                    if os.path.isdir(src_path) and original_name in duplicate_folder_names:
                        item3.setForeground(QColor("red"))
                        print(f"调试 - 设置红色字体: {original_name} - {src_path}")
                    else:
                        print(f"调试 - 正常字体: {original_name} - {src_path} (重复文件夹: {duplicate_folder_names})")
                    
                    item4 = QStandardItem(str(idx + 1))
                    item4.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item4.setData(src_path, Qt.UserRole)
                    
                    row = [item0, item1, item2, item3, item4]
                    items_to_add.append(row)
                    
                    # 设置图标
                    file_info = QFileInfo(src_path)
                    icon_provider = QFileIconProvider()
                    icon = icon_provider.icon(file_info)
                    item2.setIcon(icon)
                    
                except Exception as e:
                    print(f"重建左侧树时处理文件错误: {src_path} - {e}")
                    continue
            
            # 批量添加所有项目
            for row_items in items_to_add:
                self.left_model.appendRow(row_items)
                
        except Exception as e:
            print(f"重建左侧树时发生严重错误: {e}")
            QMessageBox.critical(self, "重建失败", f"重建文件列表时发生错误: {str(e)}")

    def on_add_folder(self):
        """添加文件夹 - 修复递归复选框逻辑"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            # 默认使用递归模式
            recursive = True
            print(f"添加文件夹: {folder_path}, 递归模式: {recursive}")  # 调试用
            self.add_folder_names([Path(folder_path)], recursive)

    def on_add_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if file_paths:
            self.add_paths([Path(p) for p in file_paths])

    def on_clear(self):
        """清空所有数据 - 添加确认对话框"""
        if self.file_data:
            reply = QMessageBox.question(
                self, "确认清空", 
                f"确定要清空所有 {len(self.file_data)} 个文件吗？\n此操作不可撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        try:
            self.left_model.removeRows(0, self.left_model.rowCount())
            self.right_model.removeRows(0, self.right_model.rowCount())
            self.file_data.clear()
            self.original_file_data.clear()  # 清空原始数据备份
            self.removed_items.clear()
            self.last_undo_stack.clear()
            
            # 清空文件夹模式相关数据
            self.folder_mode = False
            if hasattr(self, 'folder_paths'):
                self.folder_paths.clear()
            
            self.on_preview()
            
            # 清空筛选条件
            if hasattr(self, 'filter_pattern_edit'):
                self.filter_pattern_edit.clear()
            if hasattr(self, 'skip_pattern_edit'):
                self.skip_pattern_edit.clear()
            
            # 可选：显示清空完成提示
            # QMessageBox.information(self, "完成", "已清空所有文件")
            
        except Exception as e:
            QMessageBox.critical(self, "清空失败", f"清空文件列表时发生错误: {str(e)}")
            print(f"清空错误: {e}")

    def sync_vertical(self, value):
        if self.sync_vertical_enabled:
            sender = self.sender()
            if sender == self.left_tree.verticalScrollBar():
                self.right_tree.verticalScrollBar().setValue(value)
            elif sender == self.right_tree.verticalScrollBar():
                self.left_tree.verticalScrollBar().setValue(value)

    def sync_horizontal(self, value):
        if self.sync_horizontal_enabled:
            sender = self.sender()
            if sender == self.left_tree.horizontalScrollBar():
                self.right_tree.horizontalScrollBar().setValue(value)
            elif sender == self.right_tree.horizontalScrollBar():
                self.left_tree.horizontalScrollBar().setValue(value)

    def on_sync_vertical_toggled(self, state):
        self.sync_vertical_enabled = (state == Qt.Checked)

    def on_sync_horizontal_toggled(self, state):
        self.sync_horizontal_enabled = (state == Qt.Checked)

    def on_left_selection_changed(self, selected, deselected):
        """左侧树选中行变化时，同步右侧树的选中状态"""
        # 获取左侧选中的行号
        selected_rows = set()
        for index in self.left_tree.selectedIndexes():
            selected_rows.add(index.row())
        
        # 同步到右侧树
        self._sync_selection_to_right(selected_rows)

    def on_right_selection_changed(self, selected, deselected):
        """右侧树选中行变化时，同步左侧树的选中状态"""
        # 获取右侧选中的行号
        selected_rows = set()
        for index in self.right_tree.selectedIndexes():
            selected_rows.add(index.row())
        
        # 同步到左侧树
        self._sync_selection_to_left(selected_rows)

    def _sync_selection_to_right(self, selected_rows):
        """将选中行同步到右侧树"""
        # 阻止信号递归
        self.right_tree.selectionModel().blockSignals(True)
        
        # 清除当前选中
        self.right_tree.selectionModel().clearSelection()
        
        # 选中对应的行
        for row in selected_rows:
            if row < self.right_model.rowCount():
                index = self.right_model.index(row, 0)  # 选中第0列
                self.right_tree.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                # 确保该行可见（不移除横向滚动）
                # 不滚动，只确保可见
                pass
        
        self.right_tree.selectionModel().blockSignals(False)
        
        # 强制重绘整个右侧树视图，确保箭头立即显示
        self.right_tree.viewport().update()

    def _sync_selection_to_left(self, selected_rows):
        """将选中行同步到左侧树"""
        # 阻止信号递归
        self.left_tree.selectionModel().blockSignals(True)
        
        # 清除当前选中
        self.left_tree.selectionModel().clearSelection()
        
        # 选中对应的行
        for row in selected_rows:
            if row < self.left_model.rowCount():
                index = self.left_model.index(row, 0)  # 选中第0列
                self.left_tree.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                # 确保该行可见（不移除横向滚动）
                # 不滚动，只确保可见
                pass
        
        self.left_tree.selectionModel().blockSignals(False)
        
        # 强制重绘整个左侧树视图，确保箭头立即显示
        self.left_tree.viewport().update()

    def _update_find_highlight(self):
        """更新查找高亮 - 只高亮查找关键词"""
        try:
            find_text = self.find_edit.text()
            is_regex = (self.match_mode.currentIndex() == 1)

            def highlight_items(model):
                if model is None:
                    return

                for row in range(model.rowCount()):
                    index = model.index(row, 2)  # 文件名列现在是第2列
                    try:
                        text = model.data(index) or ""
                    except Exception:
                        text = ""
                        
                    # 获取已有的高亮信息（排除之前的查找高亮）
                    highlight_info = index.data(Qt.UserRole + 1) or []
                    
                    # 清除之前的查找高亮
                    if highlight_info:
                        highlight_info = [(part, role) for part, role in highlight_info if role != "find"]
                    
                    if find_text and self.highlight_enabled.isChecked() and text:
                        # 两侧树都使用自定义高亮代理
                        if model == self.right_model or model == self.left_model:
                            # 查找匹配的文本并添加高亮
                            new_highlight_info = []
                            if is_regex:
                                try:
                                    matches = re.finditer(find_text, text)
                                    last_end = 0
                                    for match in matches:
                                        start, end = match.span()
                                        if start > last_end:
                                            # 添加非查找部分
                                            before_text = text[last_end:start]
                                            if before_text:
                                                new_highlight_info.append((before_text, None))
                                        new_highlight_info.append((text[start:end], "find"))
                                        last_end = end
                                    if last_end < len(text):
                                        # 添加剩余部分
                                        remaining_text = text[last_end:]
                                        if remaining_text:
                                            new_highlight_info.append((remaining_text, None))
                                except re.error:
                                    # 正则表达式错误，使用原始高亮信息
                                    new_highlight_info = highlight_info
                            else:
                                # 普通匹配（优化版本，避免引入额外空格）
                                find_len = len(find_text)
                                start = 0
                                last_pos = 0
                                while True:
                                    pos = text.find(find_text, start)
                                    if pos == -1:
                                        # 添加剩余部分
                                        if last_pos < len(text):
                                            remaining_text = text[last_pos:]
                                            if remaining_text:
                                                new_highlight_info.append((remaining_text, None))
                                        break
                                    
                                    # 添加查找前的部分
                                    if pos > last_pos:
                                        before_text = text[last_pos:pos]
                                        if before_text:
                                            new_highlight_info.append((before_text, None))
                                    
                                    # 添加查找部分
                                    new_highlight_info.append((find_text, "find"))
                                    last_pos = pos + find_len
                                    start = pos + find_len
                            
                            # 更新高亮信息
                            item = model.itemFromIndex(index)
                            if item:
                                item.setData(new_highlight_info, Qt.UserRole + 1)
                        else:
                            # 左侧树保持原有逻辑
                            if is_regex:
                                try:
                                    if re.search(find_text, text):
                                        try:
                                            item = model.itemFromIndex(index)
                                            if item:
                                                item.setBackground(QBrush(self.colors["find"]))
                                        except Exception:
                                            pass
                                except re.error:
                                    pass
                            else:
                                if find_text in text:
                                    try:
                                        item = model.itemFromIndex(index)
                                        if item:
                                            item.setBackground(QBrush(self.colors["find"]))
                                    except Exception:
                                            pass
                    else:
                        # 没有查找文本，恢复原始高亮
                        if model == self.right_model or model == self.left_model:
                            item = model.itemFromIndex(index)
                            if item:
                                item.setData(highlight_info, Qt.UserRole + 1)

            highlight_items(self.left_model)
            highlight_items(self.right_model)

        except Exception as e:
            print(f"_update_find_highlight方法发生异常: {e}")
            # 可选：显示用户友好的错误提示
            # QMessageBox.warning(self, "高亮错误", f"查找高亮功能出错: {str(e)}")

    def _is_file_matching_find(self, original_name):
        """检查文件是否匹配查找条件"""
        find_text = self.find_edit.text()
        if not find_text:
            return True  # 如果没有查找内容，认为所有文件都匹配

        if self.match_mode.currentText() == "普通匹配":
            return find_text in original_name
        else:
            try:
                return bool(re.search(find_text, original_name))
            except re.error:
                return False
                
    def build_new_name(self, original_name, index):
        """构建新文件名 - 优化编号处理逻辑"""
        processed_parts = []
        processed_info = {}
        new_name_parts = [(original_name, None)]  # 默认部分
        
        # 检查是否匹配查找条件
        is_matching = self._is_file_matching_find(original_name)

        # 查找替换处理
        current_text = original_name
        


                



        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()
        
        if find_text and self.highlight_enabled.isChecked():
            # 先构建查找高亮信息（不替换，只高亮）
            if self.match_mode.currentText() == "普通匹配":
                if find_text in original_name:
                    parts = []
                    start = 0
                    while True:
                        pos = original_name.find(find_text, start)
                        if pos == -1:
                            if start < len(original_name):
                                parts.append((original_name[start:], None))
                            break
                        if pos > start:
                            parts.append((original_name[start:pos], None))
                        parts.append((find_text, "find"))  # 高亮查找内容
                        start = pos + len(find_text)
                    new_name_parts = parts
                else:
                    try:
                        # 正则查找高亮
                        matches = list(re.finditer(find_text, original_name))
                        if matches:
                            parts = []
                            last_end = 0
                            for match in matches:
                                start, end = match.span()
                                if start > last_end:
                                    parts.append((original_name[last_end:start], None))
                                parts.append((original_name[start:end], "find"))  # 高亮匹配内容
                                last_end = end
                            if last_end < len(original_name):
                                parts.append((original_name[last_end:], None))
                            new_name_parts = parts
                    except re.error:
                        pass
            
            # 查找替换处理
            if replace_text and find_text:  # 只有同时有查找和替换文本时才处理替换
                if self.match_mode.currentText() == "普通匹配":
                    if find_text and find_text in original_name:
                        # 如果启用了高亮，需要重新构建高亮信息以包含替换部分
                        if self.highlight_enabled.isChecked() and find_text and replace_text:
                            parts = []
                            start = 0
                            while True:
                                pos = original_name.find(find_text, start)
                                if pos == -1:
                                    if start < len(original_name):
                                        parts.append((original_name[start:], None))
                                    break
                                if pos > start:
                                    parts.append((original_name[start:pos], None))
                                parts.append((replace_text, "replace"))
                                start = pos + len(find_text)
                            new_name_parts = parts
                        else:
                            # 不启用高亮时简单替换
                            new_name_parts = [(original_name.replace(find_text, replace_text), None)]
                        processed_info["find"] = True
                        original_name = original_name.replace(find_text, replace_text)
                else:
                    try:
                        # 正则替换暂不支持部分高亮
                        new_name = re.sub(find_text, replace_text, original_name)
                        new_name_parts = [(new_name, "replace")]
                        processed_info["find"] = True
                        original_name = new_name
                    except re.error as e:
                        QMessageBox.warning(self, "正则表达式错误", f"正则表达式无效: {str(e)}")
                        return new_name_parts, processed_info

        # 前后缀（仅对匹配查找条件的文件生效）
        prefix = self.prefix_edit.text()
        if prefix and is_matching:
            new_name_parts.insert(0, (prefix, "prefix"))
            processed_info["prefix"] = True

        suffix = self.suffix_edit.text()
        if suffix and is_matching:
            new_name_parts.append((suffix, "suffix"))
            processed_info["suffix"] = True

        # 编号（仅在启用编号时且文件匹配查找条件）- 简化逻辑
        if self.enable_number_cb.isChecked() and is_matching:
            number_prefix = self.number_prefix_edit.text()
            number_suffix = self.number_suffix_edit.text()
            start_num = self.start_spin.value()
            step_num = self.step_spin.value()
            pad_num = self.pad_spin.value()

            step = step_num if step_num != 0 else 1
            num = start_num + index * step
            pad = pad_num if pad_num != 0 else 0
            num_str = str(num).zfill(pad) if pad > 0 else str(num)
            num_full = number_prefix + num_str + number_suffix
            
            insert_mode = self.insert_after_combo.currentText()
            insert_text = self.insert_after_edit.text()
            
            try:
                if insert_mode == "开头":
                    # 分别处理编号前缀、编号数字、编号后缀的颜色
                    if number_prefix:
                        new_name_parts.insert(0, (number_prefix, "number_prefix"))
                    new_name_parts.insert(0 if not number_prefix else 1, (num_str, "number"))
                    if number_suffix:
                        new_name_parts.insert(0 if not number_prefix else 2, (number_suffix, "number_suffix"))
                elif insert_mode == "末尾":
                    # 分别处理编号前缀、编号数字、编号后缀的颜色
                    if number_prefix:
                        new_name_parts.append((number_prefix, "number_prefix"))
                    new_name_parts.append((num_str, "number"))
                    if number_suffix:
                        new_name_parts.append((number_suffix, "number_suffix"))
                elif insert_mode == "关键词前" and insert_text:
                    # 查找关键词位置并插入
                    new_parts = []
                    found = False
                    for text, role in new_name_parts:
                        if not found and insert_text in text:
                            pos = text.find(insert_text)
                            if pos > 0:
                                new_parts.append((text[:pos], role))
                            # 分别处理编号前缀、编号数字、编号后缀的颜色
                            if number_prefix:
                                new_parts.append((number_prefix, "number_prefix"))
                            new_parts.append((num_str, "number"))
                            if number_suffix:
                                new_parts.append((number_suffix, "number_suffix"))
                            new_parts.append((text[pos:], role))
                            found = True
                        else:
                            new_parts.append((text, role))
                    if found:
                        new_name_parts = new_parts
                    else:
                        # 分别处理编号前缀、编号数字、编号后缀的颜色
                        if number_prefix:
                            new_name_parts.append((number_prefix, "number_prefix"))
                        new_name_parts.append((num_str, "number"))
                        if number_suffix:
                            new_name_parts.append((number_suffix, "number_suffix"))
                elif insert_mode == "关键词后" and insert_text:
                    # 查找关键词位置并插入
                    new_parts = []
                    found = False
                    for text, role in new_name_parts:
                        if not found and insert_text in text:
                            pos = text.find(insert_text) + len(insert_text)
                            new_parts.append((text[:pos], role))
                            # 分别处理编号前缀、编号数字、编号后缀的颜色
                            if number_prefix:
                                new_parts.append((number_prefix, "number_prefix"))
                            new_parts.append((num_str, "number"))
                            if number_suffix:
                                new_parts.append((number_suffix, "number_suffix"))
                            new_parts.append((text[pos:], role))
                            found = True
                        else:
                            new_parts.append((text, role))
                    if found:
                        new_name_parts = new_parts
                    else:
                        # 分别处理编号前缀、编号数字、编号后缀的颜色
                        if number_prefix:
                            new_name_parts.append((number_prefix, "number_prefix"))
                        new_name_parts.append((num_str, "number"))
                        if number_suffix:
                            new_name_parts.append((number_suffix, "number_suffix"))
                processed_info["number"] = True
            except Exception as e:
                QMessageBox.warning(self, "插入错误", f"编号插入过程中发生错误: {str(e)}")
                return new_name_parts, processed_info

        # 删除范围（基于1-based输入） - 仅对匹配查找条件的文件生效
        if self.enable_delete_cb.isChecked() and is_matching:  # 只有在启用删除功能且文件匹配查找条件时才处理
            frm = self.remove_from.value()
            to = self.remove_to.value()
            if frm > 0 and to >= frm:
                # 合并所有部分以处理删除，但保留原有的角色信息
                full_text = ''.join([text for text, _ in new_name_parts])
                
                # 检查起始位置是否超出文本长度
                if frm > len(full_text):
                    # 起始位置超出范围，跳过删除处理
                    pass
                else:
                    frm_0 = max(0, frm - 1)
                    to_0 = max(frm_0, to - 1)
                    
                    # 调整删除范围，确保不超出文本长度
                    actual_to_0 = min(to_0, len(full_text) - 1) if len(full_text) > 0 else -1
                
                    if frm_0 <= actual_to_0 and len(full_text) > 0:
                        # 使用颜色背景标记删除范围，而不是实际删除字符
                        # 需要重新构建new_name_parts，但要保留原有的角色信息
                        new_new_name_parts = []
                        current_pos = 0
                    
                    for text, role in new_name_parts:
                        text_start = current_pos
                        text_end = current_pos + len(text)
                        
                        # 检查文本是否与删除范围重叠（使用实际的结束位置）
                        if text_end <= frm_0 or text_start > actual_to_0:
                            # 文本完全在删除范围之外，保持原样
                            new_new_name_parts.append((text, role))
                        elif text_start >= frm_0 and text_end <= actual_to_0 + 1:
                            # 文本完全在删除范围之内，标记为delete
                            new_new_name_parts.append((text, "delete"))
                        else:
                            # 文本部分与删除范围重叠，需要分割
                            if text_start < frm_0:
                                # 删除范围之前的部分
                                before_part = text[:frm_0 - text_start]
                                new_new_name_parts.append((before_part, role))
                            
                            # 删除范围部分
                            delete_start = max(0, frm_0 - text_start)
                            delete_end = min(len(text), actual_to_0 + 1 - text_start)
                            if delete_start < delete_end:
                                delete_part = text[delete_start:delete_end]
                                new_new_name_parts.append((delete_part, "delete"))
                            
                            if text_end > actual_to_0 + 1:
                                # 删除范围之后的部分
                                after_part = text[delete_end:]
                                new_new_name_parts.append((after_part, role))
                        
                        current_pos = text_end
                    
                    new_name_parts = new_new_name_parts
                    processed_info["delete"] = True
                # 如果起始位置超出范围，不处理删除

        # 大小写转换（保留高光分段）
        case = self.case_combo.currentText()
        if case != "不变":
            # 合并所有部分以用于整体判断（例如标题格式保留扩展名）
            full_text = ''.join([text for text, _ in new_name_parts])

            if case == "大写":
                # 对每个分段进行大写转换，保留原有角色（高光）
                new_name_parts = [(text.upper(), role) for text, role in new_name_parts]
            elif case == "小写":
                # 对每个分段进行小写转换，保留原有角色（高光）
                new_name_parts = [(text.lower(), role) for text, role in new_name_parts]
            elif case == "标题格式":
                # 仅对文件名部分做标题化，保留扩展名，并保留分段及其角色
                name_part, ext = os.path.splitext(full_text)
                name_len = len(name_part)

                cursor = 0
                titled_parts = []
                for text, role in new_name_parts:
                    start = cursor
                    end = cursor + len(text)

                    if end <= name_len:
                        # 完全在文件名部分
                        titled_parts.append((text.title(), role))
                    elif start >= name_len:
                        # 完全在扩展名部分
                        titled_parts.append((text, role))
                    else:
                        # 横跨边界，分割后分别处理
                        split_pos = name_len - start
                        name_sub = text[:split_pos].title()
                        ext_sub = text[split_pos:]
                        if name_sub:
                            titled_parts.append((name_sub, role))
                        if ext_sub:
                            titled_parts.append((ext_sub, role))
                    cursor = end

                new_name_parts = titled_parts

            processed_info["case"] = True

        return new_name_parts, processed_info

    def on_preview(self):
        """预览功能 - 增强错误处理和性能优化"""
        try:
            self.right_model.removeRows(0, self.right_model.rowCount())
            if not self.file_data:
                return

            # 批量处理错误收集
            error_files = []
            max_name_width = 0  # 记录最长名称的宽度
            
            for idx, file_info in enumerate(self.file_data):
                if len(file_info) < 2:
                    error_files.append(f"索引 {idx}: 数据格式错误")
                    continue
                    
                src_path, original_name, _ = file_info
                try:
                    parts, processed_info = self.build_new_name(original_name, idx)
                    # 保存 processed_info
                    self.file_data[idx] = (src_path, original_name, processed_info)
                    
                    # 创建右侧模型行
                    item0 = QStandardItem(str(idx + 1))
                    item0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    
                    item1 = QStandardItem("")  # 箭头列，空内容
                    
                    # 文件名项，存储高亮部分信息
                    full_name = ''.join([text for text, _ in parts])
                    item2 = QStandardItem(full_name)
                    item2.setData(parts, Qt.UserRole + 1)  # 存储高亮信息
                    
                    item3 = QStandardItem(src_path)
                    item4 = QStandardItem(str(idx + 1))
                    item4.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    
                    # 设置图标
                    file_info_q = QFileInfo(src_path)
                    icon_provider = QFileIconProvider()
                    icon = icon_provider.icon(file_info_q)
                    item2.setIcon(icon)
                    
                    self.right_model.appendRow([item0, item1, item2, item3, item4])
                    
                    # 计算当前名称的显示宽度 - 修复中文宽度计算问题
                    font_metrics = self.right_tree.fontMetrics()
                    # 使用boundingRect来更准确地计算包含中文的文本宽度
                    name_rect = font_metrics.boundingRect(full_name + "   ")  # 添加一些边距
                    name_width = name_rect.width()
                    if name_width > max_name_width:
                        max_name_width = name_width
                    
                except Exception as e:
                    error_msg = f"{original_name}: {str(e)}"
                    error_files.append(error_msg)
                    print(f"预览错误: {error_msg}")
                    continue
            
            # 自动调整名称列宽度 - 提前调整避免重叠（现在是第2列）
            if max_name_width > 0:
                header = self.right_tree.header()
                current_width = self.right_tree.columnWidth(2)  # 第2列是文件名
                # 提前两位距离开始调整：如果计算宽度接近当前宽度就调整
                # 当名称宽度达到当前列宽的80%时就开始调整，避免重叠
                if max_name_width > (current_width * 0.8):
                    # 添加额外边距，确保有足够的空间
                    extra_margin = 20  # 额外20像素边距
                    target_width = max_name_width + extra_margin
                    # 限制最大宽度为窗口宽度的一半，避免过宽
                    max_allowed = self.width() // 2
                    new_width = min(target_width, max_allowed, 500)  # 最大500像素
                    self.right_tree.setColumnWidth(2, new_width)  # 第2列
                    # 如果启用了列宽同步，同步左侧
                    if self.sync_column_enabled:
                        self.left_tree.setColumnWidth(2, new_width)
            
            # 显示批量错误信息
            if error_files:
                error_count = len(error_files)
                if error_count <= 3:
                    QMessageBox.warning(self, "预览错误", 
                        f"以下文件预览失败（共{error_count}个）：\n" + "\n".join(error_files))
                else:
                    QMessageBox.warning(self, "预览错误", 
                        f"以下文件预览失败（共{error_count}个，显示前3个）：\n" + 
                        "\n".join(error_files[:3]) + f"\n... 还有{error_count-3}个错误")
                    
        except Exception as e:
            QMessageBox.critical(self, "预览失败", f"预览过程中发生严重错误: {str(e)}")
            print(f"预览严重错误: {e}")

            self._sync_scroll_positions()
            # 先清空所有查找高亮信息
            for row in range(self.right_model.rowCount()):
                index = self.right_model.index(row, 1)
                item = self.right_model.itemFromIndex(index)
                if item:
                    item.setData([], Qt.UserRole + 1)
            # 重新应用预览高亮
            for idx, file_info in enumerate(self.file_data):
                src_path, original_name, processed_info = file_info
                parts, _ = self.build_new_name(original_name, idx)
                index = self.right_model.index(idx, 1)
                item = self.right_model.itemFromIndex(index)
                if item:
                    item.setData(parts, Qt.UserRole + 1)
            # 最后应用查找高亮
            self._update_find_highlight()

        except Exception as e:
            QMessageBox.warning(self, "预览错误", f"预览过程中发生错误: {str(e)}")

    def _sync_scroll_positions(self):
        if self.sync_vertical_enabled:
            left_v_scroll = self.left_tree.verticalScrollBar().value()
            right_v_scroll = self.right_tree.verticalScrollBar().value()
            if left_v_scroll != right_v_scroll:
                self.right_tree.verticalScrollBar().setValue(left_v_scroll)
        if self.sync_horizontal_enabled:
            left_h_scroll = self.left_tree.horizontalScrollBar().value()
            right_h_scroll = self.right_tree.horizontalScrollBar().value()
            if left_h_scroll != right_h_scroll:
                self.right_tree.horizontalScrollBar().setValue(left_h_scroll)

    def on_sync_column_toggled(self, state):
        self.sync_column_enabled = (state == Qt.Checked)
        if self.sync_column_enabled:
            self.sync_column_widths()

    def _matches_pattern(self, file_name: str, pattern: str, mode: str) -> bool:
        """检查文件名是否匹配指定模式的辅助方法"""
        if not pattern.strip():
            return True
            
        try:
            if mode == "前缀":
                return file_name.startswith(pattern)
            elif mode == "后缀":
                return file_name.endswith(pattern)
            elif mode == "包含关键词":
                return pattern in file_name
            elif mode == "正则匹配":
                import re
                return bool(re.search(pattern, file_name))
            else:
                return True
        except Exception:
            return False

    def on_apply_new_filter(self):
        """应用新的筛选逻辑"""
        if not self.original_file_data:
            QMessageBox.warning(self, "提示", "请先添加文件")
            return
            
        # 获取筛选条件
        filter_mode = self.filter_mode_combo.currentText()
        filter_pattern = self.filter_pattern_edit.text().strip()
        skip_mode = self.skip_mode_combo.currentText()
        skip_pattern = self.skip_pattern_edit.text().strip()
        
        # 基于原始数据进行筛选
        filtered_data = []
        for item in self.original_file_data:
            src_path, original_name, processed_info = item
            path = Path(src_path)
            file_name = original_name
            
            # 第一步：应用筛选模式
            if filter_pattern:
                if not self._matches_pattern(file_name, filter_pattern, filter_mode):
                    continue
            
            # 第二步：应用跳过模式（基于筛选结果）
            if skip_pattern:
                if self._matches_pattern(file_name, skip_pattern, skip_mode):
                    continue
            
            filtered_data.append(item)
        
        # 更新文件数据
        self.file_data = filtered_data
        
        # 重建左侧树
        self._rebuild_left_tree()
        
        # 更新预览
        self.on_preview()
        
        # 不再显示筛选结果弹窗

    def on_reset_filter(self):
        """重置筛选，显示所有原始文件"""
        if not self.original_file_data:
            QMessageBox.warning(self, "提示", "没有原始文件数据")
            return
            
        # 恢复原始文件数据
        self.file_data = self.original_file_data.copy()
        
        # 重建左侧树
        self._rebuild_left_tree()
        
        # 更新预览
        self.on_preview()
        
        # 清空筛选条件
        self.filter_pattern_edit.clear()
        self.skip_pattern_edit.clear()
        
        # 不再显示重置完成弹窗

    def on_apply_filter(self):
        """应用文件过滤和排序 - 支持通配符和正则表达式（保留原有方法用于兼容性）"""
        if not self.file_data:
            return
            
        # 获取过滤条件
        filter_text = self.file_filter_edit.text().strip()
        filters = [f.strip().lower() for f in filter_text.split(',') if f.strip()]
        
        # 过滤文件
        filtered_data = []
        for item in self.file_data:
            src_path, original_name, processed_info = item
            path = Path(src_path)
            
            # 应用文件类型过滤 - 支持通配符和正则表达式
            if filters:
                file_name = path.name.lower()
                ext = path.suffix.lower()
                
                # 检查是否匹配任意过滤器
                matched = False
                for filter_pattern in filters:
                    # 支持通配符匹配 (*, ?)
                    if '*' in filter_pattern or '?' in filter_pattern:
                        import fnmatch
                        if fnmatch.fnmatch(file_name, filter_pattern):
                            matched = True
                            break
                        if fnmatch.fnmatch(ext, filter_pattern):
                            matched = True
                            break
                    # 支持正则表达式匹配
                    elif any(c in filter_pattern for c in ['[', ']', '.', '+', '^', '$']):
                        import re
                        try:
                            if re.search(filter_pattern, file_name):
                                matched = True
                                break
                            if re.search(filter_pattern, ext):
                                matched = True
                                break
                        except re.error:
                            # 正则表达式错误，使用普通文本匹配
                            if filter_pattern in file_name or filter_pattern in ext:
                                matched = True
                                break
                    # 普通文本匹配（包含匹配）
                    else:
                        if filter_pattern in file_name or filter_pattern in ext:
                            matched = True
                            break
                
                if not matched:
                    continue
            
            filtered_data.append(item)
        
        # 更新文件数据
        self.file_data = filtered_data
        
        # 重建左侧树
        self._rebuild_left_tree()
        
        # 更新预览
        self.on_preview()

    def sync_column_widths(self):
        if not self.sync_column_enabled:
            return
        for col in range(4):
            left_width = self.left_tree.columnWidth(col)
            right_width = self.right_tree.columnWidth(col)
            if left_width != right_width:
                self.right_tree.setColumnWidth(col, left_width)

    def on_left_column_resized(self, logicalIndex, oldSize, newSize):
        if self.sync_column_enabled:
            self.right_tree.setColumnWidth(logicalIndex, newSize)

    def on_right_column_resized(self, logicalIndex, oldSize, newSize):
        if self.sync_column_enabled:
            self.left_tree.setColumnWidth(logicalIndex, newSize)

    def on_apply_all(self):
        """执行全部重命名操作，包含完整的冲突检测（无弹窗版）"""
        if not self.file_data:
            return

        # 计算所有重命名操作并进行冲突检测
        rename_ops = []
        new_names: Set[str] = set()  # 用于检测内部冲突
        
        for idx, (src_path, original_name, processed_info) in enumerate(self.file_data):
            src = Path(src_path)
            if not src.exists():
                continue
                
            parts, _ = self.build_new_name(original_name, idx)
            new_name = ''.join([text for text, _ in parts])
            dst = src.with_name(new_name)
            
            if src == dst:
                continue
                
            # 检测内部冲突（同一批重命名中的重复）
            if new_name in new_names:
                # 有冲突时直接返回，不执行任何操作
                return
                
            # 检测外部冲突（目标文件已存在）
            if dst.exists():
                # 有外部冲突时跳过这些文件
                continue
                    
            # 只有在确认要重命名时才添加到集合中
            new_names.add(new_name)
            rename_ops.append((src, dst))

        if not rename_ops:
            return

        # 执行重命名操作
        performed = []
        failed = []
        
        for src, dst in rename_ops:
            try:
                src.rename(dst)
                performed.append((src, dst))
            except Exception as e:
                failed.append(f"{src.name}: {str(e)}")
                print(f"重命名错误: {e}")

        # 处理结果
        if performed:
            # 为撤销保存：存入 (dst, src) 列表，便于撤销时把 dst -> src
            undo_list = [(dst, src) for src, dst in performed]
            self.last_undo_stack.append(undo_list)

            # 更新 file_data 中对应路径
            performed_srcs = {str(src): str(dst) for src, dst in performed}
            for i, (path_str, original_name, _) in enumerate(self.file_data):
                if path_str in performed_srcs:
                    new_path = performed_srcs[path_str]
                    self.file_data[i] = (new_path, Path(new_path).name, {})

            # 重建左侧树
            self._rebuild_left_tree()
        
        self.on_preview()

    def on_undo(self):
        """执行撤销操作，包含完整的错误处理（无弹窗版）"""
        if not self.last_undo_stack:
            return

        inverse_ops = self.last_undo_stack.pop()
        performed = []
        failed = []
        
        for dst_path, src_path in inverse_ops:
            try:
                # 检查源文件是否存在
                if not dst_path.exists():
                    # 源文件不存在，跳过
                    continue
                    
                # 检查目标文件是否已存在，存在则跳过不覆盖
                if src_path.exists():
                    # 目标已存在，跳过
                    continue
                        
                # 执行撤销重命名
                dst_path.rename(src_path)
                performed.append((dst_path, src_path))
                
            except Exception as e:
                # 静默处理错误，不记录也不弹窗
                pass

        # 更新文件数据和界面
        if performed:
            # 更新 file_data 中对应路径（把 dst -> src）
            for dst_path, src_path in performed:
                dst_str = str(dst_path)
                src_str = str(src_path)
                for i, (path_str, original_name, _) in enumerate(self.file_data):
                    if path_str == dst_str:  # 用重命名后的路径(dst)来查找需要撤销的项目
                        self.file_data[i] = (src_str, Path(src_str).name, {})
                        break
                        
            # 重建左侧树
            self._rebuild_left_tree()

        self.on_preview()

    def copy_selected_path(self):
        """复制选中项的路径"""
        selected_indexes = self.left_tree.selectedIndexes() or self.right_tree.selectedIndexes()
        if selected_indexes:
            paths = []
            for index in selected_indexes:
                if index.column() == 2:  # 路径列
                    path = index.data()
                    if path:
                        paths.append(path)
                else:
                    # 从其他列获取路径
                    item = self.left_model.itemFromIndex(index) if index.model() == self.left_model else self.right_model.itemFromIndex(index)
                    if item:
                        path = item.data(Qt.UserRole)
                        if path:
                            paths.append(path)
            if paths:
                QApplication.clipboard().setText("\n".join(paths))

    def eventFilter(self, obj, event):
        """事件过滤器 - 处理鼠标移动事件以同步悬停状态"""
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            # 右键按下时，确保悬停状态正确设置
            if obj == self.left_tree.viewport():
                index = self.left_tree.indexAt(event.pos())
                if index.isValid():
                    self.left_hover_row = index.row()
                    self.right_hover_row = index.row()
                    self.left_tree.viewport().update()
                    self.right_tree.viewport().update()
            elif obj == self.right_tree.viewport():
                index = self.right_tree.indexAt(event.pos())
                if index.isValid():
                    self.right_hover_row = index.row()
                    self.left_hover_row = index.row()
                    self.left_tree.viewport().update()
                    self.right_tree.viewport().update()
                    
        elif event.type() == QEvent.MouseMove:
            if obj == self.left_tree.viewport():
                # 左侧树鼠标移动
                index = self.left_tree.indexAt(event.pos())
                new_hover_row = index.row() if index.isValid() else -1
                
                if new_hover_row != self.left_hover_row:
                    self.left_hover_row = new_hover_row
                    # 同步到右侧树
                    if new_hover_row >= 0:
                        self.right_hover_row = new_hover_row
                    # 重绘两个树视图
                    self.left_tree.viewport().update()
                    self.right_tree.viewport().update()
                    
            elif obj == self.right_tree.viewport():
                # 右侧树鼠标移动
                index = self.right_tree.indexAt(event.pos())
                new_hover_row = index.row() if index.isValid() else -1
                
                if new_hover_row != self.right_hover_row:
                    self.right_hover_row = new_hover_row
                    # 同步到左侧树
                    if new_hover_row >= 0:
                        self.left_hover_row = new_hover_row
                    # 重绘两个树视图
                    self.left_tree.viewport().update()
                    self.right_tree.viewport().update()
                    
        elif event.type() == QEvent.Leave:
            # 鼠标离开视图区域 - 检查是否有右键菜单正在显示
            # 通过检查是否有活动的弹出窗口来判断
            from PyQt5.QtWidgets import QApplication
            active_popup = QApplication.activePopupWidget()
            
            # 如果没有活动的弹出窗口（右键菜单），才清除悬停状态
            if not active_popup:
                if obj == self.left_tree.viewport():
                    self.left_hover_row = -1
                    self.left_tree.viewport().update()
                    self.right_tree.viewport().update()
                elif obj == self.right_tree.viewport():
                    self.right_hover_row = -1
                    self.left_tree.viewport().update()
                    self.right_tree.viewport().update()
                
        return super().eventFilter(obj, event)

    def on_tree_context_menu(self, position):
        """树视图右键菜单"""
        # 获取发送信号的树视图
        tree_view = self.sender()
        if not tree_view:
            return
            
        # 获取点击位置的索引
        index = tree_view.indexAt(position)
        if not index.isValid():
            return
            
        # 保存当前选择状态，右键菜单不改变选择状态
        # 阻止Qt默认的右键选择行为，保持当前选中状态
        selection_model = tree_view.selectionModel()
        current_selection = selection_model.selection()
        
        # 保存当前悬停状态，防止右键菜单期间丢失
        saved_left_hover = self.left_hover_row
        saved_right_hover = self.right_hover_row
        
        # 创建右键菜单
        menu = QMenu()
        
        # 添加复制路径菜单项
        copy_path_action = menu.addAction("复制路径")
        copy_name_action = menu.addAction("复制文件名")
        menu.addSeparator()
        open_folder_action = menu.addAction("打开所在文件夹")
        menu.addSeparator()
        
        # 选择相关菜单项
        select_all_action = menu.addAction("全选(&A)")
        select_none_action = menu.addAction("全不选(&A)")
        invert_selection_action = menu.addAction("反选(&F)")
        select_same_type_action = menu.addAction("选择同类型")
        menu.addSeparator()
        
        # 移除相关菜单项
        remove_selected_action = menu.addAction("移除选定项")
        remove_unselected_action = menu.addAction("移除未选定项")
        clear_window_action = menu.addAction("清空窗口")
        
        # 显示菜单并获取用户选择
        action = menu.exec_(tree_view.viewport().mapToGlobal(position))
        
        # 恢复原来的选择状态，确保右键菜单不改变选择
        selection_model.select(current_selection, QItemSelectionModel.ClearAndSelect)
        
        # 恢复悬停状态
        self.left_hover_row = saved_left_hover
        self.right_hover_row = saved_right_hover
        # 重绘两个树视图确保菱形显示正确
        self.left_tree.viewport().update()
        self.right_tree.viewport().update()
        
        # 处理菜单项选择
        if action == copy_path_action:
            self._copy_item_path(index, full_path=True)
        elif action == copy_name_action:
            self._copy_item_path(index, full_path=False)
        elif action == open_folder_action:
            self._open_item_folder(index)
        elif action == select_all_action:
            self._select_all_items(tree_view)
        elif action == select_none_action:
            self._select_none_items(tree_view)
        elif action == invert_selection_action:
            self._invert_selection(tree_view)
        elif action == select_same_type_action:
            self._select_same_type(tree_view)
        elif action == remove_selected_action:
            self._remove_selected_items(tree_view)
        elif action == remove_unselected_action:
            self._remove_unselected_items(tree_view)
        elif action == clear_window_action:
            self._clear_window()
    
    def _copy_item_path(self, index, full_path=True):
        """复制项目路径或文件名"""
        if not index.isValid():
            return
            
        # 获取路径数据 - 优先从第3列（路径列）获取
        path_data = None
        model = index.model()
        
        # 尝试从第3列获取路径（路径列）
        path_index = model.index(index.row(), 3)
        if path_index.isValid():
            path_data = path_index.data()
        
        # 如果第3列没有数据，尝试从当前列获取
        if not path_data:
            path_data = index.data()
            
        # 如果还是没有，尝试从UserRole获取
        if not path_data:
            item = self.left_model.itemFromIndex(index) if model == self.left_model else self.right_model.itemFromIndex(index)
            if item:
                path_data = item.data(Qt.UserRole)
        
        if path_data:
            if full_path:
                # 复制完整路径
                QApplication.clipboard().setText(path_data)
            else:
                # 复制文件名
                file_name = Path(path_data).name
                QApplication.clipboard().setText(file_name)
        else:
            QMessageBox.warning(self, "错误", f"无法获取有效的文件路径: {path_data}")
    
    def _open_item_folder(self, index):
        """打开项目所在文件夹"""
        if not index.isValid():
            QMessageBox.warning(self, "错误", "无效的项目索引")
            return
            
        # 获取路径数据 - 优先从第3列（路径列）获取
        path_data = None
        model = index.model()
        
        # 尝试从第3列获取路径（路径列）
        try:
            path_index = model.index(index.row(), 3)
            if path_index.isValid():
                path_data = path_index.data()
        except Exception as e:
            pass
        
        # 如果第3列没有数据，尝试从当前列获取
        if not path_data:
            try:
                path_data = index.data()
            except Exception as e:
                pass
            
        # 如果还是没有，尝试从UserRole获取
        if not path_data:
            try:
                if model == self.left_model:
                    item = self.left_model.itemFromIndex(index)
                else:
                    item = self.right_model.itemFromIndex(index)
                if item:
                    path_data = item.data(Qt.UserRole)
            except Exception as e:
                pass
        
        if path_data:
            try:
                file_path = Path(path_data)
                
                if file_path.exists():
                    folder_path = file_path.parent
                    
                    # 使用多种方式尝试打开文件夹
                    try:
                        result = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder_path)))
                        if not result:
                            # 备用方法：使用系统命令
                            import subprocess
                            subprocess.Popen(['explorer', str(folder_path)])
                    except Exception as e:
                        # 备用方法：使用系统命令
                        import subprocess
                        subprocess.Popen(['explorer', str(folder_path)])
                else:
                    QMessageBox.warning(self, "错误", f"文件不存在: {path_data}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"处理路径时出错: {str(e)}")
        else:
            QMessageBox.warning(self, "错误", "无法获取文件路径")
    
    def _select_all_items(self, tree_view):
        """全选"""
        tree_view.selectAll()
    
    def _select_none_items(self, tree_view):
        """全不选"""
        tree_view.clearSelection()
    
    def _invert_selection(self, tree_view):
        """反选"""
        model = tree_view.model()
        selection_model = tree_view.selectionModel()
        
        # 获取所有行的索引
        all_indexes = []
        selected_indexes = []
        
        for row in range(model.rowCount()):
            index = model.index(row, 2)  # 使用第2列（路径列）
            all_indexes.append(index)
            if selection_model.isSelected(index):
                selected_indexes.append(index)
        
        # 反选逻辑：清除当前选择，选择之前未选中的
        selection_model.clearSelection()
        
        # 选择之前未选中的项
        for index in all_indexes:
            if index not in selected_indexes:
                selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
    
    def _select_same_type(self, tree_view):
        """选择同类型（按后缀）"""
        selection_model = tree_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        
        if not selected_indexes:
            return
        
        # 收集所有选中的文件后缀
        extensions = set()
        model = tree_view.model()
        
        for index in selected_indexes:
            if index.column() == 2:  # 路径列
                path_data = index.data()
                if path_data:
                    ext = Path(path_data).suffix.lower()
                    if ext:
                        extensions.add(ext)
        
        if not extensions:
            QMessageBox.information(self, "提示", "没有选中任何文件或文件没有后缀")
            return
        
        # 选择所有相同后缀的文件
        selection_model.clearSelection()
        
        for row in range(model.rowCount()):
            index = model.index(row, 2)  # 路径列
            path_data = index.data()
            if path_data:
                ext = Path(path_data).suffix.lower()
                if ext in extensions:
                    selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
    
    def _remove_selected_items(self, tree_view):
        """移除选定项"""
        selection_model = tree_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        
        if not selected_indexes:
            QMessageBox.information(self, "提示", "没有选中的项目")
            return
        
        # 获取所有选中的行
        rows_to_remove = set()
        for index in selected_indexes:
            rows_to_remove.add(index.row())
        
        # 确认删除
        reply = QMessageBox.question(self, "确认", f"确定要移除选中的 {len(rows_to_remove)} 个项目吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 按行号降序排序，从大到小删除
            # 重要：必须从两个模型中同时删除对应的行
            for row in sorted(rows_to_remove, reverse=True):
                self.left_model.removeRow(row)
                self.right_model.removeRow(row)
            
            # 更新文件数据
            self._update_file_data_after_remove()
    
    def _remove_unselected_items(self, tree_view):
        """移除未选定项"""
        selection_model = tree_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        
        if not selected_indexes:
            QMessageBox.information(self, "提示", "没有选中的项目，将移除所有项目")
            reply = QMessageBox.question(self, "确认", "确定要移除所有项目吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 重要：必须同时清空两个模型
                self.left_model.clear()
                self.right_model.clear()
                self._update_file_data_after_remove()
            return
        
        # 获取所有选中的行
        selected_rows = set()
        for index in selected_indexes:
            selected_rows.add(index.row())
        
        # 获取所有行数
        total_rows = self.left_model.rowCount()  # 使用左模型获取总行数
        unselected_rows = set(range(total_rows)) - selected_rows
        
        if not unselected_rows:
            QMessageBox.information(self, "提示", "所有项目都被选中，没有可移除的项目")
            return
        
        # 确认删除
        reply = QMessageBox.question(self, "确认", f"确定要移除未选中的 {len(unselected_rows)} 个项目吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 按行号降序排序，从大到小删除
            # 重要：必须从两个模型中同时删除对应的行
            for row in sorted(unselected_rows, reverse=True):
                self.left_model.removeRow(row)
                self.right_model.removeRow(row)
            
            # 更新文件数据
            self._update_file_data_after_remove()
    
    def _clear_window(self):
        """清空窗口 - 使用现有的on_clear逻辑"""
        # 直接调用现有的清空逻辑
        self.on_clear()
    
    def _update_file_data_after_remove(self):
        """移除项目后更新文件数据"""
        # 获取左右树视图中剩余的项目
        remaining_paths = set()
        
        # 从左树获取 - 第3列是路径列，使用完整绝对路径作为唯一键
        for row in range(self.left_model.rowCount()):
            path_item = self.left_model.item(row, 3)
            if path_item and path_item.text():
                # 使用完整绝对路径避免同名文件误删
                try:
                    abs_path = str(Path(path_item.text()).resolve())
                    remaining_paths.add(abs_path)
                except Exception:
                    # 如果路径解析失败，使用原始路径
                    remaining_paths.add(path_item.text())
        
        # 更新file_data，只保留仍在树视图中的项目
        new_file_data = []
        for path, original_name, highlight_info in self.file_data:
            try:
                abs_path = str(Path(path).resolve())
                if abs_path in remaining_paths:
                    new_file_data.append((path, original_name, highlight_info))
            except Exception:
                # 如果路径解析失败，使用原始路径匹配
                if path in remaining_paths:
                    new_file_data.append((path, original_name, highlight_info))
        
        self.file_data = new_file_data
        
        # 重新构建预览 - 确保右窗口内容正确更新
        try:
            self.on_preview()
        except Exception as e:
            # 如果预览失败，至少保持左右窗口同步
            self._sync_models_after_remove()
            
            # 如果还有数据但预览失败，至少保持左右窗口同步
            if self.file_data:
                self.right_model.clear()
                self.right_model.setHorizontalHeaderLabels(['序号', '箭头', '新名称', '路径', '原始序号'])
                # 不再调用不存在的函数，仅同步模型
    
    def _sync_models_after_remove(self):
        """移除项目后同步左右模型"""
        # 确保右模型与左模型保持同步
        left_row_count = self.left_model.rowCount()
        right_row_count = self.right_model.rowCount()
        
        if left_row_count != right_row_count:
            # 重新同步行数
            if left_row_count > right_row_count:
                # 添加缺失的行到右模型
                for row in range(right_row_count, left_row_count):
                    items = []
                    for col in range(5):
                        item = QStandardItem()
                        items.append(item)
                    self.right_model.appendRow(items)
            else:
                # 移除多余的行从右模型
                self.right_model.removeRows(left_row_count, right_row_count - left_row_count)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        """主窗口初始化 - 增强错误处理"""
        try:
            super().__init__(parent)
            # self.setWindowTitle("批量重命名工具")
            self._build_ui()
            self.status = QStatusBar()
            self.setStatusBar(self.status)
            self.setAcceptDrops(True)
        except Exception as e:
            print(f"主窗口初始化错误: {e}")
            # 显示错误提示
            QMessageBox.critical(self, "初始化错误", f"主窗口初始化失败: {str(e)}")
            # 确保程序可以继续运行
            pass

    # def showEvent(self, event):
    #     """窗口显示事件 - 在第一次显示时居中"""
    #     super().showEvent(event)
    #     # 只在第一次显示时居中
    #     if not hasattr(self, '_centered'):
    #         # 使用QTimer延迟居中，确保窗口完全初始化
    #         QTimer.singleShot(100, self._center_window)
    #         self._centered = True

    # def _center_window(self):
    #     """将窗口居中显示"""
    #     try:
    #         # 获取屏幕几何信息
    #         screen = QApplication.primaryScreen()
    #         screen_geometry = screen.availableGeometry()
    #         
    #         # 获取窗口几何信息
    #         window_geometry = self.frameGeometry()
    #         
    #         # 计算居中位置
    #         center_point = screen_geometry.center()
    #         window_geometry.moveCenter(center_point)
    #         
    #         # 移动窗口到居中位置
    #         self.move(window_geometry.topLeft())
    #         print(f"窗口已居中: 位置 {window_geometry.topLeft().x()}, {window_geometry.topLeft().y()}")
    #     except Exception as e:
    #         print(f"窗口居中错误: {e}")
    #         # 如果居中失败，使用备用方案
    #         try:
    #             # 简单的居中方案
    #             self.move(100, 100)
    #             print("使用备用居中方案")
    #         except:
    #             pass

    def _build_ui(self):
        """构建UI - 增强错误处理"""
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            self.rename_widget = BatchRenameWidget()
            main_layout.addWidget(self.rename_widget)

            self.resize(1000, 700)
            # 不在此处居中，改为在showEvent中处理
            
        except Exception as e:
            print(f"UI构建错误: {e}")
            # 显示错误提示
            QMessageBox.critical(self, "构建错误", f"界面构建失败: {str(e)}")
            # 确保程序可以继续运行
            pass

    def dragEnterEvent(self, event):
        """拖拽进入事件 - 增强错误处理"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                super().dragEnterEvent(event)
        except Exception as e:
            print(f"拖拽进入事件错误: {e}")
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """拖拽移动事件 - 增强错误处理"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                super().dragMoveEvent(event)
        except Exception as e:
            print(f"拖拽移动事件错误: {e}")
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """拖拽放下事件 - 增强错误处理"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                paths = []
                
                # 安全地处理URL转换
                for url in urls:
                    try:
                        local_file = url.toLocalFile()
                        if local_file:  # 确保转换成功
                            paths.append(Path(local_file))
                    except Exception as url_error:
                        # 记录单个URL转换失败的错误，但继续处理其他URL
                        print(f"警告: 无法转换URL {url.toString()}: {str(url_error)}")
                        continue
                
                if paths:  # 只有在有有效路径时才继续处理
                    # 检查是否有文件夹被拖入
                    folder_paths = [p for p in paths if p.is_dir()]
                    file_paths = [p for p in paths if p.is_file()]
                    
                    # 如果有文件夹，显示选择对话框
                    if folder_paths:
                        dialog = FolderDropDialog(self)
                        if dialog.exec_() == QDialog.Accepted:
                            mode = dialog.selected_mode
                            recursive = dialog.recursive_checked
                            
                            try:
                                if mode == "files":
                                    # 文件名模式：导入文件夹内的文件
                                    self.rename_widget.add_paths(folder_paths, recursive)
                                else:
                                    # 文件夹名模式：导入文件夹本身
                                    self.rename_widget.add_folder_names(folder_paths, recursive)
                            except Exception as e:
                                print("拖拽加载失败:", e)
                                QMessageBox.warning(self, "拖拽失败", f"文件加载失败: {str(e)}")
                        else:
                            # 用户取消了对话框
                            event.acceptProposedAction()
                            return
                    
                    # 处理文件路径（如果有的话）
                    if file_paths:
                        try:
                            # 文件拖拽时不需要递归处理，直接使用False
                            recursive = False
                            print(f"拖拽添加文件，递归模式: {recursive}")  # 调试用
                            self.rename_widget.add_paths(file_paths, recursive)
                        except Exception as e:
                            print("文件拖拽加载失败:", e)
                            QMessageBox.warning(self, "拖拽失败", f"文件加载失败: {str(e)}")
                
                event.acceptProposedAction()
            else:
                super().dropEvent(event)
        except Exception as e:
            print(f"拖拽放下事件错误: {e}")
            # 显示用户友好的错误提示
            QMessageBox.warning(self, "拖拽错误", f"拖拽操作失败: {str(e)}")
            # 确保事件被正确处理，避免拖拽状态卡住
            event.ignore()
            super().dropEvent(event)

    def keyPressEvent(self, event):
        """键盘事件 - 增强错误处理"""
        try:
            # 复制快捷键处理
            if event.matches(QKeySequence.Copy):
                if self.rename_widget:
                    self.rename_widget.copy_selected_path()
                return
            
            # Ctrl+Z 撤销功能
            if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
                if self.rename_widget and hasattr(self.rename_widget, 'on_undo'):
                    self.rename_widget.on_undo()
                return
            
            # 处理新的快捷键 - 使用更安全的组合键避免冲突
            modifiers = event.modifiers()
            key = event.key()
            
            # 使用 Ctrl+Shift+Alt 组合来避免与系统快捷键冲突
            if modifiers == (Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier):
                focused_widget = QApplication.focusWidget()
                
                if key == Qt.Key_A:
                    # Ctrl+Shift+Alt+A 全选
                    if focused_widget == self.rename_widget.left_tree:
                        self.rename_widget._select_all_items(self.rename_widget.left_tree)
                    elif focused_widget == self.rename_widget.right_tree:
                        self.rename_widget._select_all_items(self.rename_widget.right_tree)
                    return
                elif key == Qt.Key_N:
                    # Ctrl+Shift+Alt+N 全不选
                    if focused_widget == self.rename_widget.left_tree:
                        self.rename_widget._select_none_items(self.rename_widget.left_tree)
                    elif focused_widget == self.rename_widget.right_tree:
                        self.rename_widget._select_none_items(self.rename_widget.right_tree)
                    return
                elif key == Qt.Key_I:
                    # Ctrl+Shift+Alt+I 反选
                    if focused_widget == self.rename_widget.left_tree:
                        self.rename_widget._invert_selection(self.rename_widget.left_tree)
                    elif focused_widget == self.rename_widget.right_tree:
                        self.rename_widget._invert_selection(self.rename_widget.right_tree)
                    return
            
            super().keyPressEvent(event)
        except Exception as e:
            print(f"键盘事件错误: {e}")
            # 可选：显示错误提示
            # QMessageBox.warning(self, "快捷键错误", f"快捷键操作失败: {str(e)}")
            super().keyPressEvent(event)


def main():
    """主函数 - 增强错误处理"""
    try:
        app = QApplication(sys.argv)
        w = MainWindow()
        w.show()
        # 不需要在这里调用居中，因为showEvent已经处理了居中逻辑
        # w._center_window()  # 移除这行以避免重复居中
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动错误: {e}")
        # 显示错误提示
        QMessageBox.critical(None, "启动错误", f"程序启动失败: {str(e)}")
        sys.exit(1)


# if __name__ == "__main__":
#     """程序入口 - 增强错误处理"""
#     try:
#         main()
#     except Exception as e:
#         print(f"程序运行错误: {e}")
#         # 最后的错误处理
#         QMessageBox.critical(None, "运行错误", f"程序运行失败: {str(e)}")
#         sys.exit(1)
