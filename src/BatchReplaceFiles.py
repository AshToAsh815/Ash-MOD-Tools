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

import os
import sys
import shutil
import re
import time
import json
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QTreeWidget,
    QTreeWidgetItem, QProgressBar, QGroupBox, QComboBox,
    QSizePolicy, QMessageBox, QStyle, QSplitter, QMenu, QAction,
    QTextEdit, QDialog, QFormLayout, QCheckBox, QAbstractItemView,
    QKeySequenceEdit, QListWidget, QListWidgetItem, QHeaderView,
    QInputDialog, QFileIconProvider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QRegExp, QRect, QFileSystemWatcher, QPoint, QSettings, QTimer, QEvent, QFileInfo
from PyQt5.QtGui import (
    QDragEnterEvent, QDropEvent, QMouseEvent, QDragMoveEvent, 
    QColor, QKeySequence, QTextCursor, QTextCharFormat, QRegExpValidator,
    QKeyEvent, QPainter, QBrush, QPaintEvent, QIcon, QPixmap, QDesktopServices
)

# 导入编译后的资源文件（必须保留，否则图标无法加载）
import resources


class FindDialog(QDialog):
    """查找对话框（已无用，保留避免报错）"""
    def __init__(self, parent=None, text_edit=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self.setWindowTitle("查找")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.find_input = QLineEdit()
        form_layout.addRow("查找内容:", self.find_input)
        buttons_layout = QHBoxLayout()
        self.find_next_btn = QPushButton("查找下一个")
        self.cancel_btn = QPushButton("取消")
        buttons_layout.addWidget(self.find_next_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addLayout(form_layout)
        layout.addLayout(buttons_layout)
        
        # 添加悬停提示
        self.find_input.setToolTip("输入要查找的文本内容")
        self.find_next_btn.setToolTip("查找下一个匹配项")
        self.cancel_btn.setToolTip("取消查找操作")


class EnhancedTextEdit(QTextEdit):
    """增强版文本编辑框（修复日志颜色异常问题）"""
    def __init__(self, parent=None, is_log=False):
        super().__init__(parent)
        self.is_log = is_log
        self.setReadOnly(True)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | 
            Qt.TextSelectableByKeyboard | 
            Qt.LinksAccessibleByMouse | 
            Qt.LinksAccessibleByKeyboard
        )
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setFocusPolicy(Qt.StrongFocus)
        self.add_shortcuts()
        # 保存默认格式
        self.default_format = QTextCharFormat(self.currentCharFormat())
        
        # 添加悬停提示
        self.setToolTip("显示结果或日志信息，可选中复制内容")

    def add_shortcuts(self):
        """仅保留复制、全选快捷键"""
        # 复制
        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy)
        copy_action.setToolTip("复制选中的内容 (Ctrl+C)")
        self.addAction(copy_action)
        
        # 全选
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.selectAll)
        select_all_action.setToolTip("选中所有内容 (Ctrl+A)")
        self.addAction(select_all_action)

    def keyPressEvent(self, event: QKeyEvent):
        """仅处理复制、全选快捷键"""
        if event.matches(QKeySequence.Copy):
            self.copy()
            event.accept()
        elif event.matches(QKeySequence.SelectAll):
            self.selectAll()
            event.accept()
        else:
            if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, 
                              Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End) or \
               event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                event.ignore()

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        super().mousePressEvent(event)

    def show_context_menu(self, position):
        """右键菜单（移除查找）"""
        menu = QMenu()
        
        # 复制
        copy_action = menu.addAction("复制")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(not self.textCursor().selection().isEmpty())
        copy_action.setToolTip("复制选中的内容 (Ctrl+C)")
        
        # 全选
        select_all_action = menu.addAction("全选")
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.selectAll)
        select_all_action.setEnabled(not self.toPlainText().strip() == "")
        select_all_action.setToolTip("选中所有内容 (Ctrl+A)")
        
        menu.addSeparator()
        
        # 清空
        clear_action = menu.addAction("清空")
        clear_action.triggered.connect(self.clear)
        clear_action.setEnabled(not self.toPlainText().strip() == "")
        clear_action.setToolTip("清空当前窗口内容")
        
        menu.exec_(self.mapToGlobal(position))

    def append_text(self, text, color=None):
        """修复颜色异常问题：每次添加文本后强制恢复默认格式"""
        self.blockSignals(True)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        # 保存当前格式
        current_format = QTextCharFormat(self.currentCharFormat())
        
        if color:
            temp_format = QTextCharFormat(current_format)
            temp_format.setForeground(color)
            self.setCurrentCharFormat(temp_format)
        
        self.insertPlainText(text + "\n")
        
        # 强制恢复为默认格式，修复颜色继承问题
        self.setCurrentCharFormat(QTextCharFormat(self.default_format))
        
        self.blockSignals(False)
        self.moveCursor(QTextCursor.End)


class ShortcutLineEdit(QLineEdit):
    """自定义快捷键输入框，确保正确显示中文"""
    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        # 将右键菜单翻译成中文
        for action in menu.actions():
            text = action.text()
            if "撤销" not in text and "Undo" in text:
                action.setText("撤销")
                action.setToolTip("撤销上一步操作 (Ctrl+Z)")
            elif "重做" not in text and "Redo" in text:
                action.setText("重做")
                action.setToolTip("重做上一步操作 (Ctrl+Y)")
            elif "剪切" not in text and "Cut" in text:
                action.setText("剪切")
                action.setToolTip("剪切选中的内容 (Ctrl+X)")
            elif "复制" not in text and "Copy" in text:
                action.setText("复制")
                action.setToolTip("复制选中的内容 (Ctrl+C)")
            elif "粘贴" not in text and "Paste" in text:
                action.setText("粘贴")
                action.setToolTip("粘贴剪贴板内容 (Ctrl+V)")
            elif "删除" not in text and "Delete" in text:
                action.setText("删除")
                action.setToolTip("删除选中的内容 (Delete)")
            elif "全选" not in text and "Select All" in text:
                action.setText("全选")
                action.setToolTip("选中所有内容 (Ctrl+A)")
        menu.exec_(event.globalPos())


class DraggableLineEdit(ShortcutLineEdit):
    """可拖拽输入框（保留原逻辑）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setToolTip("可直接拖拽文件/文件夹到此处")

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(path)


class FileReplacerThread(QThread):
    """文件替换线程（保留原逻辑）"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str, QColor)  # 添加颜色参数

    def __init__(self, source_file, targets, backup_dir=None, preview_only=False, restore=False, target_root=None, restore_map=None):
        super().__init__()
        self.source_file = source_file
        self.targets = targets[:]
        self.backup_dir = backup_dir
        self.preview_only = preview_only
        self.restore = restore
        self.target_root = target_root
        self.restore_map = restore_map or {}
        self.is_running = True

    def run(self):
        results = []
        total = len(self.targets)
        if total == 0:
            self.finished_signal.emit(["未找到匹配的文件 {未找到匹配的文件}"])
            return
        if self.preview_only:
            for full in self.targets:
                filename = os.path.basename(full)
                results.append(f"{filename} {{{full}}}")
            self.finished_signal.emit(results)
            return
        
        for idx, full in enumerate(self.targets):
            if not self.is_running:
                results.append(("error", f"{full} - 操作被终止"))
                break
            
            filename = os.path.basename(full)
            disp = f"{filename} {{{full}}}"
            try:
                if self.restore:
                    # 当提供 restore_map 时，按映射还原，不强制要求备份目录存在
                    if self.restore_map:
                        original_target_path = self.restore_map.get(full)
                        if not original_target_path:
                            results.append(("error", f"{disp} - 缺少还原映射"))
                            self.log_signal.emit(f"错误：{disp} - 缺少还原映射", QColor(Qt.red))
                            continue
                    else:
                        if not self.backup_dir or not os.path.exists(self.backup_dir):
                            results.append(("error", f"{disp} - 备份目录不存在"))
                            self.log_signal.emit(f"错误：{disp} - 备份目录不存在", QColor(Qt.red))
                            continue
                        if not self.target_root or not os.path.exists(self.target_root):
                            results.append(("error", f"{disp} - 备份时的目标根路径无效"))
                            self.log_signal.emit(f"错误：{disp} - 备份时的目标根路径无效", QColor(Qt.red))
                            continue
                        rel_path = os.path.relpath(full, self.backup_dir)
                        original_target_path = os.path.normpath(os.path.join(self.target_root, rel_path))
                    
                    if not os.path.exists(full):
                        results.append(("error", f"{disp} - 备份文件不存在：{full}"))
                        self.log_signal.emit(f"错误：{disp} - 备份文件不存在：{full}", QColor(Qt.red))
                        continue
                    
                    success, msg = safe_copy(full, original_target_path)
                    if success:
                        results.append(("restore", f"{os.path.basename(original_target_path)} {{{original_target_path}}}"))
                        self.log_signal.emit(f"[还原成功] {original_target_path}", QColor(Qt.blue))
                    else:
                        results.append(("error", f"{os.path.basename(original_target_path)} {{{original_target_path}}} - 还原失败：{msg}"))
                        self.log_signal.emit(f"错误：{os.path.basename(original_target_path)} {{{original_target_path}}} - 还原失败：{msg}", QColor(Qt.red))
                
                else:
                    if self.backup_dir:
                        # 将备份文件直接放入同一备份文件夹（不再创建父级子目录）
                        backup_path = os.path.join(self.backup_dir, os.path.basename(full))
                        success, msg = safe_copy(full, backup_path)
                        if not success:
                            results.append(("error", f"{disp} - 备份失败：{msg}"))
                            self.log_signal.emit(f"错误：{disp} - 备份失败：{msg}", QColor(Qt.red))
                            continue
                        self.log_signal.emit(f"已备份：{full} → {backup_path}", QColor(Qt.darkGreen))
                    
                    success, msg = safe_copy(self.source_file, full)
                    if success:
                        results.append(("success", disp))
                        self.log_signal.emit(f"[替换成功] {disp}", QColor(Qt.blue))
                    else:
                        results.append(("error", f"{disp} - 替换失败：{msg}"))
                        self.log_signal.emit(f"错误：{disp} - 替换失败：{msg}", QColor(Qt.red))
            
            except Exception as e:
                error_details = f"{disp} - 未知错误：{str(e)}"
                results.append(("error", error_details))
                self.log_signal.emit(f"错误：{error_details}", QColor(Qt.red))
            
            percent = int((idx + 1) / total * 100)
            self.progress_signal.emit(percent, filename)
        
        self.finished_signal.emit(results)
    
    def stop(self):
        self.is_running = False


class DraggableTreeWidget(QTreeWidget):
    """增强版树状图（修复全选快捷键和搜索功能，实现懒加载）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 拖放设置
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DropOnly)
        self.setDropIndicatorShown(True)
        # 选择设置 - 改为类似Windows文件管理器的选择方式
        self.setSelectionMode(QTreeWidget.ExtendedSelection)  # 支持Shift/Ctrl选择
        self.setSelectionBehavior(QTreeWidget.SelectRows)
        self.setHeaderHidden(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 框选相关（移除视觉框，保留功能）
        self.is_dragging = False
        self.select_rect = QRect()
        self.last_click_pos = QPoint()
        # 滚动相关变量
        self.scroll_direction = 0
        self.scroll_timer = None
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_menu)
        # 父窗口引用
        self.main_window = None
        # 存储展开状态用于刷新后恢复
        self.expanded_paths = set()
        # 懒加载相关 - 记录已加载的目录
        self.loaded_dirs = set()
        # 在批量刷新/清空期间暂停展开/折叠状态的跟踪，避免误删保存的展开集合
        self.suspend_expand_tracking = False
        # 连接展开信号用于懒加载
        self.itemExpanded.connect(self.on_item_expanded)
        # 新增：连接折叠信号，及时维护展开状态集合
        self.itemCollapsed.connect(self.on_item_collapsed)
        # 安装事件过滤器处理右键点击
        self.viewport().installEventFilter(self)
        
        # 添加悬停提示
        self.setToolTip("显示文件和文件夹结构，可选择要操作的项目")

    def set_main_window(self, main_window):
        """设置父窗口引用（用于调用方法）"""
        self.main_window = main_window

    # 修复全选快捷键：确保树状图能处理Shift+A
    def keyPressEvent(self, event: QKeyEvent):
        if self.main_window:
            # 检查是否匹配自定义的全选快捷键
            if self.main_window.check_shortcut(event, 'select_all'):
                self.main_window.select_all_tree()
                event.accept()
                return
                
        super().keyPressEvent(event)

    # 右键点击事件过滤器 - 实现右键点击未选中项不取消已选
    def eventFilter(self, source, event):
        if source is self.viewport() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                # 始终弹出右键菜单，同时不改变现有选择状态
                try:
                    self.show_right_menu(event.pos())
                finally:
                    return True
        return super().eventFilter(source, event)

    # ---------------- 拖拽功能修复 ----------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        """支持文件和文件夹拖拽"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.scheme() == "file":
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """允许拖放移动"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽添加（修复拖入问题）"""
        event.setDropAction(Qt.CopyAction)
        event.accept()
        
        if not self.main_window:
            return

        for url in event.mimeData().urls():
            try:
                path = url.toLocalFile()
                if not path or not os.path.exists(path):
                    QMessageBox.warning(self.main_window, "无效路径", f"路径不存在: {path}")
                    continue
                
                # 检查是否已存在（修复问题2：允许在清空后重新拖入）
                exists = False
                for i in range(self.topLevelItemCount()):
                    top_item = self.topLevelItem(i)
                    if top_item.data(0, Qt.UserRole) == path:
                        exists = True
                        break
                
                # 特殊情况：如果树为空且路径在已移除列表中，允许重新添加
                if not exists and self.topLevelItemCount() == 0 and path in self.main_window.removed_items:
                    self.main_window.removed_items.remove(path)
                
                if exists:
                    QMessageBox.information(self.main_window, "提示", f"路径已存在: {path}")
                    continue
                
                # 添加到树状图，使用懒加载方式
                self.main_window.load_tree_lazy(path)
                if os.path.isdir(path):
                    self.main_window.log(f"已添加目录: {path}")
                else:
                    self.main_window.log(f"已添加文件: {path}")
            except Exception as e:
                self.main_window.log(f"拖放失败: {str(e)}", QColor(Qt.red))

    # ---------------- 懒加载实现 ----------------
    def on_item_expanded(self, item):
        """当项目被展开时加载其子项（懒加载，同时记录展开状态）"""
        path = item.data(0, Qt.UserRole)
        
        # 及时记录展开状态
        if path:
            self.expanded_paths.add(path)
        
        # 检查是否是目录且尚未加载
        if os.path.isdir(path) and path not in self.loaded_dirs:
            self.load_children(item, path)
            self.loaded_dirs.add(path)  # 标记为已加载
            # 保持一次记录即可，避免重复添加

    def on_item_collapsed(self, item):
        """当项目被折叠时移除展开状态记录"""
        path = item.data(0, Qt.UserRole)
        # 新增：折叠时移除展开状态记录（使用discard更安全）
        if self.suspend_expand_tracking:
            return
        self.expanded_paths.discard(path)

    def load_children(self, parent_item, path):
        """加载目录的子项"""
        try:
            # 先清空旧的子项，避免重复显示（文件更新或刷新后）
            try:
                while parent_item.childCount() > 0:
                    parent_item.takeChild(0)
            except Exception:
                pass
            # 获取目录内容并按类型排序（文件夹在前，文件在后）
            dirs = []
            files = []
            for f in os.listdir(path):
                full_path = os.path.join(path, f)
                # 跳过已移除的项目
                if full_path in self.main_window.removed_items:
                    continue
                if os.path.isdir(full_path):
                    dirs.append(f)
                else:
                    files.append(f)
            
            # 文件夹按名称排序
            dirs.sort(key=str.lower)
            
            # 文件按后缀排序，再按名称排序
            def get_file_sort_key(filename):
                name, ext = os.path.splitext(filename)
                return (ext.lower(), name.lower())
            
            files.sort(key=get_file_sort_key)
            
            # 先添加文件夹，再添加文件
            for f in dirs + files:
                child_path = os.path.join(path, f)
                child_item = QTreeWidgetItem([f])
                child_item.setData(0, Qt.UserRole, child_path)
                
                # 设置图标 - 使用Windows资源管理器图标
                if os.path.isdir(child_path):
                    # 使用系统文件夹图标
                    file_info = QFileInfo(child_path)
                    icon_provider = QFileIconProvider()
                    icon = icon_provider.icon(file_info)
                    child_item.setIcon(0, icon)
                    # 标记为可展开（即使还没有加载子项）
                    child_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
                else:
                    # 使用系统文件图标
                    file_info = QFileInfo(child_path)
                    icon_provider = QFileIconProvider()
                    icon = icon_provider.icon(file_info)
                    child_item.setIcon(0, icon)
                    # 文件没有子项
                    child_item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)
                
                parent_item.addChild(child_item)
                
                # 如果是已展开的目录，递归标记为已加载
                if os.path.isdir(child_path) and child_path in self.expanded_paths:
                    self.load_children(child_item, child_path)
                    self.loaded_dirs.add(child_path)
                    
        except Exception as e:
            if self.main_window:
                self.main_window.log(f"无法访问 {path}: {e}")

    # ---------------- 鼠标事件处理（修复选择问题） ----------------
    def mousePressEvent(self, event: QMouseEvent):
        """修复问题1：点击展开箭头不改变选择状态"""
        self.last_click_pos = event.pos()
        self.is_dragging = False
        self.scroll_direction = 0
        self.scroll_timer = None
        item = self.itemAt(event.pos())
        
        # 点击空白处：全不选
        if not item:
            self.clearSelection()
            if self.main_window:
                self.main_window.deselect_all_tree()
            super().mousePressEvent(event)
            return
        
        # 获取项的矩形区域
        item_rect = self.visualItemRect(item)
        # 计算展开/折叠箭头区域（左侧约20px）
        arrow_rect = QRect(item_rect.left(), item_rect.top(), 20, item_rect.height())
        
        # 判断点击位置
        is_click_arrow = arrow_rect.contains(event.pos())

        # 修复问题1：点击箭头只展开/折叠，不改变选择状态
        if is_click_arrow:
            # 展开/折叠操作，不改变选择状态
            item.setExpanded(not item.isExpanded())
            event.accept()
            return
        
        # 正常点击处理
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """处理框选移动并支持自动滚动"""
        if self.is_dragging:
            # 确保矩形坐标正确，始终保持矩形状态
            top_left = QPoint(min(self.last_click_pos.x(), event.pos().x()), 
                             min(self.last_click_pos.y(), event.pos().y()))
            bottom_right = QPoint(max(self.last_click_pos.x(), event.pos().x()), 
                                 max(self.last_click_pos.y(), event.pos().y()))
            self.select_rect.setTopLeft(top_left)
            self.select_rect.setBottomRight(bottom_right)
            
            # 检查是否需要自动滚动
            viewport = self.viewport()
            margin = 20  # 边缘触发滚动的距离
            y = event.pos().y()
            
            # 计算滚动方向和速度
            new_direction = 0
            if y < margin:
                new_direction = -1  # 向上滚动
            elif y > viewport.height() - margin:
                new_direction = 1   # 向下滚动
            
            # 启动或更新滚动定时器
            if new_direction != self.scroll_direction:
                self.scroll_direction = new_direction
                if self.scroll_timer:
                    self.scroll_timer.stop()
                
                if new_direction != 0:
                    self.scroll_timer = QTimer(self)
                    self.scroll_timer.timeout.connect(self.auto_scroll)
                    self.scroll_timer.start(50)  # 滚动间隔
                else:
                    self.scroll_timer = None
        
        super().mouseMoveEvent(event)

    def auto_scroll(self):
        """自动滚动并更新选择"""
        if self.scroll_direction == 0 or not self.is_dragging:
            if self.scroll_timer:
                self.scroll_timer.stop()
            return
        
        # 滚动一定像素
        scroll_step = 5
        current_scroll = self.verticalScrollBar().value()
        new_scroll = current_scroll + self.scroll_direction * scroll_step
        self.verticalScrollBar().setValue(new_scroll)
        
        # 更新选择
        self.update_dragging_selection()

    def update_dragging_selection(self):
        """更新拖拽过程中的选择"""
        if not self.is_dragging:
            return
        
        selected_items = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if self.is_item_in_rect(item, self.select_rect):
                selected_items.append(item)
            self.check_child_in_rect(item, self.select_rect, selected_items)
        
        # 更新选择状态
        for item in selected_items:
            item.setSelected(True)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """完成框选，选中区域内项（修复框选选择问题）"""
        # 停止自动滚动
        if self.scroll_timer:
            self.scroll_timer.stop()
            self.scroll_timer = None
        self.scroll_direction = 0
        
        if self.is_dragging and (event.pos() - self.last_click_pos).manhattanLength() > 5:
            self.is_dragging = False
            # 最后一次更新选择，确保所有项都被考虑
            self.update_dragging_selection()
        
        self.select_rect = QRect()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent):
        """移除框选矩形绘制"""
        super().paintEvent(event)
        # 不再绘制框选矩形

    def is_item_in_rect(self, item, rect):
        """判断项是否在框选区域内"""
        item_rect = self.visualItemRect(item)
        return rect.intersects(item_rect)

    def check_child_in_rect(self, parent_item, rect, selected_items):
        """递归检查子项是否在框选区域"""
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            if self.is_item_in_rect(child_item, rect):
                selected_items.append(child_item)
            self.check_child_in_rect(child_item, rect, selected_items)

    # ---------------- 右键菜单修复 ----------------
    def show_right_menu(self, pos):
        """显示右键菜单（添加新功能）"""
        try:
            if not self.main_window:
                return
            
            menu = QMenu()
            
            # 1. 展开/折叠相关功能
            expand_all_action = QAction("展开全部", self)
            expand_all_action.triggered.connect(lambda: self.main_window.expand_all(True))
            expand_all_action.setEnabled(self.topLevelItemCount() > 0)
            expand_all_action.setToolTip("展开所有目录")
            menu.addAction(expand_all_action)
            
            expand_sel_action = QAction("展开选定项", self)
            expand_sel_action.triggered.connect(lambda: self.main_window.expand_selected(True))
            expand_sel_action.setEnabled(len(self.selectedItems()) > 0)
            expand_sel_action.setToolTip("展开所有选中的目录")
            menu.addAction(expand_sel_action)
            
            collapse_all_action = QAction("关闭全部", self)
            collapse_all_action.triggered.connect(lambda: self.main_window.expand_all(False))
            collapse_all_action.setEnabled(self.topLevelItemCount() > 0)
            collapse_all_action.setToolTip("折叠所有目录")
            menu.addAction(collapse_all_action)
            
            collapse_sel_action = QAction("关闭选定项", self)
            collapse_sel_action.triggered.connect(lambda: self.main_window.expand_selected(False))
            collapse_sel_action.setEnabled(len(self.selectedItems()) > 0)
            collapse_sel_action.setToolTip("折叠所有选中的目录")
            menu.addAction(collapse_sel_action)
            
            # 添加关闭未选定项菜单项
            collapse_unsel_action = QAction("关闭未选定项", self)
            collapse_unsel_action.triggered.connect(self.main_window.collapse_unselected)
            collapse_unsel_action.setEnabled(self.topLevelItemCount() > 0)
            collapse_unsel_action.setToolTip("折叠所有未选中的目录")
            menu.addAction(collapse_unsel_action)
            
            menu.addSeparator()
            
            # 2. 选择相关功能
            select_all_action = QAction(f"全选 (Shift+A)", self)
            select_all_action.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_A))
            select_all_action.triggered.connect(self.main_window.select_all_tree)
            select_all_action.setEnabled(self.topLevelItemCount() > 0)
            select_all_action.setToolTip("选中所有项目 (Shift+A)")
            menu.addAction(select_all_action)
            
            deselect_all_action = QAction(f"全不选 (Alt+A)", self)
            deselect_all_action.setShortcut(QKeySequence(Qt.ALT + Qt.Key_A))
            deselect_all_action.triggered.connect(self.main_window.deselect_all_tree)
            deselect_all_action.setEnabled(len(self.selectedItems()) > 0)
            deselect_all_action.setToolTip("取消所有选中 (Alt+A)")
            menu.addAction(deselect_all_action)
            
            select_level_action = QAction(f"选择层级 (Shift+S)", self)
            select_level_action.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_S))
            select_level_action.triggered.connect(self.main_window.select_level)
            select_level_action.setEnabled(len(self.selectedItems()) > 0)
            select_level_action.setToolTip("选择所选文件夹内的所有内容 (Shift+S)")
            menu.addAction(select_level_action)
            
            menu.addSeparator()
            
            # 3. 反选相关功能
            invert_all_action = QAction(f"反选 (Alt+F)", self)
            invert_all_action.setShortcut(QKeySequence(Qt.ALT + Qt.Key_F))
            invert_all_action.triggered.connect(self.main_window.invert_all_selection)
            invert_all_action.setEnabled(self.topLevelItemCount() > 0)
            invert_all_action.setToolTip("反转所有项目的选择状态 (Alt+F)")
            menu.addAction(invert_all_action)
            
            invert_single_level_action = QAction(f"在选定项的层级中反选 (Ctrl+F)", self)
            invert_single_level_action.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_F))
            invert_single_level_action.triggered.connect(self.main_window.invert_single_level_selection)
            invert_single_level_action.setEnabled(len(self.selectedItems()) > 0)
            invert_single_level_action.setToolTip("在选定项的同级中反转选择状态 (Ctrl+F)")
            menu.addAction(invert_single_level_action)
            
            menu.addSeparator()
            
            # 4. 新增功能
            copy_path_action = QAction("复制绝对路径", self)
            copy_path_action.triggered.connect(self.main_window.copy_selected_path)
            copy_path_action.setEnabled(len(self.selectedItems()) > 0)
            copy_path_action.setToolTip("复制选中项的绝对路径到剪贴板")
            menu.addAction(copy_path_action)
            
            open_dir_action = QAction("打开所在目录", self)
            open_dir_action.triggered.connect(self.main_window.open_selected_dir)
            open_dir_action.setEnabled(len(self.selectedItems()) > 0)
            open_dir_action.setToolTip("在文件管理器中打开选中项所在的目录")
            menu.addAction(open_dir_action)
            
            rename_action = QAction("重命名", self)
            rename_action.triggered.connect(self.main_window.rename_selected_item)
            rename_action.setEnabled(len(self.selectedItems()) == 1)  # 只允许单个选中项重命名
            rename_action.setToolTip("重命名选中的文件或文件夹")
            menu.addAction(rename_action)
            
            menu.addSeparator()
            
            # 5. 其他功能
            refresh_action = QAction(f"刷新", self)
            refresh_action.triggered.connect(self.main_window.refresh_tree_preserve_state)
            refresh_action.setEnabled(self.topLevelItemCount() > 0)
            refresh_action.setToolTip(f"刷新目录树（保留搜索）")
            menu.addAction(refresh_action)

            reset_search_action = QAction("重置搜索", self)
            reset_search_action.triggered.connect(self.main_window.reset_search)
            reset_search_action.setToolTip("清空搜索并刷新目录树")
            menu.addAction(reset_search_action)
            
            clear_sel_action = QAction(f"清空选定项 (Shift+D)", self)
            clear_sel_action.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_D))
            clear_sel_action.triggered.connect(self.main_window.clear_selected_items)
            clear_sel_action.setEnabled(len(self.selectedItems()) > 0)
            clear_sel_action.setToolTip("从目录树中移除选定项 (Shift+D)")
            menu.addAction(clear_sel_action)
            
            menu.addSeparator()
            
            # 测试功能
            test_log_action = QAction("测试日志颜色", self)
            test_log_action.triggered.connect(self.main_window.test_log_colors)
            test_log_action.setToolTip("测试日志颜色功能")
            menu.addAction(test_log_action)
            
            menu.exec_(self.mapToGlobal(pos))
        except Exception as e:
            if self.main_window:
                self.main_window.log(f"右键菜单错误: {str(e)}", QColor(Qt.red))

    # ---------------- 展开/折叠状态保存与恢复 ----------------
    def save_expanded_state(self):
        """保存展开状态"""
        # 若暂停展开状态跟踪，则不更新集合，避免误清空
        if getattr(self, "suspend_expand_tracking", False):
            return
        self.expanded_paths.clear()
        def recurse(item):
            path = item.data(0, Qt.UserRole)
            if item.isExpanded():
                self.expanded_paths.add(path)
            for i in range(item.childCount()):
                recurse(item.child(i))
        for i in range(self.topLevelItemCount()):
            recurse(self.topLevelItem(i))

    def restore_expanded_state(self):
        """恢复展开状态"""
        def recurse(item):
            path = item.data(0, Qt.UserRole)
            if path in self.expanded_paths:
                item.setExpanded(True)
            for i in range(item.childCount()):
                recurse(item.child(i))
        for i in range(self.topLevelItemCount()):
            recurse(self.topLevelItem(i))


def safe_copy(src_path, dst_path, buffer_size=1024*1024):
    """安全复制函数（保留原逻辑）"""
    if not os.path.exists(src_path):
        return False, f"源文件不存在：{src_path}"
    
    dst_dir = os.path.dirname(dst_path)
    os.makedirs(dst_dir, exist_ok=True)
    
    temp_dst = f"{dst_path}.tmp"
    try:
        with open(src_path, 'rb') as src_file:
            with open(temp_dst, 'wb') as dst_file:
                while True:
                    buffer = src_file.read(buffer_size)
                    if not buffer:
                        break
                    dst_file.write(buffer)
        
        shutil.copystat(src_path, temp_dst)
        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(temp_dst, dst_path)
        
        return True, "复制成功"
    except PermissionError:
        if os.path.exists(temp_dst):
            os.remove(temp_dst)
        return False, "权限不足（文件可能被其他程序占用）"
    except Exception as e:
        if os.path.exists(temp_dst):
            os.remove(temp_dst)
        return False, f"复制失败：{str(e)}"


class FileReplacerApp(QMainWindow):
    """主窗口（修复所有交互问题）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.backup_dir = None
        self.original_tree_items = []  # 存储原始项的路径而非对象，避免引用问题
        self.removed_items = []  # 存储被手动移除的项，用于撤销操作
        self.file_watcher = QFileSystemWatcher()  # 自动刷新监控
        self.operation_history = []  # 操作历史，用于撤销功能
        self.search_block_parents = set()  # 搜索模式下屏蔽的父目录集合
        self.search_query = ""  # 保存当前搜索关键词
        self.search_type = ""  # 保存当前搜索类型
        self.init_shortcuts()  # 初始化快捷键
        self.init_ui()
        self.init_file_watcher()
        
        # 设置窗口居中
        # self.center_window()
        
        # 设置窗口图标 - 使用内嵌资源
        # self.init_window_icon()

    def init_window_icon(self):
        """初始化窗口图标，使用内嵌资源"""
        try:
            # 从内嵌资源加载图标
            self.setWindowIcon(QIcon(":/icon.ico"))
            self.log("窗口图标加载成功（内嵌资源）")
        except Exception as e:
            # 加载失败时使用系统默认图标
            self.log(f"警告：窗口图标加载失败 - {str(e)}", QColor(Qt.yellow))
            self.setWindowIcon(self.style().standardIcon(QStyle.SP_FileIcon))

    def center_window(self):
        """将窗口居中显示"""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 2), int((screen.height() - size.height()) / 2))

    def init_shortcuts(self):
        """初始化快捷键（固定快捷键，不提供自定义功能）"""
        # 定义固定快捷键 - 移除刷新快捷键
        self.shortcuts = {
            'select_all': ("全选", QKeySequence(Qt.SHIFT + Qt.Key_A)),
            'deselect_all': ("全不选", QKeySequence(Qt.ALT + Qt.Key_A)),
            'invert_all': ("反选", QKeySequence(Qt.ALT + Qt.Key_F)),
            'invert_single_level': ("层级反选", QKeySequence(Qt.CTRL + Qt.Key_F)),
            'undo_action': ("撤销", QKeySequence(Qt.CTRL + Qt.Key_Z)),
            'clear_selected': ("清空选定项", QKeySequence(Qt.SHIFT + Qt.Key_D)),
            'select_level': ("选择层级", QKeySequence(Qt.SHIFT + Qt.Key_S)),
        }
        
        # 创建快捷键动作
        self.shortcut_actions = {}
        for action_name in self.shortcuts.keys():
            action = QAction(self)
            action.setShortcut(self.shortcuts[action_name][1])
            action.setShortcutContext(Qt.ApplicationShortcut)
            self.shortcut_actions[action_name] = action
        
        # 连接快捷键到功能
        self.shortcut_actions['select_all'].triggered.connect(self.select_all_tree)
        self.shortcut_actions['deselect_all'].triggered.connect(self.deselect_all_tree)
        self.shortcut_actions['invert_all'].triggered.connect(self.invert_all_selection)
        self.shortcut_actions['invert_single_level'].triggered.connect(self.invert_single_level_selection)
        self.shortcut_actions['undo_action'].triggered.connect(self.undo_last_action)
        self.shortcut_actions['clear_selected'].triggered.connect(self.clear_selected_items)
        self.shortcut_actions['select_level'].triggered.connect(self.select_level)
        
        # 添加到窗口
        for action in self.shortcut_actions.values():
            self.addAction(action)

    def get_shortcut(self, action_name):
        """获取指定动作的快捷键"""
        if action_name in self.shortcuts:
            return self.shortcuts[action_name][1]
        return QKeySequence()

    def get_shortcut_text(self, action_name):
        """获取指定动作的快捷键文本表示"""
        seq = self.get_shortcut(action_name)
        if seq.isEmpty():
            return ""
        # 直接使用系统格式化文本即可
        return seq.toString()

    def check_shortcut(self, event, action_name):
        """检查事件是否匹配指定的快捷键"""
        if action_name not in self.shortcuts:
            return False
            
        target_seq = self.shortcuts[action_name][1]
        if target_seq.isEmpty():
            return False
            
        # 创建当前事件的快捷键序列
        modifiers = event.modifiers()
        key = event.key()
        
        # 忽略修饰键本身
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return False
            
        current_seq = QKeySequence(modifiers | key)
        return current_seq.matches(target_seq) == QKeySequence.ExactMatch

    def init_ui(self):
        self.setWindowTitle("Ash-MOD-Tool-v0.1测试版")
        self.setGeometry(100, 100, 1000, 640)

        main_widget = QWidget()
        self.main_layout = QVBoxLayout(main_widget)
        main_widget.setLayout(self.main_layout)
        self.setCentralWidget(main_widget)

        # 主分割线
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: white; }")
        self.main_layout.addWidget(self.main_splitter)

        # 上半部分容器
        upper_container = QWidget()
        upper_layout = QVBoxLayout(upper_container)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_container.setMinimumHeight(200)
        
        # 左右水平分割（保持各50%宽度）
        splitter_main = QSplitter(Qt.Horizontal)
        splitter_main.setHandleWidth(6)
        splitter_main.setChildrenCollapsible(False)
        splitter_main.setOpaqueResize(True)
        splitter_main.setStyleSheet("QSplitter::handle { background-color: white; }")

        # 左控件布局（保留原逻辑）
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(200)

        # 源文件组
        source_group = QGroupBox("源文件")
        source_group.setToolTip("用于替换其他文件的源文件")
        source_layout = QHBoxLayout()
        source_layout.setContentsMargins(10, 10, 10, 10)
        source_group.setLayout(source_layout)
        self.source_edit = DraggableLineEdit()
        self.source_edit.setPlaceholderText("选择要用于替换的源文件")
        btn_src_select = QPushButton("选择")
        btn_src_select.clicked.connect(self.browse_source)
        btn_src_select.setToolTip("浏览并选择源文件")
        btn_src_clear = QPushButton("清空")
        btn_src_clear.clicked.connect(lambda: self.source_edit.clear())
        btn_src_clear.setToolTip("清空当前源文件路径")
        source_layout.addWidget(self.source_edit)
        source_layout.addWidget(btn_src_select)
        source_layout.addWidget(btn_src_clear)
        left_layout.addWidget(source_group, 1)

        # 匹配模式组
        match_group = QGroupBox("匹配模式")
        match_group.setToolTip("设置文件匹配的方式")
        match_layout = QHBoxLayout()
        match_layout.setContentsMargins(10, 10, 10, 10)
        match_group.setLayout(match_layout)
        self.match_combo = QComboBox()
        self.match_combo.addItems(["后缀匹配", "关键词匹配", "正则表达式"])
        self.match_combo.setToolTip("""
        后缀匹配：根据文件后缀名进行匹配
        关键词匹配：根据文件名包含的关键词进行匹配
        正则表达式：使用正则表达式进行复杂匹配
        """)
        self.match_edit = ShortcutLineEdit()
        self.match_edit.setPlaceholderText("后缀示例: .10 或 10；关键词示例: mdf；正则示例: ^pl0100.*")
        self.match_edit.setToolTip("""
        后缀匹配示例：.txt 或 txt（匹配所有txt文件）
        关键词匹配示例：report（匹配所有文件名包含report的文件）
        正则表达式示例：^file_\d{3}\.pdf$（匹配file_001.pdf、file_123.pdf等格式的文件）
        正则表达式语法：
        . 匹配任意单个字符
        * 匹配前面的字符零次或多次
        + 匹配前面的字符一次或多次
        ? 匹配前面的字符零次或一次
        ^ 匹配字符串的开始
        $ 匹配字符串的结束
        [] 匹配括号内的任意一个字符
        () 分组匹配
        \d 匹配任意数字
        \w 匹配任意字母、数字或下划线
        """)
        match_layout.addWidget(QLabel("模式:"))
        match_layout.addWidget(self.match_combo)
        match_layout.addWidget(self.match_edit)
        left_layout.addWidget(match_group, 1)

        # 跳过关键词组
        skip_group = QGroupBox("跳过关键词")
        skip_group.setToolTip("设置需要跳过的文件关键词")
        skip_layout = QHBoxLayout()
        skip_layout.setContentsMargins(10, 10, 10, 10)
        skip_group.setLayout(skip_layout)
        self.skip_edit = ShortcutLineEdit()
        self.skip_edit.setPlaceholderText("逗号分隔关键词（中英文逗号均可），例如：tmp, test，临时")
        self.skip_edit.setToolTip("输入需要跳过的关键词，多个关键词用逗号分隔，文件名包含任意关键词的文件将被跳过")
        skip_layout.addWidget(QLabel("跳过关键词:"))
        skip_layout.addWidget(self.skip_edit)
        left_layout.addWidget(skip_group, 1)

        # 备份目录组
        backup_group = QGroupBox("备份目录 (可选)")
        backup_group.setToolTip("设置文件替换前的备份目录")
        # 改为两行布局：第一行放已有备份下拉框；第二行放启用/输入框/按钮
        backup_layout = QVBoxLayout()
        backup_layout.setContentsMargins(10, 10, 10, 10)
        backup_group.setLayout(backup_layout)
        
        self.backup_enable = QCheckBox("启用备份")
        self.backup_enable.setChecked(True)
        self.backup_enable.stateChanged.connect(self.update_backup_controls)
        self.backup_enable.setToolTip("勾选则在替换文件前创建备份，以便需要时还原")
        
        self.backup_edit = DraggableLineEdit()
        self.backup_edit.setPlaceholderText("不填则自动在目标目录创建 backup-年-月-日-时-分")
        self.backup_edit.setToolTip("指定备份文件的保存目录，不填则自动创建")
        # 文本变化时更新备份相关控件的启用状态
        try:
            self.backup_edit.textChanged.connect(self.update_backup_controls)
        except Exception:
            pass
        self.btn_backup_select = QPushButton("选择")
        self.btn_backup_select.clicked.connect(self.browse_backup)
        self.btn_backup_select.setToolTip("浏览并选择备份目录")
        self.btn_backup_clear = QPushButton("清空")
        self.btn_backup_clear.clicked.connect(lambda: self.backup_edit.clear())
        self.btn_backup_clear.setToolTip("清空当前备份目录路径")

        # 新增：已有的备份下拉框（与输入框同宽，置于上一行）
        row_existing = QHBoxLayout()
        self.backup_existing_combo = QComboBox()
        self.backup_existing_combo.setToolTip("从已有备份中选择，用于还原")
        self.backup_existing_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.backup_existing_combo.currentIndexChanged.connect(self.on_existing_backup_selected)
        # 当仅有一个条目时，activated 才能保证点击也能触发填充
        self.backup_existing_combo.activated.connect(self.on_existing_backup_activated)
        # 抑制在程序性添加下拉项时自动填充输入框
        self.suppress_backup_selection = False
        row_existing.addWidget(QLabel("已有的备份:"))
        row_existing.addWidget(self.backup_existing_combo)

        row_inputs = QHBoxLayout()
        self.backup_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_inputs.addWidget(self.backup_enable)
        row_inputs.addWidget(self.backup_edit)
        row_inputs.addWidget(self.btn_backup_select)
        row_inputs.addWidget(self.btn_backup_clear)

        backup_layout.addLayout(row_existing)
        backup_layout.addLayout(row_inputs)
        left_layout.addWidget(backup_group, 1)

        left_layout.setStretch(0, 1)
        left_layout.setStretch(1, 1)
        left_layout.setStretch(2, 1)
        left_layout.setStretch(3, 1)

        splitter_main.addWidget(left_widget)

        # 右控件 目标目录（修复搜索功能）
        right_group = QGroupBox("目标目录")
        right_group.setToolTip("需要进行文件替换的目标目录和文件")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)  # 设置为0以最小化间距
        right_group.setLayout(right_layout)
        right_group.setMinimumWidth(200)

        # 第一行：选择目录、清空目录、刷新按钮（并列）
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 5, 10, 0)  # 减少上下间距
        btn_layout.setSpacing(5)
        
        self.btn_tree_select = QPushButton("选择目录")
        self.btn_tree_select.clicked.connect(self.browse_target)
        self.btn_tree_select.setToolTip("选择要添加到目标列表的目录")
        
        self.btn_tree_clear = QPushButton("清空目录")
        self.btn_tree_clear.clicked.connect(self.clear_tree)
        self.btn_tree_clear.setToolTip("清空当前所有目标目录和文件")
        
        self.btn_tree_refresh = QPushButton("刷新")
        # 移除刷新快捷键绑定
        self.btn_tree_refresh.clicked.connect(self.refresh_tree_preserve_state)
        self.btn_tree_refresh.setToolTip(f"刷新目录树（保留搜索）")
        btn_layout.addWidget(self.btn_tree_select)
        btn_layout.addWidget(self.btn_tree_clear)
        btn_layout.addWidget(self.btn_tree_refresh)
        right_layout.addLayout(btn_layout)

        # 第二行：搜索（下拉框+输入框+按钮）
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(10, 5, 10, 0)  # 减少上下间距
        search_layout.setSpacing(5)
        
        self.search_type_combo = QComboBox()
        # 只保留"搜文件夹"和"搜文件"两个选项
        self.search_type_combo.addItems(["搜文件夹", "搜文件"])
        self.search_type_combo.setMinimumContentsLength(8)
        self.search_type_combo.setToolTip("选择搜索类型：文件夹或文件")
        
        self.tree_search = ShortcutLineEdit()
        self.tree_search.setPlaceholderText("输入关键词搜索")
        self.tree_search.setToolTip("输入关键词搜索文件或文件夹，支持部分匹配")
        # 添加回车键触发搜索
        self.tree_search.returnPressed.connect(self.on_search_clicked)
        
        self.btn_search = QPushButton("搜索")
        self.btn_search.clicked.connect(self.on_search_clicked)
        self.btn_search.setToolTip("根据关键词搜索文件或文件夹")
        self.btn_search.setFixedWidth(60)

        self.btn_reset_search = QPushButton("重置")
        self.btn_reset_search.clicked.connect(self.reset_search)
        self.btn_reset_search.setToolTip("清空搜索并刷新目录树")
        self.btn_reset_search.setFixedWidth(60)
        
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_type_combo)
        search_layout.addWidget(self.tree_search)
        search_layout.addWidget(self.btn_search)
        search_layout.addWidget(self.btn_reset_search)
        right_layout.addLayout(search_layout)

        # 移除已选目标的文字提示，直接添加树状图
        # 树状图（增强版）
        self.target_tree = DraggableTreeWidget()
        self.target_tree.set_main_window(self)
        # 横向滚动条优化：禁用列宽自适应，增加初始宽度
        self.target_tree.header().setStretchLastSection(False)
        self.target_tree.setColumnWidth(0, 800)  # 进一步增加初始列宽
        self.target_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 连接选择变化信号，用于更新统计信息
        self.target_tree.itemSelectionChanged.connect(self.update_selection_stats)
        right_layout.addWidget(self.target_tree)

        splitter_main.addWidget(right_group)
        splitter_main.setSizes([500, 500])
        splitter_main.setStretchFactor(0, 1)
        splitter_main.setStretchFactor(1, 1)

        # 操作按钮和进度条区域（保留原逻辑）
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(3)
        controls_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 操作按钮
        ops_widget = QWidget()
        ops_layout = QHBoxLayout(ops_widget)
        ops_layout.setContentsMargins(0, 0, 0, 0)
        ops_layout.setSpacing(5)
        self.btn_preview = QPushButton("预览匹配文件")
        self.btn_preview.clicked.connect(self.on_preview)
        self.btn_preview.setToolTip("预览所有匹配条件的文件，不执行实际替换")
        self.btn_replace = QPushButton("开始替换")
        self.btn_replace.clicked.connect(self.on_replace)
        self.btn_replace.setToolTip("开始替换所有匹配条件的文件")
        self.btn_restore_selected = QPushButton("还原选中")
        self.btn_restore_selected.clicked.connect(self.on_restore_selected)
        self.btn_restore_selected.setEnabled(False)
        self.btn_restore_selected.setToolTip("还原输入的备份或左侧选中的对应文件")

        self.btn_restore_all = QPushButton("还原所有文件")
        self.btn_restore_all.clicked.connect(self.on_restore_all)
        self.btn_restore_all.setEnabled(False)
        self.btn_restore_all.setToolTip("从已有的备份列表中还原所有文件")

        self.btn_clear_selected = QPushButton("清除选中备份")
        self.btn_clear_selected.clicked.connect(self.on_clear_selected_backup)
        self.btn_clear_selected.setEnabled(False)
        self.btn_clear_selected.setToolTip("仅清除输入框中填入的备份（文件或文件夹）")

        self.btn_clear_all = QPushButton("清除所有备份")
        self.btn_clear_all.clicked.connect(self.on_clear_all_backups)
        self.btn_clear_all.setEnabled(False)
        self.btn_clear_all.setToolTip("清除已有的备份下拉框中的所有备份")
        
        ops_layout.addWidget(self.btn_preview)
        ops_layout.addWidget(self.btn_replace)
        ops_layout.addWidget(self.btn_restore_selected)
        ops_layout.addWidget(self.btn_restore_all)
        ops_layout.addWidget(self.btn_clear_selected)
        ops_layout.addWidget(self.btn_clear_all)
        
        # 进度条
        prog_widget = QWidget()
        prog_layout = QHBoxLayout(prog_widget)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_label_left = QLabel("替换进度：")
        self.progress_label_left.setToolTip("显示当前操作的进度")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setToolTip("进度条显示当前操作的完成百分比")
        self.progress_label_right = QLabel("准备就绪")
        self.progress_label_right.setToolTip("显示当前操作的状态")
        prog_layout.addWidget(self.progress_label_left)
        prog_layout.addWidget(self.progress_bar)
        prog_layout.addWidget(self.progress_label_right)
        
        controls_layout.addWidget(ops_widget)
        controls_layout.addWidget(prog_widget)

        upper_layout.addWidget(splitter_main, 1)
        upper_layout.addWidget(controls_widget, 0)
        upper_layout.setSpacing(5)

        self.main_splitter.addWidget(upper_container)

        # 下半部分容器（保留原逻辑）
        lower_splitter = QSplitter(Qt.Vertical)
        lower_splitter.setHandleWidth(6)
        lower_splitter.setChildrenCollapsible(False)
        lower_splitter.setOpaqueResize(True)
        lower_splitter.setMinimumHeight(250)
        lower_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 文件列表
        result_group = QGroupBox("文件列表")
        result_group.setToolTip("显示匹配的文件列表或操作结果")
        result_group.setStyleSheet("QGroupBox { padding-top: 2px; }")
        result_group.setMinimumHeight(120)
        result_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(5, 0, 5, 5)
        result_layout.setSpacing(2)
        
        self.preview_header = QLabel("")
        self.preview_header.setStyleSheet("font-weight: bold; margin: 0px; padding: 0px;")
        self.preview_header.setAlignment(Qt.AlignCenter)
        self.preview_header.setContentsMargins(0, 0, 0, 0)
        self.preview_header.setToolTip("显示文件列表统计信息")
        
        self.result_list = EnhancedTextEdit(is_log=False)
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        result_layout.addWidget(self.preview_header, 0)
        result_layout.addWidget(self.result_list, 1)
        lower_splitter.addWidget(result_group)

        # 日志
        log_group = QGroupBox("操作日志")
        log_group.setToolTip("显示所有操作的详细日志信息")
        log_group.setMinimumHeight(120)
        log_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 2, 5, 5)
        
        self.log_list = EnhancedTextEdit(is_log=True)
        self.log_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout.addWidget(self.log_list, 1)
        lower_splitter.addWidget(log_group)
        
        lower_splitter.setStretchFactor(0, 1)
        lower_splitter.setStretchFactor(1, 1)
        lower_splitter.setSizes([125, 125])

        self.main_splitter.addWidget(lower_splitter)

        # 主分割线初始比例
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([384, 256])

        # 初始化
        self.thread = None
        self.update_backup_controls()

    def init_file_watcher(self):
        """初始化文件监控（自动刷新）"""
        self.file_watcher.directoryChanged.connect(self.on_dir_changed)
        self.file_watcher.fileChanged.connect(self.on_file_changed)
        # 增加监控超时，避免频繁刷新
        self.last_refresh_time = 0
        self.refresh_delay = 1000  # 1秒延迟

    def on_dir_changed(self, path):
        """目录变化时自动刷新（增加延迟）"""
        current_time = time.time() * 1000  # 毫秒
        if current_time - self.last_refresh_time > self.refresh_delay:
            self.last_refresh_time = current_time
            self.log(f"检测到目录变化：{path}，自动刷新")
            # 保留搜索与展开状态
            self.refresh_tree_preserve_state()
            # 取消搜索模式下的自动展开，避免干扰用户视图
            self.update_watcher()

    def on_file_changed(self, path):
        """文件变化时自动刷新（增加延迟）"""
        current_time = time.time() * 1000  # 毫秒
        if current_time - self.last_refresh_time > self.refresh_delay:
            self.last_refresh_time = current_time
            self.log(f"检测到文件变化：{path}，自动刷新")
            # 保留搜索与展开状态
            self.refresh_tree_preserve_state()
            # 取消搜索模式下的自动展开，避免干扰用户视图
            self.update_watcher()

    def update_watcher(self):
        """更新监控列表（顶层目录、已展开/已加载目录、搜索结果顶层文件的父目录，及搜索模式祖先目录）"""
        try:
            # 清空现有监控
            try:
                self.file_watcher.removePaths(self.file_watcher.directories())
            except Exception:
                pass
            try:
                self.file_watcher.removePaths(self.file_watcher.files())
            except Exception:
                pass

            monitored_dirs = set()

            # 顶层节点（无论是否为搜索结果视图）
            for i in range(self.target_tree.topLevelItemCount()):
                item = self.target_tree.topLevelItem(i)
                p = item.data(0, Qt.UserRole)
                if not p:
                    continue
                if os.path.isdir(p):
                    monitored_dirs.add(os.path.normpath(p))
                else:
                    # 文件：监控它的父目录，捕捉文件重命名/创建/删除事件
                    parent = os.path.dirname(p)
                    if parent and os.path.isdir(parent):
                        monitored_dirs.add(os.path.normpath(parent))

            # 已展开和已加载的目录
            for p in list(self.target_tree.expanded_paths) + list(self.target_tree.loaded_dirs):
                if p and os.path.isdir(p):
                    monitored_dirs.add(os.path.normpath(p))

            # 搜索模式下：补充监控所有祖先目录直到顶层原始目录
            if self.search_query:
                root_set = set(os.path.normpath(r) for r in self.original_tree_items)
                extra_ancestors = set()
                for i in range(self.target_tree.topLevelItemCount()):
                    item = self.target_tree.topLevelItem(i)
                    p = item.data(0, Qt.UserRole)
                    if not p:
                        continue
                    # 从父目录开始向上（文件取父目录，目录取自身）
                    cur = os.path.normpath(os.path.dirname(p)) if os.path.isfile(p) else os.path.normpath(p)
                    while cur:
                        if cur in extra_ancestors:
                            break
                        extra_ancestors.add(cur)
                        if cur in root_set:
                            break
                        new_cur = os.path.dirname(cur)
                        if new_cur == cur or not new_cur:
                            break
                        cur = new_cur
                monitored_dirs.update(extra_ancestors)

            # 添加目录到监控（不监控文件，降低抖动）
            for d in monitored_dirs:
                try:
                    self.file_watcher.addPath(d)
                except Exception as e:
                    self.log(f"添加监控失败: {d}, 错误: {str(e)}")
        except Exception as e:
            self.log(f"更新监控列表失败: {str(e)}", QColor(Qt.red))

    # ------------------ 树状图核心功能 ------------------
    def load_tree_lazy(self, path, parent_item=None):
        """懒加载树状图：只加载当前层级，不加载子目录"""
        # 如果路径在已移除列表中，则不加载
        if path in self.removed_items:
            return
            
        try:
            # 检查是否已存在相同路径的项（修复问题1：防止重复）
            exists = False
            def check_existing(item):
                nonlocal exists
                if item.data(0, Qt.UserRole) == path:
                    exists = True
                    return
                for i in range(item.childCount()):
                    check_existing(item.child(i))
                    if exists:
                        return
            
            if parent_item is None:
                for i in range(self.target_tree.topLevelItemCount()):
                    check_existing(self.target_tree.topLevelItem(i))
                    if exists:
                        return
            else:
                check_existing(parent_item)
                if exists:
                    return
            
            item = QTreeWidgetItem([os.path.basename(path)])
            item.setData(0, Qt.UserRole, path)
            
            # 顶层项图标（使用icon.ico），子项默认图标
            if parent_item is None:
                # 使用资源文件中的icon.ico作为顶层项图标
                icon = QIcon(":/icon.ico")
                item.setIcon(0, icon)
            else:
                # 使用Windows资源管理器图标
                file_info = QFileInfo(path)
                icon_provider = QFileIconProvider()
                icon = icon_provider.icon(file_info)
                item.setIcon(0, icon)
            
            # 如果是目录，设置为可展开（但不立即加载子项）
            if os.path.isdir(path):
                item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            else:
                item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)
            
            if parent_item is None:
                self.target_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            
            # 记录顶层项路径而非对象
            if parent_item is None and path not in self.original_tree_items:
                self.original_tree_items.append(path)
                
            # 如果是搜索结果中的目录且之前已展开，则立即加载子项
            if parent_item is not None and os.path.isdir(path) and path in self.target_tree.expanded_paths:
                self.target_tree.load_children(item, path)
                self.target_tree.loaded_dirs.add(path)
                
        except Exception as e:
            self.log(f"加载路径失败: {path}, 错误: {str(e)}", QColor(Qt.red))

    def refresh_tree_legacy(self):
        """旧版刷新方法：委托到最终版 refresh_tree，避免重复定义导致混淆"""
        return self.refresh_tree()

    def clear_tree(self):
        """清空树状图"""
        # 保存当前状态用于撤销
        current_state = {
            'type': 'clear_tree',
            'original_items': self.original_tree_items.copy(),
            'removed_items': self.removed_items.copy(),
            'search_state': {
                'query': self.search_query,
                'type': self.search_type
            }
        }
        self.operation_history.append(current_state)
        
        self.target_tree.clear()
        # 清空已加载目录记录
        self.target_tree.loaded_dirs.clear()
        # 将所有原始项添加到已移除列表
        self.removed_items.extend(self.original_tree_items)
        self.original_tree_items.clear()
        self.target_tree.expanded_paths.clear()
        self.file_watcher.removePaths(self.file_watcher.directories())
        self.file_watcher.removePaths(self.file_watcher.files())
        self.log("已清空目标目录树")

    def on_search_clicked(self):
        """修复搜索功能，搜文件/文件夹模式只显示包含关键词的目标和其子级，不显示父节点，实现懒加载"""
        try:
            search_text = self.tree_search.text().strip().lower()
            search_type = self.search_type_combo.currentText()
            
            # 保存搜索状态
            self.search_query = search_text
            self.search_type = search_type
            
            # 清空当前树和已加载目录记录
            self.target_tree.clear()
            self.target_tree.loaded_dirs.clear()
            
            if not search_text:
                # 空搜索时加载所有原始项（懒加载）
                for path in self.original_tree_items:
                    if path not in self.removed_items:
                        self.load_tree_lazy(path)
                return
            
            # 定义文件排序函数
            def get_file_sort_key(filename):
                name, ext = os.path.splitext(filename)
                return (ext.lower(), name.lower())
            
            # 按类型过滤搜索
            def match_item(path):
                """判断路径是否符合搜索条件"""
                name = os.path.basename(path).lower()
                if search_text not in name:
                    return False
                # 按类型过滤
                if search_type == "搜文件夹":
                    return os.path.isdir(path)
                elif search_type == "搜文件":
                    return os.path.isfile(path)
                return False  # 其他情况不匹配
            
            # 收集所有匹配的目标路径
            matched_targets = []
            
            # 递归搜索所有匹配的目标
            def search_targets(path):
                if path in self.removed_items or not os.path.exists(path):
                    return
                    
                if os.path.isfile(path):
                    if search_type == "搜文件" and match_item(path):
                        matched_targets.append(path)
                elif os.path.isdir(path):
                    # 如果是文件夹且匹配搜索条件
                    if search_type == "搜文件夹" and match_item(path):
                        matched_targets.append(path)
                    
                    # 递归搜索子项（无论是否匹配，都继续搜索子级）
                    try:
                        for f in os.listdir(path):
                            child_path = os.path.join(path, f)
                            search_targets(child_path)
                    except Exception as e:
                        self.log(f"访问目录失败: {path}, 错误: {str(e)}")
            
            # 开始搜索所有顶层目录
            for path in self.original_tree_items:
                if path not in self.removed_items and os.path.exists(path):
                    search_targets(path)
            
            # 处理搜索结果
            if not matched_targets:
                self.log(f"未找到包含 '{search_text}' 的{search_type}")
                # 末尾：更新监控，让搜索结果中的顶层节点（目录/文件父目录）进入监控集合
                self.update_watcher()
                return
            
            # 为每个匹配项创建节点（不显示父节点）
            for path in matched_targets:
                # 额外过滤：跳过已被移除的路径，避免在外部重命名后又被加入
                if path in self.removed_items:
                    continue
                # 搜索模式屏蔽：若其父目录在屏蔽集合中，则跳过
                parent_dir = os.path.dirname(path)
                if parent_dir in self.search_block_parents:
                    continue
                # 创建当前匹配项作为顶层节点
                item = QTreeWidgetItem([os.path.basename(path)])
                item.setData(0, Qt.UserRole, path)
                
                # 设置图标和子项指示器（使用系统真实图标，与非搜索状态一致）
                file_info = QFileInfo(path)
                icon_provider = QFileIconProvider()
                icon = icon_provider.icon(file_info)
                item.setIcon(0, icon)
                if os.path.isdir(path):
                    item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)  # 显示展开指示器
                else:
                    item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)  # 不显示展开指示器
                
                self.target_tree.addTopLevelItem(item)
                
                # 如果是已展开的目录，加载其所有子级
                if os.path.isdir(path) and path in self.target_tree.expanded_paths:
                    self.target_tree.load_children(item, path)
                    self.target_tree.loaded_dirs.add(path)
            
            # 显示结果统计
            self.log(f"找到 {len(matched_targets)} 个包含 '{search_text}' 的{search_type}")
            # 末尾：更新监控，让搜索结果中的顶层节点（目录/文件父目录）进入监控集合
            self.update_watcher()
        except Exception as e:
            self.log(f"搜索失败: {str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "搜索错误", f"搜索过程中发生错误: {str(e)}")

    def apply_search_filter(self):
        """应用搜索过滤，用于刷新后恢复搜索状态"""
        if not self.search_query:
            return
            
        # 保存当前展开状态
        self.target_tree.save_expanded_state()
        
        # 重新执行搜索
        self.on_search_clicked()
        
        # 恢复展开状态
        self.target_tree.restore_expanded_state()

    def update_selection_stats(self):
        """更新已选目标的统计信息（内部使用，不显示在界面上）"""
        selected_items = self.target_tree.selectedItems()
        dir_count = 0
        file_count = 0
        
        for item in selected_items:
            path = item.data(0, Qt.UserRole)
            if os.path.isdir(path):
                dir_count += 1
            else:
                file_count += 1

    # ------------------ 选择相关功能 ------------------
    def get_selected_files(self):
        """获取所有选中的文件（替换原来的勾选功能）"""
        files = []
        selected_items = self.target_tree.selectedItems()
        for item in selected_items:
            path = item.data(0, Qt.UserRole)
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                # 如果是目录，递归添加所有文件
                for root, _, dir_files in os.walk(path):
                    for f in dir_files:
                        file_path = os.path.join(root, f)
                        # 跳过已手动移除的项
                        if file_path not in self.removed_items:
                            files.append(file_path)
        # 去重处理，解决匹配文件数量异常问题
        return list(set(files))

    def select_all_tree(self):
        """全选（选中所有项）"""
        self.target_tree.selectAll()
        self.log("已全选所有项")

    def deselect_all_tree(self):
        """全不选（取消所有选中）"""
        self.target_tree.clearSelection()
        self.log("已取消所有选中")

    def invert_all_selection(self):
        """反选（所有项选择状态翻转）"""
        all_items = []
        def recurse(item):
            all_items.append(item)
            for i in range(item.childCount()):
                recurse(item.child(i))
        
        for i in range(self.target_tree.topLevelItemCount()):
            recurse(self.target_tree.topLevelItem(i))
        
        for item in all_items:
            item.setSelected(not item.isSelected())
        
        self.log("已反选所有项")

    def select_level(self):
        """选择层级：选择所选文件夹内的所有内容"""
        selected_items = self.target_tree.selectedItems()
        if not selected_items:
            return
        
        # 先取消当前选择
        self.target_tree.clearSelection()
        
        # 选择每个文件夹中的所有内容
        for item in selected_items:
            path = item.data(0, Qt.UserRole)
            if os.path.isdir(path):
                # 递归选择所有子项
                def select_children(parent_item):
                    parent_item.setSelected(True)
                    for i in range(parent_item.childCount()):
                        child = parent_item.child(i)
                        child.setSelected(True)
                        select_children(child)
                
                select_children(item)
            else:
                # 如果是文件，只选择自己
                item.setSelected(True)
        
        self.log(f"已选择 {len(selected_items)} 个项目的所有层级内容")

    def invert_single_level_selection(self):
        """在选定项的层级中反选（重命名，原单层级反选）"""
        selected_items = self.target_tree.selectedItems()
        if not selected_items:
            return
        
        # 对于每个选中的项目，找到其父节点，然后反选该父节点下的所有同级项目
        processed_parents = set()
        
        for item in selected_items:
            parent = item.parent()
            if not parent:  # 如果是顶级项目
                parent = self.target_tree.invisibleRootItem()
            
            # 使用父节点路径作为唯一标识
            parent_path = parent.data(0, Qt.UserRole) if parent != self.target_tree.invisibleRootItem() else "root"
            
            if parent_path in processed_parents:
                continue
            
            processed_parents.add(parent_path)
            
            # 获取父节点下的所有子项
            children = []
            for i in range(parent.childCount()):
                children.append(parent.child(i))
            
            # 反选这些子项
            for child in children:
                child.setSelected(not child.isSelected())
        
        self.log(f"已在选定项的层级中反选")

    def clear_selected_items(self):
        """清空选定项（修复问题2和问题4，并修复搜索状态下清除选定项导致文件夹关闭的问题）"""
        try:
            selected_items = self.target_tree.selectedItems()
            if not selected_items:
                return
            
            # 收集所有选中项的路径
            selected_paths = [item.data(0, Qt.UserRole) for item in selected_items]
            
            # 先保存当前展开状态，再写入撤销历史
            self.target_tree.save_expanded_state()
            
            # 保存当前状态用于撤销，包括搜索状态和展开状态
            current_state = {
                'type': 'clear_selected',
                'removed_paths': selected_paths.copy(),
                'search_state': {
                    'query': self.search_query,
                    'type': self.search_type
                },
                'expanded_paths': self.target_tree.expanded_paths.copy(),
                'original_items': self.original_tree_items.copy(),
                'removed_items': self.removed_items.copy()
            }
            self.operation_history.append(current_state)
            
            # 递归检查父项是否在选中列表中
            def has_selected_parent(path):
                parent_path = os.path.dirname(path)
                if parent_path == path:  # 到达根目录
                    return False
                return parent_path in selected_paths or has_selected_parent(parent_path)
            
            # 过滤掉那些有父项已被选中的项（避免重复删除）
            filtered_paths = []
            for path in selected_paths:
                if not has_selected_parent(path):
                    filtered_paths.append(path)
            
            # 从原始项列表中移除顶级项
            for path in filtered_paths[:]:
                if path in self.original_tree_items:
                    self.original_tree_items.remove(path)
                    filtered_paths.remove(path)
            
            # 添加到已移除列表
            self.removed_items.extend(selected_paths)

            # 搜索模式下：屏蔽这些选中项的父目录，防止改名后重新回到结果
            if self.search_query:
                for sp in selected_paths:
                    parent = os.path.dirname(sp)
                    if parent:
                        self.search_block_parents.add(os.path.normpath(parent))
            
            # 修复搜索状态下清除选定项导致文件夹关闭的问题
            # 直接移除选中项，而不是刷新整个树
            if self.search_query:
                # 在搜索状态下，直接移除选中项
                def remove_selected_items():
                    # 保存当前展开状态
                    self.target_tree.save_expanded_state()
                    
                    # 递归移除选中项
                    def remove_item_recursive(item):
                        path = item.data(0, Qt.UserRole)
                        if path in selected_paths:
                            parent = item.parent()
                            if parent:
                                parent.removeChild(item)
                            else:
                                index = self.target_tree.indexOfTopLevelItem(item)
                                if index >= 0:
                                    self.target_tree.takeTopLevelItem(index)
                        else:
                            for i in range(item.childCount() - 1, -1, -1):
                                remove_item_recursive(item.child(i))
                    
                    # 从顶层项开始移除
                    for i in range(self.target_tree.topLevelItemCount() - 1, -1, -1):
                        remove_item_recursive(self.target_tree.topLevelItem(i))
                    
                    # 恢复展开状态
                    self.target_tree.restore_expanded_state()

                    # 补充：更新监控，避免监控指向已移除路径
                    self.update_watcher()
                
                remove_selected_items()
            else:
                # 非搜索状态下，使用刷新保持状态
                self.refresh_tree_preserve_state()
            
            self.log(f"已清空 {len(selected_paths)} 个选定项")
        except Exception as e:
            self.log(f"清空选定项错误: {str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "清空失败", f"清空选定项过程中发生错误: {str(e)}")

    def undo_last_action(self):
        """撤销上一次操作（修复问题3和问题4，并修复撤销时重置搜索的问题）"""
        if not self.operation_history:
            self.log("没有可撤销的操作")
            return
        
        last_op = self.operation_history.pop()
        
        if last_op['type'] == 'clear_tree':
            # 恢复清空的树
            self.original_tree_items = last_op['original_items']
            self.removed_items = last_op['removed_items']
            # 恢复搜索状态
            self.search_query = last_op['search_state']['query']
            self.search_type = last_op['search_state']['type']
            # 使用refresh_tree_preserve_state保持搜索状态
            self.refresh_tree_preserve_state()
            self.log("已撤销清空目录操作")
        elif last_op['type'] == 'clear_selected':
            # 恢复列表与搜索状态
            self.original_tree_items = last_op['original_items']
            self.removed_items = last_op['removed_items']
            self.search_query = last_op['search_state']['query']
            self.search_type = last_op['search_state']['type']
            
            # 先刷新并应用搜索过滤，再恢复展开状态
            saved_expanded_paths = last_op['expanded_paths']
            self.refresh_tree_preserve_state()
            self.target_tree.expanded_paths = saved_expanded_paths
            self.target_tree.restore_expanded_state()
            
            self.log(f"已撤销清空 {len(last_op['removed_paths'])} 个选定项的操作")
        elif last_op['type'] == 'rename':
            old_path = last_op['old_path']
            new_path = last_op['new_path']
            try:
                if os.path.exists(new_path) and not os.path.exists(old_path):
                    os.rename(new_path, old_path)
            except Exception as e:
                self.log(f"撤销重命名失败（文件系统）：{str(e)}", QColor(Qt.red))
            # 恢复列表与状态
            self.original_tree_items = last_op.get('original_tree_items', self.original_tree_items)
            self.removed_items = last_op.get('removed_items', self.removed_items)
            self.target_tree.expanded_paths = last_op.get('expanded_paths', self.target_tree.expanded_paths)
            self.target_tree.loaded_dirs = last_op.get('loaded_dirs', self.target_tree.loaded_dirs)
            self.search_query = last_op.get('search_state', {}).get('query', self.search_query)
            self.search_type = last_op.get('search_state', {}).get('type', self.search_type)
            # 刷新并恢复展开状态
            self.refresh_tree_preserve_state()
            self.target_tree.restore_expanded_state()
            self.log(f"已撤销重命名: {new_path} -> {old_path}")

    # ------------------ 新增功能实现 ------------------
    def copy_selected_path(self):
        """复制选中项的绝对路径到剪贴板"""
        selected_items = self.target_tree.selectedItems()
        if not selected_items:
            return
            
        paths = [item.data(0, Qt.UserRole) for item in selected_items]
        clipboard = QApplication.clipboard()
        
        if len(paths) == 1:
            clipboard.setText(paths[0])
            self.log(f"已复制路径: {paths[0]}")
        else:
            clipboard.setText("\n".join(paths))
            self.log(f"已复制 {len(paths)} 个路径")

    def open_selected_dir(self):
        """在文件管理器中打开选中项所在的目录"""
        selected_items = self.target_tree.selectedItems()
        if not selected_items:
            return
        
        path = selected_items[0].data(0, Qt.UserRole)
        selected_is_file = os.path.isfile(path)
        selected_file_path = path if selected_is_file else None
        if selected_is_file:
            path = os.path.dirname(path)
        
        # 规整路径为绝对路径并使用反斜杠
        path = os.path.normpath(os.path.abspath(path))
        
        if not os.path.exists(path):
            self.log(f"目录不存在: {path}", QColor(Qt.red))
            QMessageBox.warning(self, "错误", f"目录不存在: {path}")
            return
        
        try:
            # Windows 使用 Explorer，避免 QDesktopServices 某些环境下崩溃
            if os.name == 'nt':
                if selected_file_path and os.path.exists(selected_file_path):
                    file_arg = os.path.normpath(os.path.abspath(selected_file_path))
                    # 使用列表参数并禁用 shell，避免引号与空格问题
                    subprocess.Popen(['explorer', '/select,', file_arg], shell=False)
                else:
                    subprocess.Popen(['explorer', path], shell=False)
                self.log(f"已打开目录: {path}")
            else:
                # 其他平台沿用 QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                self.log(f"已打开目录: {path}")
        except Exception as e:
            self.log(f"打开目录失败: {str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "错误", f"打开目录失败: {str(e)}")

    def rename_selected_item(self):
        """重命名选中的文件或文件夹（递归更新子节点路径与展开/加载状态，并支持撤销）"""
        selected_items = self.target_tree.selectedItems()
        if not selected_items or len(selected_items) != 1:
            QMessageBox.warning(self, "重命名", "请选择一个项目进行重命名")
            return

        item = selected_items[0]
        old_path = item.data(0, Qt.UserRole)
        if not old_path or not os.path.exists(old_path):
            QMessageBox.warning(self, "重命名失败", "路径无效或不存在")
            return

        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "重命名", f"输入新的名称（当前：{old_name}）", text=old_name)

        if not ok:
            return

        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "重命名失败", "名称不能为空")
            return

        if new_name == old_name:
            self.log("名称未改变，已取消重命名")
            return

        new_path = os.path.join(os.path.dirname(old_path), new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "重命名失败", f"目标已存在：{new_path}")
            return

        try:
            # 记录重命名前的状态用于撤销
            expanded_paths_snapshot = self.target_tree.expanded_paths.copy()
            loaded_dirs_snapshot = self.target_tree.loaded_dirs.copy()
            original_tree_items_snapshot = self.original_tree_items.copy()
            removed_items_snapshot = self.removed_items.copy()
            search_state_snapshot = {
                'query': self.search_query,
                'type': self.search_type
            }

            os.rename(old_path, new_path)

            # 更新当前节点显示与路径
            item.setText(0, new_name)
            item.setData(0, Qt.UserRole, new_path)

            # 如果是目录，递归更新子节点路径
            if os.path.isdir(new_path):
                def remap_children(node):
                    for i in range(node.childCount()):
                        child = node.child(i)
                        c_path = child.data(0, Qt.UserRole)
                        if c_path and isinstance(c_path, str) and c_path.startswith(old_path):
                            new_c_path = new_path + c_path[len(old_path):]
                            child.setData(0, Qt.UserRole, new_c_path)
                            child.setText(0, os.path.basename(new_c_path))
                        remap_children(child)
                remap_children(item)

                # 同步展开和已加载集合
                def remap_set(s):
                    updated = set()
                    for p in s:
                        if p and isinstance(p, str) and p.startswith(old_path):
                            updated.add(new_path + p[len(old_path):])
                        else:
                            updated.add(p)
                    return updated

                self.target_tree.expanded_paths = remap_set(self.target_tree.expanded_paths)
                self.target_tree.loaded_dirs = remap_set(self.target_tree.loaded_dirs)

                # 同步原始与移除列表
                self.original_tree_items = [
                    (new_path + p[len(old_path):]) if p and p.startswith(old_path) else p
                    for p in self.original_tree_items
                ]
                self.removed_items = [
                    (new_path + p[len(old_path):]) if p and p.startswith(old_path) else p
                    for p in self.removed_items
                ]
            else:
                # 文件重命名时更新列表
                if old_path in self.original_tree_items:
                    idx = self.original_tree_items.index(old_path)
                    self.original_tree_items[idx] = new_path
                self.removed_items = [new_path if p == old_path else p for p in self.removed_items]

            # 更新监控并记录日志
            self.update_watcher()
            self.log(f"已重命名: {old_path} → {new_path}")

            # 记录操作历史以支持撤销
            self.operation_history.append({
                'type': 'rename',
                'old_path': old_path,
                'new_path': new_path,
                'expanded_paths': expanded_paths_snapshot,
                'loaded_dirs': loaded_dirs_snapshot,
                'original_tree_items': original_tree_items_snapshot,
                'removed_items': removed_items_snapshot,
                'search_state': search_state_snapshot
            })
        except Exception as e:
            self.log(f"重命名失败: {str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "重命名失败", f"重命名失败：{str(e)}")

    def delete_selected_items(self):
        """删除选中的文件或文件夹（带确认）"""
        selected_items = self.target_tree.selectedItems()
        if not selected_items:
            return
            
        paths = [item.data(0, Qt.UserRole) for item in selected_items]
        if len(paths) == 1:
            msg = f"确定要删除以下{'文件夹' if os.path.isdir(paths[0]) else '文件'}吗？\n\n{paths[0]}"
        else:
            msg = f"确定要删除以下 {len(paths)} 个项目吗？\n\n{paths[0]}\n..."
        
        reply = QMessageBox.warning(
            self, "确认删除", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = 0
            failed_count = 0
            failed_paths = []
            
            for path in paths:
                try:
                    if os.path.isfile(path) or os.path.islink(path):
                        os.remove(path)
                        deleted_count += 1
                        self.log(f"已删除文件: {path}")
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                        deleted_count += 1
                        self.log(f"已删除文件夹: {path}")
                    
                    # 从原始项列表中移除
                    if path in self.original_tree_items:
                        self.original_tree_items.remove(path)
                    
                    # 从已移除项列表中移除
                    if path in self.removed_items:
                        self.removed_items.remove(path)
                except Exception as e:
                    failed_count += 1
                    failed_paths.append(f"{path} ({str(e)})")
                    self.log(f"删除失败: {path} - {str(e)}", QColor(Qt.red))
            
            self.refresh_tree()  # 刷新以反映删除结果
            
            result_msg = f"删除完成：成功删除 {deleted_count} 个项目"
            if failed_count > 0:
                result_msg += f"，{failed_count} 个项目删除失败：\n" + "\n".join(failed_paths)
            
            self.log(result_msg)
            QMessageBox.information(self, "删除结果", result_msg)

    # ------------------ 展开/关闭功能 ------------------
    def expand_all(self, expand=True):
        """展开/关闭所有项"""
        if expand:
            # 展开所有项，并加载它们的子项
            def expand_recursive(item):
                path = item.data(0, Qt.UserRole)
                if os.path.isdir(path) and path not in self.target_tree.loaded_dirs:
                    self.target_tree.load_children(item, path)
                    self.target_tree.loaded_dirs.add(path)
                item.setExpanded(True)
                for i in range(item.childCount()):
                    expand_recursive(item.child(i))
            
            for i in range(self.target_tree.topLevelItemCount()):
                expand_recursive(self.target_tree.topLevelItem(i))
        else:
            self.target_tree.collapseAll()
        
        self.log(f"已{'展开' if expand else '关闭'}所有项")

    def expand_selected(self, expand=True):
        """展开/关闭选定项"""
        selected_items = self.target_tree.selectedItems()
        
        for item in selected_items:
            if expand:
                # 展开并加载子项
                def expand_recursive(child_item):
                    path = child_item.data(0, Qt.UserRole)
                    if os.path.isdir(path) and path not in self.target_tree.loaded_dirs:
                        self.target_tree.load_children(child_item, path)
                        self.target_tree.loaded_dirs.add(path)
                    child_item.setExpanded(True)
                    for i in range(child_item.childCount()):
                        expand_recursive(child_item.child(i))
                
                expand_recursive(item)
            else:
                item.setExpanded(False)
                # 递归处理子项
                def collapse_recursive(child_item):
                    child_item.setExpanded(False)
                    for i in range(child_item.childCount()):
                        collapse_recursive(child_item.child(i))
                for i in range(item.childCount()):
                    collapse_recursive(item.child(i))
        
        self.log(f"已{'展开' if expand else '关闭'} {len(selected_items)} 个选定项")

    def collapse_unselected(self):
        """关闭未选定项（只关闭完全未被选中的项）"""
        try:
            # 获取选中的项 - 使用列表而不是集合，因为QTreeWidgetItem不可哈希
            selected_items = self.target_tree.selectedItems()
            
            # 使用迭代方式遍历所有项，避免递归深度过大
            all_items = []
            stack = []
            
            # 添加所有顶层项到栈中
            for i in range(self.target_tree.topLevelItemCount()):
                stack.append(self.target_tree.topLevelItem(i))
            
            # 迭代遍历所有项
            while stack:
                item = stack.pop()
                all_items.append(item)
                # 将子项添加到栈中（反向添加以保证顺序）
                for i in range(item.childCount()-1, -1, -1):
                    stack.append(item.child(i))
            
            # 检查每个项是否应该被关闭
            def should_collapse(item):
                # 如果项本身被选中，不应该关闭
                if item in selected_items:  # 直接使用列表的in操作
                    return False
                
                # 使用迭代方式检查是否有任何子项被选中
                stack = []
                for i in range(item.childCount()):
                    stack.append(item.child(i))
                
                while stack:
                    child_item = stack.pop()
                    if child_item in selected_items:  # 直接使用列表的in操作
                        return False
                    # 将子项的子项添加到栈中
                    for i in range(child_item.childCount()-1, -1, -1):
                        stack.append(child_item.child(i))
                
                return True
            
            # 折叠应该被关闭的项
            unselected_count = 0
            for item in all_items:
                if should_collapse(item):
                    item.setExpanded(False)
                    unselected_count += 1
            
            self.log(f"已关闭 {unselected_count} 个未选定项")
            
        except Exception as e:
            # 捕获异常并记录错误，避免程序崩溃
            self.log(f"关闭未选定项时出错: {str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "操作失败", f"关闭未选定项时发生错误：{str(e)}")

    # ------------------ 其他保留功能 ------------------
    def browse_source(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择源文件")
        if p:
            self.source_edit.setText(p)
            self.log(f"已选择源文件: {p}")

    def browse_target(self):
        d = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if d:
            # 添加新目录（不替换）
            if d not in self.original_tree_items and d not in self.removed_items:
                self.load_tree_lazy(d)
                self.update_watcher()
                # 记录操作历史
                self.operation_history.append({
                    'type': 'add_directory',
                    'path': d,
                    'search_state': {
                        'query': self.search_query,
                        'type': self.search_type
                    }
                })
            self.log(f"已选择目标目录: {d}")

    def browse_backup(self):
        d = QFileDialog.getExistingDirectory(self, "选择备份目录")
        if d:
            self.backup_edit.setText(d)
            self.backup_dir = d
            self.update_backup_controls()
            self.log(f"已选择备份目录: {d}")

    def get_backup_input_path(self):
        """规范化备份输入路径：去引号、扩展变量、归一化分隔符并返回绝对路径"""
        try:
            raw = (self.backup_edit.text() or "").strip()
            if not raw:
                return ""
            # 去除包裹的引号（用户从外部复制时常见）
            if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                raw = raw[1:-1].strip()
            # 展开环境变量与用户目录
            raw = os.path.expandvars(os.path.expanduser(raw))
            # 归一化路径（保持有效性检查与显示一致）
            norm = os.path.normpath(raw)
            try:
                # 尽量转换为绝对路径（不会创建路径）
                norm = os.path.abspath(norm)
            except Exception:
                pass
            return norm
        except Exception:
            return (self.backup_edit.text() or "").strip()

    def update_backup_controls(self):
        is_enabled = bool(self.backup_enable.isChecked())
        backup_dir = self.get_backup_input_path()
        is_valid_backup = False
        is_valid_selected_file = False
        has_selected_targets = False
        has_existing_list = False
        
        try:
            if is_enabled and backup_dir:
                is_valid_backup = bool(os.path.exists(backup_dir) and os.path.isdir(backup_dir))
                is_valid_selected_file = bool(os.path.exists(backup_dir) and os.path.isfile(backup_dir))
        except Exception as e:
            self.log(f"检查备份目录时出错: {str(e)}")
            is_valid_backup = False
            is_valid_selected_file = False

        try:
            has_existing_list = self.backup_existing_combo.count() > 0
        except Exception:
            has_existing_list = False

        try:
            has_selected_targets = len(self.target_tree.selectedItems()) > 0
        except Exception:
            has_selected_targets = False
        
        self.backup_edit.setEnabled(is_enabled)
        self.btn_backup_select.setEnabled(is_enabled)
        self.btn_backup_clear.setEnabled(is_enabled)
        # 下拉框总是可用，用于从已有备份选择
        self.backup_existing_combo.setEnabled(True)
        # 允许：输入框是有效文件 或 有效备份路径（目录/文件），不再强制要求左侧选中
        self.btn_restore_selected.setEnabled(is_valid_selected_file or is_valid_backup)
        # 当已有备份列表非空时，允许“还原所有文件”与“清除所有备份”
        self.btn_restore_all.setEnabled(has_existing_list)
        self.btn_clear_all.setEnabled(has_existing_list)
        # 当输入框路径存在（文件或文件夹）时允许“清除选中备份”
        self.btn_clear_selected.setEnabled(bool(backup_dir and os.path.exists(backup_dir)))

    def add_existing_backup(self, path):
        """将备份目录加入“已有的备份”下拉框（去重）"""
        try:
            if not path:
                return
            idx = self.backup_existing_combo.findText(path)
            if idx == -1:
                # 在程序性添加期间不触发自动填充
                self.suppress_backup_selection = True
                self.backup_existing_combo.addItem(path)
                self.suppress_backup_selection = False
        except Exception:
            pass

    def on_existing_backup_selected(self, index):
        """选择已有备份后，将路径填入备份输入框用于还原"""
        try:
            if index < 0:
                return
            path = self.backup_existing_combo.itemText(index)
            if path:
                if self.suppress_backup_selection:
                    # 程序性变更时不自动填充
                    return
                self.backup_edit.setText(path)
                self.backup_dir = path
                self.update_backup_controls()
                self.log(f"已从已有备份选择：{path}")
        except Exception as e:
            self.log(f"选择已有备份时出错: {str(e)}")

    def on_existing_backup_activated(self, index):
        """点击下拉框条目时总是填充输入框（解决单条目无法点击问题）"""
        try:
            if index < 0:
                index = self.backup_existing_combo.currentIndex()
            if index < 0:
                return
            path = self.backup_existing_combo.itemText(index)
            if path:
                self.backup_edit.setText(path)
                self.backup_dir = path
                self.update_backup_controls()
                self.log(f"已从已有备份点击选择：{path}")
        except Exception as e:
            self.log(f"点击已有备份时出错: {str(e)}")

    def scan_matches(self):
        src = self.source_edit.text()
        if not src or not os.path.exists(src):
            raise ValueError("源文件不存在或未选择")
        
        mode = self.match_combo.currentText()
        pattern = self.match_edit.text().strip()
        skip_keywords = [k.strip() for k in re.split(r'[，,]', self.skip_edit.text()) if k.strip()]
        targets = self.get_selected_files()  # 使用选择的文件而非勾选的文件
        
        if not targets:
            raise ValueError("未选择任何目标文件")
        
        matches = []
        for full in targets:
            # 跳过备份目录及其子项（避免将备份文件作为目标）
            try:
                if self.backup_dir:
                    bdir = os.path.abspath(self.backup_dir)
                    fpath = os.path.abspath(full)
                    if fpath == bdir or fpath.startswith(bdir + os.sep):
                        continue
                
            except Exception:
                pass
            if os.path.samefile(src, full):
                continue
            if any(kw in os.path.basename(full) for kw in skip_keywords):
                self.log(f"已跳过: {full} (匹配到跳过关键词)")
                continue
            filename = os.path.basename(full)
            matched = False
            
            if mode == "后缀匹配":
                if not pattern:
                    raise ValueError("后缀匹配模式请输入后缀（如 .10 或 10）")
                _, ext = os.path.splitext(filename)
                if ext.lower().lstrip(".") == pattern.lower().lstrip("."):
                    matched = True
            elif mode == "关键词匹配":
                if not pattern:
                    raise ValueError("关键词匹配模式请输入关键词")
                keys = [k.strip() for k in re.split(r'[，,]', pattern) if k.strip()]
                if keys and any(k in filename for k in keys):
                    matched = True
            elif mode == "正则表达式":
                if not pattern:
                    raise ValueError("正则表达式模式请输入正则")
                try:
                    if re.search(pattern, filename):
                        matched = True
                except re.error:
                    raise ValueError(f"无效正则表达式: {pattern}")
            
            if matched:
                matches.append(full)
        
        return matches

    def on_clear_backup(self):
        backup_dir = self.backup_edit.text().strip()
        if not backup_dir or not os.path.exists(backup_dir):
            QMessageBox.warning(self, "清除失败", "备份目录不存在")
            return
        
        confirm_msg = f"确定删除备份文件夹及所有内容？\n\n目录：{backup_dir}\n⚠️  删除后不可恢复！"
        reply = QMessageBox.warning(
            self, "确认清除备份", confirm_msg,
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply != QMessageBox.Ok:
            return
        
        try:
            shutil.rmtree(backup_dir)
            self.log(f"成功删除备份目录：{backup_dir}")
            self.backup_edit.clear()
            self.backup_dir = None
            # 从“已有的备份”下拉框移除
            try:
                idx = self.backup_existing_combo.findText(backup_dir)
                if idx != -1:
                    self.backup_existing_combo.removeItem(idx)
            except Exception:
                pass
            self.update_backup_controls()
            QMessageBox.information(self, "清除成功", f"备份目录已删除：{backup_dir}")
        except PermissionError:
            msg = "删除失败：备份文件夹被其他程序占用，请关闭相关程序后重试"
            QMessageBox.critical(self, "清除失败", msg)
            self.log(f"错误：{msg}")
        except Exception as e:
            msg = f"删除失败：{str(e)}"
            QMessageBox.critical(self, "清除失败", msg)
            self.log(f"错误：{msg}")

    def on_preview(self):
        try:
            if not self.validate_inputs():
                return
            matches = self.scan_matches()
            self.result_list.clear()
            # 使用HTML将数字显示为红色
            self.preview_header.setText(f"已找到 <span style='color: red'>{len(matches)}</span> 个匹配文件 (预览模式)")
            for full in matches:
                self.result_list.append_text(f"{os.path.basename(full)} {{{full}}}")
            self.log(f"预览完成，找到 {len(matches)} 个匹配文件")
        except ValueError as ve:
            self.log(f"错误：{str(ve)}", QColor(Qt.red))
            QMessageBox.warning(self, "预览失败", str(ve))

    def on_replace(self):
        try:
            if not self.validate_inputs():
                return
            matches = self.scan_matches()
            if not matches:
                QMessageBox.warning(self, "替换失败", "未找到匹配的目标文件")
                return

            src_path = self.source_edit.text().strip()
            src_dir = os.path.dirname(src_path)
            backup_dir_user = self.backup_edit.text().strip()
            self.backup_dir = None

            if self.backup_enable.isChecked():
                # 未选择备份路径：在源文件同目录下创建带秒级时间戳的备份文件夹
                local_time = time.localtime()
                timestamp = f"{local_time.tm_year}-{local_time.tm_mon}-{local_time.tm_mday}-{local_time.tm_hour}-{local_time.tm_min}-{local_time.tm_sec}"
                if not backup_dir_user:
                    backup_dir_name = f"backup-{timestamp}"
                    backup_dir_user = os.path.join(src_dir, backup_dir_name)
                    os.makedirs(backup_dir_user, exist_ok=True)
                    # 不自动填充输入框，遵循需求 2
                    self.backup_dir = backup_dir_user
                    self.log(f"自动创建备份目录：{backup_dir_user}", color=QColor(Qt.blue))
                else:
                    # 使用用户选择的备份路径（不创建子文件夹）
                    os.makedirs(backup_dir_user, exist_ok=True)
                    self.backup_dir = backup_dir_user
                    self.log(f"使用指定备份目录：{self.backup_dir}")

                # 生成或追加 manifest.json（记录多个原始路径与备份相对路径，去重）
                manifest_path = os.path.join(self.backup_dir, "manifest.json")
                manifest = None
                try:
                    if os.path.exists(manifest_path):
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)
                    else:
                        manifest = {"version": 2, "created_at": timestamp, "entries": []}
                except Exception:
                    # 如果旧文件损坏，则从头重建
                    manifest = {"version": 2, "created_at": timestamp, "entries": []}

                # 建立已有 original_path 集合以去重
                existing = set()
                try:
                    for e in manifest.get("entries", []):
                        op = e.get("original_path")
                        if op:
                            existing.add(op)
                except Exception:
                    pass

                for full in matches:
                    if full in existing:
                        continue
                    # 不创建父级子目录，统一使用文件名作为备份相对路径
                    backup_rel_path = os.path.basename(full).replace('\\', '/')
                    manifest.setdefault("entries", []).append({
                        "backup_rel_path": backup_rel_path,
                        "original_path": full
                    })

                try:
                    with open(manifest_path, 'w', encoding='utf-8') as f:
                        json.dump(manifest, f, ensure_ascii=False, indent=2)
                    self.log(f"已记录/更新备份映射到: {manifest_path}")
                except Exception as e:
                    self.log(f"记录备份映射失败: {str(e)}", QColor(Qt.red))

                # 将本次备份加入“已有的备份”下拉框
                self.add_existing_backup(self.backup_dir)
                
                self.update_backup_controls()
            else:
                self.log("未启用备份，跳过备份步骤")

            self.progress_label_left.setText("替换进度：")
            self.result_list.clear()
            self.preview_header.setText("")
            self.progress_bar.setValue(0)
            self.progress_label_right.setText("处理中...")
            self.btn_preview.setEnabled(False)
            self.btn_replace.setEnabled(False)

            self.thread = FileReplacerThread(
                source_file=src_path,
                targets=matches,
                backup_dir=self.backup_dir,
                preview_only=False
            )
            self.thread.progress_signal.connect(self.on_progress)
            self.thread.finished_signal.connect(self.on_finished)
            self.thread.log_signal.connect(self.log)  # 连接带颜色的日志信号
            self.thread.start()
            self.log(f"开始替换 {len(matches)} 个文件...", color=QColor(Qt.blue))
        except ValueError as ve:
            self.log(f"错误：{str(ve)}", QColor(Qt.red))
            QMessageBox.warning(self, "替换失败", str(ve))
            self.btn_preview.setEnabled(True)
            self.btn_replace.setEnabled(True)

    def on_restore(self):
        try:
            if not self.backup_enable.isChecked():
                QMessageBox.warning(self, "还原失败", "请先勾选「启用备份」")
                return
            
            backup_dir = self.backup_edit.text().strip()
            if not backup_dir or not os.path.exists(backup_dir):
                QMessageBox.warning(self, "还原失败", "备份目录不存在")
                return
            self.backup_dir = backup_dir
            
            restore_map = {}
            files_to_restore = []
            manifest_json = os.path.join(self.backup_dir, "manifest.json")
            manifest_txt = os.path.join(self.backup_dir, "manifest.txt")
            target_root = None
            if os.path.exists(manifest_json):
                try:
                    with open(manifest_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    entries = data.get("entries", [])
                    for entry in entries:
                        rel = entry.get("backup_rel_path")
                        orig = entry.get("original_path")
                        if not rel or not orig:
                            continue
                        backup_file_path = os.path.join(self.backup_dir, rel.replace('/', os.sep))
                        files_to_restore.append(backup_file_path)
                        restore_map[backup_file_path] = orig
                    self.log(f"已读取 manifest.json，共 {len(restore_map)} 条还原映射")
                except Exception as e:
                    QMessageBox.warning(self, "还原失败", f"解析 manifest.json 失败：{str(e)}")
                    return
            elif os.path.exists(manifest_txt):
                # 兼容旧版本：使用目标根路径拼接相对路径
                with open(manifest_txt, 'r', encoding='utf-8') as f:
                    target_root = f.read().strip()
                if not target_root or not os.path.exists(target_root):
                    QMessageBox.warning(self, "还原失败", f"manifest记录的原路径无效：{target_root}")
                    return
                self.log(f"从manifest读取原目标根路径：{target_root}")
                for root, _, files in os.walk(self.backup_dir):
                    for f in files:
                        if f == "manifest.txt":
                            continue
                        backup_file_path = os.path.join(root, f)
                        files_to_restore.append(backup_file_path)
            else:
                QMessageBox.warning(self, "还原失败", "备份目录缺少 manifest 文件")
                return
            
            if not files_to_restore:
                QMessageBox.information(self, "还原", "备份目录中无文件可还原")
                return

            self.progress_label_left.setText("还原进度：")
            self.progress_label_right.setText("处理中...")
            self.result_list.clear()
            self.preview_header.setText("")
            self.progress_bar.setValue(0)
            self.btn_preview.setEnabled(False)
            self.btn_replace.setEnabled(False)

            self.thread = FileReplacerThread(
                source_file=None,
                targets=files_to_restore,
                backup_dir=self.backup_dir,
                preview_only=False,
                restore=True,
                target_root=target_root,
                restore_map=restore_map if restore_map else None
            )
            self.thread.progress_signal.connect(self.on_progress)
            self.thread.finished_signal.connect(self.on_finished)
            self.thread.log_signal.connect(self.log)  # 连接带颜色的日志信号
            self.thread.start()
            self.log(f"开始还原 {len(files_to_restore)} 个备份文件...", color=QColor(Qt.blue))
        except Exception as e:
            self.log(f"错误：还原初始化失败：{str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "还原失败", str(e))
            self.btn_preview.setEnabled(True)
            self.btn_replace.setEnabled(True)

    def on_restore_selected(self):
        try:
            if not self.backup_enable.isChecked():
                QMessageBox.warning(self, "还原失败", "请先勾选「启用备份」")
                return
            selected_path = self.get_backup_input_path()
            if not selected_path or not os.path.exists(selected_path):
                QMessageBox.warning(self, "还原失败", "请选择有效的备份路径（文件或文件夹）")
                return

            restore_map = {}
            target_root = None
            files_to_restore = []
            base_dir = None

            if os.path.isfile(selected_path):
                # 文件模式：按文件相对路径查询映射
                start_dir = os.path.dirname(selected_path)
                manifest_json = None
                for _ in range(4):
                    candidate = os.path.join(start_dir, "manifest.json")
                    if os.path.exists(candidate):
                        base_dir = start_dir
                        manifest_json = candidate
                        break
                    parent = os.path.dirname(start_dir)
                    if parent == start_dir:
                        break
                    start_dir = parent

                files_to_restore = [selected_path]
                if manifest_json and os.path.exists(manifest_json):
                    try:
                        with open(manifest_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        rel = os.path.relpath(selected_path, base_dir).replace('\\', '/')
                        found = None
                        for e in data.get("entries", []):
                            if e.get("backup_rel_path") == rel:
                                found = e.get("original_path")
                                break
                        if not found:
                            QMessageBox.warning(self, "还原失败", "manifest.json 中未找到对应映射")
                            return
                        restore_map[selected_path] = found
                    except Exception as e:
                        QMessageBox.warning(self, "还原失败", f"解析 manifest.json 失败：{str(e)}")
                        return
                else:
                    # 兼容旧版：尝试使用 manifest.txt
                    manifest_txt = os.path.join(base_dir if base_dir else os.path.dirname(selected_path), "manifest.txt")
                    if os.path.exists(manifest_txt):
                        try:
                            with open(manifest_txt, 'r', encoding='utf-8') as f:
                                target_root = f.read().strip()
                            rel = os.path.relpath(selected_path, base_dir if base_dir else os.path.dirname(selected_path))
                            restore_map[selected_path] = os.path.join(target_root, rel)
                        except Exception as e:
                            QMessageBox.warning(self, "还原失败", f"解析 manifest.txt 失败：{str(e)}")
                            return
                    else:
                        QMessageBox.warning(self, "还原失败", "未找到 manifest 文件")
                        return
            else:
                # 目录模式：优先还原左侧选中；若未选中则按备份目录全部还原
                base_dir = selected_path
                manifest_json = os.path.join(base_dir, "manifest.json")
                manifest_txt = os.path.join(base_dir, "manifest.txt")
                selected_originals = set(self.get_selected_files())
                restore_all = len(selected_originals) == 0
                if os.path.exists(manifest_json):
                    try:
                        with open(manifest_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        for e in data.get("entries", []):
                            orig = e.get("original_path")
                            rel = e.get("backup_rel_path")
                            if not orig or not rel:
                                continue
                            if restore_all or orig in selected_originals:
                                bf = os.path.join(base_dir, rel.replace('/', os.sep))
                                if os.path.exists(bf):
                                    files_to_restore.append(bf)
                                    restore_map[bf] = orig
                    except Exception as e:
                        QMessageBox.warning(self, "还原失败", f"解析 manifest.json 失败：{str(e)}")
                        return
                elif os.path.exists(manifest_txt):
                    try:
                        with open(manifest_txt, 'r', encoding='utf-8') as f:
                            target_root = f.read().strip()
                        if not target_root or not os.path.exists(target_root):
                            QMessageBox.warning(self, "还原失败", f"manifest记录的原路径无效：{target_root}")
                            return
                        for root, _, files in os.walk(base_dir):
                            for f in files:
                                if f in ("manifest.txt", "manifest.json"):
                                    continue
                                bf = os.path.join(root, f)
                                rel = os.path.relpath(bf, base_dir)
                                orig = os.path.join(target_root, rel)
                                if restore_all or orig in selected_originals:
                                    files_to_restore.append(bf)
                    except Exception as e:
                        QMessageBox.warning(self, "还原失败", f"解析 manifest.txt 失败：{str(e)}")
                        return
                else:
                    QMessageBox.warning(self, "还原失败", "备份目录缺少 manifest 文件")
                    return

                if not files_to_restore:
                    QMessageBox.information(self, "还原", "所选项目在备份中未找到对应文件")
                    return

            self.progress_label_left.setText("还原进度：")
            self.progress_label_right.setText("处理中...")
            self.result_list.clear()
            self.preview_header.setText("")
            self.progress_bar.setValue(0)
            self.btn_preview.setEnabled(False)
            self.btn_replace.setEnabled(False)

            self.thread = FileReplacerThread(
                source_file=None,
                targets=files_to_restore,
                backup_dir=base_dir,
                preview_only=False,
                restore=True,
                target_root=target_root,
                restore_map=restore_map if restore_map else None
            )
            self.thread.progress_signal.connect(self.on_progress)
            self.thread.finished_signal.connect(self.on_finished)
            self.thread.log_signal.connect(self.log)
            self.thread.start()
            self.log(f"开始还原选中文件 {len(files_to_restore)} 个...", color=QColor(Qt.blue))
        except Exception as e:
            self.log(f"错误：还原选中文件失败：{str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "还原失败", str(e))

    def on_restore_all(self):
        try:
            total = self.backup_existing_combo.count()
            if total <= 0:
                QMessageBox.information(self, "还原", "列表中无可还原项")
                return

            files_to_restore = []
            restore_map = {}
            # 汇总所有已有备份目录中的文件
            for i in range(total):
                bdir = self.backup_existing_combo.itemText(i)
                if not bdir or not os.path.exists(bdir) or not os.path.isdir(bdir):
                    continue
                manifest_json = os.path.join(bdir, "manifest.json")
                manifest_txt = os.path.join(bdir, "manifest.txt")
                if os.path.exists(manifest_json):
                    try:
                        with open(manifest_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        for e in data.get("entries", []):
                            rel = e.get("backup_rel_path")
                            orig = e.get("original_path")
                            if not rel or not orig:
                                continue
                            bf = os.path.join(bdir, rel.replace('/', os.sep))
                            if os.path.exists(bf):
                                files_to_restore.append(bf)
                                restore_map[bf] = orig
                    except Exception as e:
                        self.log(f"解析 {manifest_json} 失败：{str(e)}", QColor(Qt.red))
                        continue
                elif os.path.exists(manifest_txt):
                    try:
                        with open(manifest_txt, 'r', encoding='utf-8') as f:
                            target_root = f.read().strip()
                        for root, _, files in os.walk(bdir):
                            for f in files:
                                if f in ("manifest.txt", "manifest.json"):
                                    continue
                                bf = os.path.join(root, f)
                                rel = os.path.relpath(bf, bdir)
                                files_to_restore.append(bf)
                                restore_map[bf] = os.path.join(target_root, rel)
                    except Exception as e:
                        self.log(f"解析 {manifest_txt} 失败：{str(e)}", QColor(Qt.red))
                        continue

            if not files_to_restore:
                QMessageBox.information(self, "还原", "无文件可还原")
                return

            self.progress_label_left.setText("还原进度：")
            self.progress_label_right.setText("处理中...")
            self.result_list.clear()
            self.preview_header.setText("")
            self.progress_bar.setValue(0)
            self.btn_preview.setEnabled(False)
            self.btn_replace.setEnabled(False)

            self.thread = FileReplacerThread(
                source_file=None,
                targets=files_to_restore,
                backup_dir=None,
                preview_only=False,
                restore=True,
                target_root=None,
                restore_map=restore_map
            )
            self.thread.progress_signal.connect(self.on_progress)
            self.thread.finished_signal.connect(self.on_finished)
            self.thread.log_signal.connect(self.log)
            self.thread.start()
            self.log(f"开始还原所有文件，共 {len(files_to_restore)} 个...", color=QColor(Qt.blue))
        except Exception as e:
            self.log(f"错误：还原所有文件失败：{str(e)}", QColor(Qt.red))
            QMessageBox.warning(self, "还原失败", str(e))

    def on_clear_selected_backup(self):
        try:
            path = self.backup_edit.text().strip()
            if not path or not os.path.exists(path):
                QMessageBox.warning(self, "清除失败", "备份路径不存在")
                return
            # 确认删除选中的备份
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确认删除备份：\n{path}\n此操作不可撤销",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    self.log(f"已删除备份文件：{path}")
                except Exception as e:
                    QMessageBox.critical(self, "清除失败", f"删除文件失败：{str(e)}")
                    return
            else:
                try:
                    shutil.rmtree(path)
                    self.log(f"已删除备份目录：{path}")
                    # 从下拉框移除该目录
                    try:
                        idx = self.backup_existing_combo.findText(path)
                        if idx != -1:
                            self.backup_existing_combo.removeItem(idx)
                    except Exception:
                        pass
                    # 如果输入框正好是该目录，清空
                    if self.backup_edit.text().strip() == path:
                        self.backup_edit.clear()
                except Exception as e:
                    QMessageBox.critical(self, "清除失败", f"删除目录失败：{str(e)}")
                    return
            self.update_backup_controls()
            # 按需不弹成功提示
        except Exception as e:
            self.log(f"错误：清除选中备份失败：{str(e)}", QColor(Qt.red))

    def on_clear_all_backups(self):
        try:
            total = self.backup_existing_combo.count()
            if total <= 0:
                QMessageBox.information(self, "清除", "无可清除的备份")
                return
            # 确认删除所有备份
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确认清除所有备份（共 {total} 项）？此操作不可撤销",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            removed = 0
            errors = 0
            paths = [self.backup_existing_combo.itemText(i) for i in range(total)]
            for p in paths:
                if not p or not os.path.exists(p):
                    continue
                if os.path.isdir(p):
                    try:
                        shutil.rmtree(p)
                        removed += 1
                    except Exception as e:
                        errors += 1
                        self.log(f"删除目录失败：{p}，错误：{str(e)}", QColor(Qt.red))
                else:
                    try:
                        os.remove(p)
                        removed += 1
                    except Exception as e:
                        errors += 1
                        self.log(f"删除文件失败：{p}，错误：{str(e)}", QColor(Qt.red))

            # 清空下拉框并更新控件
            self.backup_existing_combo.clear()
            # 如果输入框路径也在被删除列表中，清空
            cur = self.backup_edit.text().strip()
            if cur in paths:
                self.backup_edit.clear()
            self.update_backup_controls()
            # 按需不弹成功提示
        except Exception as e:
            self.log(f"错误：清除所有备份失败：{str(e)}", QColor(Qt.red))

    def on_progress(self, percent, filename):
        self.progress_bar.setValue(percent)
        self.progress_label_right.setText(f"处理中: {filename}")

    def on_finished(self, results):
        self.btn_preview.setEnabled(True)
        self.btn_replace.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label_right.setText("完成")
        
        success_count = 0
        error_count = 0
        locked_files = []

        for result in results:
            if isinstance(result, tuple):
                result_type, content = result
                if result_type in ["success", "restore"]:
                    self.result_list.append_text(content)
                    success_count += 1
                elif result_type == "error":
                    self.log(f"错误：{content}", QColor(Qt.red))
                    error_count += 1
                    if "被占用" in content:
                        locked_files.append(content.split("{")[1].rstrip("}"))
            else:
                self.result_list.append_text(result)
                if "错误" in result:
                    self.log(result, QColor(Qt.red))
                    error_count += 1
                else:
                    self.log(result)
                    success_count += 1
        
        if locked_files:
            msg = f"以下文件被占用，未处理：\n" + "\n".join(locked_files)
            QMessageBox.warning(self, "文件被占用", msg)
        
        mode = "还原" if hasattr(self.thread, 'restore') and self.thread.restore else "替换"
        # 使用HTML将数字显示为红色
        self.preview_header.setText(f"{mode} 完成：成功 <span style='color: red'>{success_count}</span> 个，失败 <span style='color: red'>{error_count}</span> 个")
        self.log(f"{mode} 完成：成功 {success_count} 个，失败 {error_count} 个", QColor(Qt.blue))

    def validate_inputs(self):
        src = self.source_edit.text().strip()
        if not src:
            QMessageBox.warning(self, "输入错误", "请选择源文件")
            return False
        if not os.path.exists(src):
            QMessageBox.warning(self, "文件错误", "源文件不存在")
            return False
        
        if self.backup_enable.isChecked():
            backup_dir = self.backup_edit.text().strip()
            if backup_dir and not os.path.exists(backup_dir):
                reply = QMessageBox.question(
                    self, "路径不存在", f"备份目录不存在，是否创建？\n{backup_dir}",
                    QMessageBox.Ok | QMessageBox.Cancel
                )
                if reply == QMessageBox.Ok:
                    os.makedirs(backup_dir, exist_ok=True)
                else:
                    return False
        
        mode = self.match_combo.currentText()
        pattern = self.match_edit.text().strip()
        if mode == "后缀匹配" and not pattern:
            QMessageBox.warning(self, "输入错误", "后缀匹配请输入后缀（如 .10 或 10）")
            return False
        if mode == "关键词匹配" and not pattern:
            QMessageBox.warning(self, "输入错误", "关键词匹配请输入关键词")
            return False
        if mode == "正则表达式" and not pattern:
            QMessageBox.warning(self, "输入错误", "正则表达式模式请输入正则")
            return False
        
        if not self.get_selected_files():  # 使用选择的文件而非勾选的文件
            QMessageBox.warning(self, "输入错误", "请在目标目录树中选择文件/文件夹")
            return False
        
        return True

    def refresh_tree_preserve_state(self):
        """刷新树但保持展开状态和搜索状态（修复问题2）"""
        # 保存当前展开状态
        self.target_tree.save_expanded_state()
        
        # 清空当前树和已加载目录记录
        # 暂停折叠事件对展开集合的影响，避免清空过程导致已保存的展开状态被误删
        self.target_tree.suspend_expand_tracking = True
        self.target_tree.clear()
        self.target_tree.loaded_dirs.clear()
        
        # 重新加载所有原始项（懒加载）
        for path in self.original_tree_items:
            if os.path.exists(path):
                self.load_tree_lazy(path)
        
        # 恢复展开状态
        self.target_tree.suspend_expand_tracking = False
        self.target_tree.restore_expanded_state()
        
        # 如果处于搜索状态，重新应用搜索过滤
        if self.search_query:
            self.apply_search_filter_preserve_state()
        
        # 更新监控
        self.update_watcher()

    def apply_search_filter_preserve_state(self):
        """应用搜索过滤但保持展开状态（修复问题2）"""
        if not self.search_query:
            return
            
        # 暂停展开状态跟踪，避免保存/搜索过程中清空集合
        self.target_tree.suspend_expand_tracking = True
        # 保留之前保存的 expanded_paths，不再覆盖为当前树的状态
        # self.target_tree.save_expanded_state()  # 在暂停期间不更新
        
        # 重新执行搜索（不触发展开集合清空）
        self.on_search_clicked()
        
        # 恢复展开状态
        self.target_tree.suspend_expand_tracking = False
        self.target_tree.restore_expanded_state()

    def refresh_tree(self):
        """刷新树状图（保留展开状态，重置搜索）"""
        # 重置搜索状态
        self.search_query = ""
        self.search_type = ""
        self.tree_search.clear()
        
        # 保存当前展开状态
        self.target_tree.save_expanded_state()
        
        # 清空当前树和已加载目录记录
        self.target_tree.clear()
        self.target_tree.loaded_dirs.clear()
        
        # 重新加载所有原始项（懒加载）
        for path in self.original_tree_items:
            if os.path.exists(path) and path not in self.removed_items:
                self.load_tree_lazy(path)
        
        # 恢复展开状态
        self.target_tree.restore_expanded_state()
        
        # 更新监控
        self.update_watcher()
        
        self.log("树状图已刷新，搜索已重置")

    def reset_search(self):
        """清空搜索并刷新（与刷新分离，避免逻辑冲突）"""
        # 清空搜索状态与搜索屏蔽集合
        self.search_query = ""
        self.search_type = ""
        self.tree_search.clear()
        self.search_block_parents.clear()

        # 保存当前展开状态
        self.target_tree.save_expanded_state()

        # 清空当前树和已加载目录记录
        self.target_tree.clear()
        self.target_tree.loaded_dirs.clear()

        # 重新加载所有原始项（懒加载）
        for path in self.original_tree_items:
            if os.path.exists(path) and path not in self.removed_items:
                self.load_tree_lazy(path)

        # 恢复展开状态
        self.target_tree.restore_expanded_state()

        # 更新监控
        self.update_watcher()

        self.log("搜索已重置，并刷新目录树")

    def log(self, s, color=None):
        # 修复日志颜色问题：只有错误操作使用红色，其他操作使用默认颜色
        # 替换、还原、删除备份操作使用指定颜色，其他操作使用默认颜色
        if color is None:
            # 检查是否为错误日志
            if "错误" in s or "失败" in s or "被占用" in s:
                color = QColor(Qt.red)
            else:
                # 非错误操作使用默认颜色（黑色）
                color = QColor(Qt.black)
        self.log_list.append_text(s, color)
    
    def test_log_colors(self):
        """测试日志颜色功能"""
        self.log("=== 开始日志颜色测试 ===")
        self.log("这是普通日志（应该显示黑色）")
        self.log("这是一个错误日志（应该显示红色）", QColor(Qt.red))
        self.log("这是包含'错误'关键词的日志（应该自动显示红色）")
        self.log("这是包含'失败'关键词的日志（应该自动显示红色）")
        self.log("这是包含'被占用'关键词的日志（应该自动显示红色）")
        self.log("这是正常的成功日志（应该显示黑色）")
        self.log("=== 日志颜色测试结束 ===")

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait(1000)
        event.accept()


# if __name__ == "__main__":
#     # 移除matplotlib依赖，解决中文显示问题通过PyQt5自身机制
#     
#     app = QApplication(sys.argv)
#     # 设置应用程序图标 - 使用内嵌资源
#     try:
#         app.setWindowIcon(QIcon(":/icon.ico"))
#     except Exception as e:
#         print(f"加载应用图标失败: {str(e)}")
#     
#     win = FileReplacerApp()
#     win.show()
#     sys.exit(app.exec_())
    