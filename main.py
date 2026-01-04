import sys
import json
import os
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QWidget, QDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMessageBox, QScrollArea, QMenu, QSystemTrayIcon, QListWidgetItem
)
from PyQt6.QtCore import Qt, QPoint, QSize, QEvent
from PyQt6.QtGui import QFont, QAction, QIcon, QPixmap, QCursor

# ===================== 全局配置 & 工具类 =====================
# 修复打包后路径问题
if getattr(sys, 'frozen', False):
    # 运行在打包后的环境中
    if sys.platform.startswith('win'):
        # Windows系统获取实际执行路径
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        buf = ctypes.create_unicode_buffer(1024)
        kernel32.GetModuleFileNameW(None, buf, 1024)
        BASE_DIR = os.path.dirname(buf.value)
    else:
        # 其他系统
        BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 正常开发环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
# 确保data目录存在
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR)
    except Exception as e:
        print(f"创建data目录失败: {e}")

# 固定尺寸：宽100px，高200px，添加软件文字完全显示
FLOAT_WIN_WIDTH = 100
FLOAT_WIN_HEIGHT = 200

# 字体配置 - Windows中文完美适配
FONT_NORMAL = QFont("微软雅黑", 9)
FONT_SMALL = QFont("微软雅黑", 8)
FONT_TITLE = QFont("微软雅黑", 10, QFont.Weight.Bold)

# ===================== 数据持久化工具类【单软件单文件，JSON格式】 =====================
class DataManager:
    @staticmethod
    def save_software(soft_name, shortcut_list):
        if not soft_name.strip():
            return False
        # 过滤Windows文件名非法字符
        invalid_chars = r'\/:*?"<>|'
        for char in invalid_chars:
            soft_name = soft_name.replace(char, '_')
        file_name = f"{soft_name.strip()}.json"
        file_path = os.path.join(DATA_DIR, file_name)
        
        save_data = {
            "software_name": soft_name.strip(),
            "shortcut_list": shortcut_list
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False

    @staticmethod
    def get_all_software():
        soft_list = []
        if os.path.exists(DATA_DIR):
            for file in os.listdir(DATA_DIR):
                if file.endswith(".json"):
                    soft_list.append(os.path.splitext(file)[0])
        return soft_list

    @staticmethod
    def get_software_detail(soft_name):
        invalid_chars = r'\/:*?"<>|'
        for char in invalid_chars:
            soft_name = soft_name.replace(char, '_')
        file_name = f"{soft_name.strip()}.json"
        file_path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("shortcut_list", [])
        except:
            return []

    @staticmethod
    def delete_software(soft_name):
        """删除软件及对应本地JSON文件"""
        invalid_chars = r'\/:*?"<>|'
        for char in invalid_chars:
            soft_name = soft_name.replace(char, '_')
        file_name = f"{soft_name.strip()}.json"
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except:
                return False
        return False

# ===================== 弹窗窗口-添加/编辑软件快捷键【支持删除原有行】 =====================
class AddEditShortcutWindow(QDialog):
    def __init__(self, soft_name=None, shortcut_list=None, parent=None):
        super().__init__(parent)
        self.result = None
        self.shortcut_temp = shortcut_list if shortcut_list else []
        self.edit_soft_name = soft_name
        self.init_ui()
        # 编辑模式：回显数据
        if soft_name and self.shortcut_temp:
            self.soft_name_edit.setText(soft_name)
            self.soft_name_edit.setReadOnly(True)
            for item in self.shortcut_temp:
                self.shortcut_list.addItem(f"{item['操作']} → {item['快捷键']}")

    def init_ui(self):
        win_title = "编辑软件快捷键" if self.edit_soft_name else "添加软件 & 快捷键"
        self.setWindowTitle(win_title)
        self.setFixedSize(420, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setFont(FONT_NORMAL)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20,20,20,20)

        self.soft_name_edit = QLineEdit()
        self.soft_name_edit.setPlaceholderText("请输入软件名称（例：微信、PyCharm、Excel）")
        layout.addWidget(QLabel("📌 软件名称", font=FONT_TITLE))
        layout.addWidget(self.soft_name_edit)

        layout.addWidget(QLabel("📌 操作 & 快捷键（可添加/删除/编辑多条）", font=FONT_TITLE))
        layout.addWidget(QLabel("格式示例：复制 → Ctrl+C", font=FONT_SMALL, styleSheet="color:#666666;"))
        layout.addWidget(QLabel("双击列表项可编辑", font=FONT_SMALL, styleSheet="color:#666666;"))
        
        self.oper_edit = QLineEdit()
        self.oper_edit.setPlaceholderText("输入操作（例：全选）")
        layout.addWidget(self.oper_edit)
        
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入快捷键（例：Ctrl+A）")
        layout.addWidget(self.key_edit)

        # 添加+删除+更新按钮 横向布局
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加该行快捷键")
        add_btn.clicked.connect(self.add_one_shortcut)
        btn_layout.addWidget(add_btn)

        self.update_btn = QPushButton("🔄 更新该行快捷键")
        self.update_btn.setStyleSheet("background:#F59E0B;color:white;")
        self.update_btn.clicked.connect(self.update_one_shortcut)
        self.update_btn.setEnabled(False)
        btn_layout.addWidget(self.update_btn)

        del_btn = QPushButton("🗑️ 删除选中行")
        del_btn.setStyleSheet("background:#EF4444;color:white;")
        del_btn.clicked.connect(self.del_one_shortcut)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

        self.shortcut_list = QListWidget()
        self.shortcut_list.itemDoubleClicked.connect(self.edit_one_shortcut)
        layout.addWidget(self.shortcut_list)

        btn_text = "✅ 确认修改并保存" if self.edit_soft_name else "✅ 确认添加该软件"
        save_btn = QPushButton(btn_text)
        save_btn.setStyleSheet("background:#27AE60;color:white;border-radius:6px;padding:6px;")
        save_btn.clicked.connect(self.save_all)
        layout.addWidget(save_btn)

        # 记录当前编辑的行索引
        self.editing_index = -1

    def add_one_shortcut(self):
        oper = self.oper_edit.text().strip()
        key = self.key_edit.text().strip()
        if not oper or not key:
            QMessageBox.warning(self, "提示", "操作名称和快捷键都不能为空！")
            return
        self.shortcut_temp.append({"操作": oper, "快捷键": key})
        self.shortcut_list.addItem(f"{oper} → {key}")
        self.oper_edit.clear()
        self.key_edit.clear()
        # 重置编辑状态
        self.editing_index = -1
        self.update_btn.setEnabled(False)

    def edit_one_shortcut(self, item):
        # 获取当前选中项的索引
        self.editing_index = self.shortcut_list.row(item)
        if self.editing_index == -1:
            return
        
        # 解析当前项的内容
        current_text = item.text()
        if " → " in current_text:
            oper, key = current_text.split(" → ", 1)
            self.oper_edit.setText(oper.strip())
            self.key_edit.setText(key.strip())
            # 启用更新按钮，禁用添加按钮
            self.update_btn.setEnabled(True)

    def update_one_shortcut(self):
        if self.editing_index == -1:
            return
        
        oper = self.oper_edit.text().strip()
        key = self.key_edit.text().strip()
        if not oper or not key:
            QMessageBox.warning(self, "提示", "操作名称和快捷键都不能为空！")
            return
        
        # 更新数据和列表项
        self.shortcut_temp[self.editing_index] = {"操作": oper, "快捷键": key}
        self.shortcut_list.item(self.editing_index).setText(f"{oper} → {key}")
        
        # 清空输入框，重置编辑状态
        self.oper_edit.clear()
        self.key_edit.clear()
        self.editing_index = -1
        self.update_btn.setEnabled(False)
        
        QMessageBox.information(self, "成功", "已更新选中的快捷键！")

    def del_one_shortcut(self):
        current_item = self.shortcut_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选中要删除的快捷键行！")
            return
        row = self.shortcut_list.currentRow()
        self.shortcut_list.takeItem(row)
        del self.shortcut_temp[row]
        # 如果删除的是正在编辑的行，重置编辑状态
        if self.editing_index == row:
            self.editing_index = -1
            self.update_btn.setEnabled(False)
            self.oper_edit.clear()
            self.key_edit.clear()
        elif self.editing_index > row:
            # 如果删除的行在编辑行之前，调整编辑行索引
            self.editing_index -= 1
        QMessageBox.information(self, "成功", "已删除选中的快捷键！")

    def save_all(self):
        soft_name = self.soft_name_edit.text().strip()
        if not soft_name:
            QMessageBox.warning(self, "提示", "软件名称不能为空！")
            return
        if not self.shortcut_temp:
            QMessageBox.warning(self, "提示", "请至少保留一条快捷键！")
            return
        
        self.result = (soft_name, self.shortcut_temp)
        success = DataManager.save_software(soft_name, self.shortcut_temp)
        if success:
            tip_text = f"{soft_name} 的快捷键已修改保存完成！" if self.edit_soft_name else f"{soft_name} 的快捷键已添加完成！"
            QMessageBox.information(self, "操作成功", tip_text)
            self.accept()
        else:
            QMessageBox.warning(self, "保存失败", "无法保存快捷键数据，请检查权限或目录是否存在！")

# ===================== 弹窗窗口-软件操作选择【编辑/查看/删除】 =====================
class SoftwareOptionWindow(QDialog):
    def __init__(self, soft_name, parent=None):
        super().__init__(parent)
        self.soft_name = soft_name
        self.parent_win = parent
        self.opt_result = None
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(FLOAT_WIN_WIDTH, FLOAT_WIN_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:#1E293B;border-radius:10px;")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(8,20,8,20)

        title_label = QLabel(f"📌 {self.soft_name}", font=FONT_TITLE)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color:white;margin-bottom:10px;")
        layout.addWidget(title_label)

        view_btn = QPushButton("查看快捷键", font=FONT_NORMAL)
        view_btn.setStyleSheet("background:#0EA5E9;color:white;border-radius:6px;padding:6px;")
        view_btn.clicked.connect(lambda : self.set_result("view"))
        layout.addWidget(view_btn)

        edit_btn = QPushButton("编辑快捷键", font=FONT_NORMAL)
        edit_btn.setStyleSheet("background:#F59E0B;color:white;border-radius:6px;padding:6px;")
        edit_btn.clicked.connect(lambda : self.set_result("edit"))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("删除该软件", font=FONT_NORMAL)
        del_btn.setStyleSheet("background:#EF4444;color:white;border-radius:6px;padding:6px;")
        del_btn.clicked.connect(lambda : self.set_result("delete"))
        layout.addWidget(del_btn)

        self.move(self.parent_win.pos())

    def set_result(self, opt):
        if opt == "delete":
            confirm = QMessageBox.question(self, "确认删除", f"确定要删除【{self.soft_name}】及所有快捷键吗？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return
            if DataManager.delete_software(self.soft_name):
                QMessageBox.information(self, "成功", f"已删除【{self.soft_name}】")
            else:
                QMessageBox.warning(self, "失败", "删除失败，请重试！")
        
        self.opt_result = opt
        self.accept()

# ===================== 弹窗窗口-快捷键详情展示 =====================
class ShortcutDetailWindow(QDialog):
    def __init__(self, soft_name, parent=None):
        super().__init__(parent)
        self.soft_name = soft_name
        self.parent_win = parent
        self.is_pressing = False
        self.last_pos = QPoint(0,0)
        self.resizing = False  # 是否正在调整大小
        self.edge_size = 20  # 边缘检测区域大小，增大以提高可点击性
        self.init_ui()
        # 安装事件过滤器以处理鼠标事件
        self.installEventFilter(self)

    def init_ui(self):
        # 获取屏幕高度并计算最大高度为屏幕高度的2/3
        screen_geo = QApplication.primaryScreen().geometry()
        self.max_height = int(screen_geo.height() * 2 / 3)
        
        # 获取快捷键列表
        shortcut_list = DataManager.get_software_detail(self.soft_name)
        
        # 窗口宽度
        width = 250
        
        # 初始高度
        init_height = min(400, max(150, len(shortcut_list) * 40 + 100))
        # 确保初始高度不超过最大高度
        init_height = min(init_height, self.max_height)
        
        self.setMinimumSize(width, 150)  # 设置最小尺寸
        self.setMaximumSize(width, self.max_height)  # 设置最大尺寸为屏幕高度的2/3
        self.resize(width, init_height)  # 设置初始尺寸
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:#1E293B;border-radius:10px;")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10,10,10,10)

        title_label = QLabel(f"📌 {self.soft_name}", font=FONT_TITLE)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color:white;margin-bottom:5px;")
        layout.addWidget(title_label)

        # 添加滚动区域，支持内容过多时滚动
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;")
        layout.addWidget(scroll)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(5)
        content_layout.setContentsMargins(0,0,0,0)
        scroll.setWidget(content_widget)

        if not shortcut_list:
            empty_label = QLabel("暂无快捷键数据", font=FONT_SMALL)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color:#94A3B8;")
            content_layout.addWidget(empty_label)
        else:
            for item in shortcut_list:
                # 列表式展示：操作和快捷键在同一行，更紧凑
                key_label = QLabel(f"{item['操作']} → {item['快捷键']}", font=FONT_SMALL)
                key_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                key_label.setStyleSheet("color:white;background:#334155;border-radius:5px;padding:5px 8px;")
                content_layout.addWidget(key_label)

        # 按钮布局：返回、新增和收起按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setContentsMargins(0,0,0,0)
        
        back_btn = QPushButton("← 返回", font=FONT_SMALL)
        back_btn.setStyleSheet("background:#0EA5E9;color:white;border-radius:5px;padding:4px;")
        back_btn.clicked.connect(self.back_to_main)
        btn_layout.addWidget(back_btn)
        
        # 新增快捷键按钮
        new_btn = QPushButton("➕ 新增", font=FONT_SMALL)
        new_btn.setStyleSheet("background:#22C55E;color:white;border-radius:5px;padding:4px;")
        new_btn.clicked.connect(self.new_shortcut)
        btn_layout.addWidget(new_btn)
        
        collapse_btn = QPushButton("🔽 收起", font=FONT_SMALL)
        collapse_btn.setStyleSheet("background:#8B5CF6;color:white;border-radius:5px;padding:4px;")
        collapse_btn.clicked.connect(self.collapse_and_back)
        btn_layout.addWidget(collapse_btn)
        
        layout.addLayout(btn_layout)

        self.move(self.parent_win.pos())

    def back_to_main(self):
        self.parent_win.show()
        self.accept()
        
    def collapse_and_back(self):
        """收起主窗口并返回，确保在查看窗口位置收起"""
        # 将主窗口位置设置为当前查看窗口的位置
        self.parent_win.move(self.pos())
        # 然后收起主窗口
        self.parent_win.toggle_collapse()
        self.parent_win.show()
        self.accept()
        
    def new_shortcut(self):
        """新增快捷键"""
        # 获取当前软件的快捷键列表
        shortcut_list = DataManager.get_software_detail(self.soft_name)
        # 打开编辑窗口，传入当前软件名称和现有快捷键列表
        edit_win = AddEditShortcutWindow(self.soft_name, shortcut_list, self)
        # 如果编辑成功，刷新当前界面
        if edit_win.exec():
            self.refresh_ui()
    
    def refresh_ui(self):
        """刷新快捷键界面"""
        # 获取最新的快捷键列表
        shortcut_list = DataManager.get_software_detail(self.soft_name)
        
        # 清空现有内容
        content_widget = self.layout().itemAt(1).widget().widget()
        content_layout = content_widget.layout()
        # 清空所有现有控件
        while content_layout.count() > 0:
            item = content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 重新添加内容
        if not shortcut_list:
            empty_label = QLabel("暂无快捷键数据", font=FONT_SMALL)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color:#94A3B8;")
            content_layout.addWidget(empty_label)
        else:
            for item in shortcut_list:
                # 列表式展示：操作和快捷键在同一行，更紧凑
                key_label = QLabel(f"{item['操作']} → {item['快捷键']}", font=FONT_SMALL)
                key_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                key_label.setStyleSheet("color:white;background:#334155;border-radius:5px;padding:5px 8px;")
                content_layout.addWidget(key_label)
    
    # 鼠标事件处理 - 支持拖动和调整大小
    def mousePressEvent(self, event):
        # 检查是否在调整大小区域
        rect = self.rect()
        bottom_edge = rect.bottom() - self.edge_size
        top_edge = rect.top() + self.edge_size
        
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在底部或顶部边缘
            if event.pos().y() >= bottom_edge or event.pos().y() <= top_edge:
                self.resizing = True
                self.last_pos = event.pos()
                self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                event.accept()
                return
            
            # 否则处理拖动
            self.is_pressing = True
            self.last_pos = event.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.resizing:
            # 调整窗口大小
            delta = event.pos().y() - self.last_pos.y()
            new_height = self.height() + delta
            
            # 确保高度在最小和最大范围内
            if new_height >= self.minimumHeight() and new_height <= self.max_height:
                self.resize(self.width(), new_height)
                self.last_pos = event.pos()
            event.accept()
        elif self.is_pressing and event.buttons() == Qt.MouseButton.LeftButton:
            # 窗口拖动
            new_pos = self.pos() + event.pos() - self.last_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resizing:
                self.resizing = False
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            else:
                self.is_pressing = False
            event.accept()
    
    # 重写event方法，优先处理鼠标事件
    def event(self, event):
        # 处理鼠标移动事件，用于边缘检测
        if event.type() == QEvent.Type.MouseMove:
            rect = self.rect()
            bottom_edge = rect.bottom() - self.edge_size
            top_edge = rect.top() + self.edge_size
            
            if self.resizing:
                # 正在调整大小时，设置调整光标
                self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
            else:
                # 检查是否在边缘区域
                if event.pos().y() >= bottom_edge or event.pos().y() <= top_edge:
                    self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                else:
                    self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        # 处理鼠标按下事件
        elif event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                rect = self.rect()
                bottom_edge = rect.bottom() - self.edge_size
                top_edge = rect.top() + self.edge_size
                
                # 检查是否在底部或顶部边缘
                if event.pos().y() >= bottom_edge or event.pos().y() <= top_edge:
                    self.resizing = True
                    self.last_pos = event.pos()
                    self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                    event.accept()
                    return True
        # 处理鼠标释放事件
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton and self.resizing:
                self.resizing = False
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                event.accept()
                return True
        
        # 其他事件交给父类处理
        return super().event(event)
    
    # 事件过滤器 - 处理鼠标悬停时的光标变化
    def eventFilter(self, obj, event):
        # 确保鼠标移动事件被正确处理
        if event.type() == QEvent.Type.MouseMove:
            rect = self.rect()
            bottom_edge = rect.bottom() - self.edge_size
            top_edge = rect.top() + self.edge_size
            
            if not self.resizing:
                # 检查是否在边缘区域
                if event.pos().y() >= bottom_edge or event.pos().y() <= top_edge:
                    self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                    # 阻止事件继续传递，确保光标正确显示
                    return True
        return super().eventFilter(obj, event)

# ===================== 核心：悬浮球主窗口【✅修复列表删空闪退BUG 核心修改】 =====================
class FloatShortcutMain(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.is_pressing = False
        self.last_pos = QPoint(0,0)
        self.is_collapsed = False  # 收起状态标志
        self.last_state = "main"  # 记录最后状态：main或detail
        self.last_soft_name = None  # 记录最后查看的软件名称
        self.init_ui()
        self.load_software_list()
        # 安装事件过滤器，确保按钮事件不影响拖动
        self.collapse_btn.installEventFilter(self)

    def init_ui(self):
        # 初始展开状态的尺寸
        if self.is_collapsed:
            self.setFixedSize(30, 30)
        else:
            self.setFixedSize(QSize(FLOAT_WIN_WIDTH, FLOAT_WIN_HEIGHT))
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:#1E293B;border-radius:10px;")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5,5,5,5)

        # 收起/展开按钮
        self.collapse_btn = QPushButton("🔽 收起")
        self.collapse_btn.setStyleSheet("background:#8B5CF6;color:white;border-radius:5px;padding:3px;")
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        main_layout.addWidget(self.collapse_btn)

        self.add_btn = QPushButton("➕ 添加软件", font=FONT_TITLE)
        self.add_btn.setStyleSheet("background:#F97316;color:white;border-radius:8px;padding:5px;")
        self.add_btn.clicked.connect(self.open_add_window)
        main_layout.addWidget(self.add_btn)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索软件")
        self.search_edit.setFont(FONT_SMALL)
        self.search_edit.setStyleSheet("background:#334155;color:white;border-radius:5px;padding:2px;text-align:center;")
        self.search_edit.textChanged.connect(self.search_software)
        main_layout.addWidget(self.search_edit)

        self.exit_btn = QPushButton("❌ 退出程序", font=FONT_SMALL)
        self.exit_btn.setStyleSheet("background:#EF4444;color:white;border-radius:5px;padding:3px;")
        self.exit_btn.clicked.connect(self.exit_program)
        main_layout.addWidget(self.exit_btn)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border:none;")
        main_layout.addWidget(self.scroll_area)

        self.soft_list_widget = QWidget()
        self.soft_layout = QVBoxLayout(self.soft_list_widget)
        self.soft_layout.setSpacing(5)
        self.scroll_area.setWidget(self.soft_list_widget)

        self.move_to_right_edge()
        self.all_soft_list = DataManager.get_all_software()

    def toggle_collapse(self):
        """切换展开/收起状态"""
        # 保存当前位置（左上角坐标）
        current_pos = self.pos()
        
        self.is_collapsed = not self.is_collapsed
        
        if self.is_collapsed:
            # 收起状态：缩小为圆形，直接使用当前位置
            self.setFixedSize(30, 30)
            self.setStyleSheet("background:#1E293B;border-radius:15px;")
            
            # 隐藏所有控件，只显示一个简单的指示器
            self.add_btn.hide()
            self.search_edit.hide()
            self.exit_btn.hide()
            self.scroll_area.hide()
            self.collapse_btn.setText("⭕")
            self.collapse_btn.setStyleSheet("background:#1E293B;color:white;border-radius:15px;padding:0;")
            
            # 直接使用当前位置，不做调整
            self.move(current_pos)
        else:
            # 展开状态：恢复正常大小，直接使用当前位置
            self.setFixedSize(QSize(FLOAT_WIN_WIDTH, FLOAT_WIN_HEIGHT))
            self.setStyleSheet("background:#1E293B;border-radius:10px;")
            
            # 显示所有控件
            self.add_btn.show()
            self.search_edit.show()
            self.exit_btn.show()
            self.scroll_area.show()
            self.collapse_btn.setText("🔽 收起")
            self.collapse_btn.setStyleSheet("background:#8B5CF6;color:white;border-radius:5px;padding:3px;")
            
            # 重新加载软件列表，确保显示正确
            self.load_software_list()
            
            # 直接使用当前位置，不做调整
            self.move(current_pos)

    def move_to_right_edge(self):
        screen_geo = QApplication.primaryScreen().geometry()
        win_x = screen_geo.width() - self.width() - 10
        win_y = (screen_geo.height() - self.height()) // 2
        self.move(win_x, win_y)

    def load_software_list(self, filter_list=None):
        """✅ 核心修复BUG 重点：每次清空后动态创建空标签，永不复用已销毁控件"""
        # 清空所有现有控件
        for i in reversed(range(self.soft_layout.count())):
            widget_item = self.soft_layout.itemAt(i).widget()
            if widget_item:
                widget_item.deleteLater()

        # 重新读取最新数据
        self.all_soft_list = DataManager.get_all_software()
        soft_list = filter_list if filter_list else self.all_soft_list
        
        if not soft_list:
            # ✅ 关键修复：每次列表为空时，新建一个空状态标签，不是复用旧的
            empty_label = QLabel("暂无软件\n点击添加", font=FONT_SMALL)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color:#94A3B8;")
            self.soft_layout.addWidget(empty_label)
            return
        
        # 生成软件按钮
        for soft_name in soft_list:
            soft_btn = QPushButton(soft_name, font=FONT_SMALL)
            soft_btn.setStyleSheet("background:#3B82F6;color:white;border-radius:6px;padding:5px;")
            soft_btn.clicked.connect(lambda _, s=soft_name: self.open_software_option(s))
            self.soft_layout.addWidget(soft_btn)

    def search_software(self):
        keyword = self.search_edit.text().strip().lower()
        if not keyword:
            self.load_software_list()
            return
        filter_list = [name for name in self.all_soft_list if keyword in name.lower()]
        self.load_software_list(filter_list)

    def open_add_window(self):
        add_win = AddEditShortcutWindow(parent=self)
        if add_win.exec():
            if add_win.result:
                self.search_edit.clear()
                self.load_software_list()

    def open_software_option(self, soft_name):
        self.hide()
        opt_win = SoftwareOptionWindow(soft_name, self)
        if opt_win.exec():
            opt = opt_win.opt_result
            if opt == "view":
                # 记录查看状态
                self.last_state = "detail"
                self.last_soft_name = soft_name
                detail_win = ShortcutDetailWindow(soft_name, self)
                detail_win.exec()
            elif opt == "edit":
                shortcut_list = DataManager.get_software_detail(soft_name)
                edit_win = AddEditShortcutWindow(soft_name, shortcut_list, self)
                if edit_win.exec():
                    self.search_edit.clear()
                    self.load_software_list()
            elif opt == "delete":
                self.search_edit.clear()
                self.load_software_list()
        self.show()

    def exit_program(self):
        confirm = QMessageBox.question(self, "确认退出", "确定要退出快捷键助手吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.app.quit()

    # 鼠标拖动悬浮窗 - 确保在所有状态下都能正常工作
    def mousePressEvent(self, event):
        # 确保所有状态下都能捕获鼠标按下事件
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressing = True
            self.last_pos = event.pos()
            # 阻止事件传递给子控件
            event.accept()

    def mouseMoveEvent(self, event):
        # 确保所有状态下都能捕获鼠标移动事件
        if self.is_pressing and event.buttons() == Qt.MouseButton.LeftButton:
            # 计算新位置
            new_pos = self.pos() + event.pos() - self.last_pos
            self.move(new_pos)
            # 阻止事件传递给子控件
            event.accept()

    def mouseReleaseEvent(self, event):
        # 确保所有状态下都能捕获鼠标释放事件
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressing = False
            # 阻止事件传递给子控件
            event.accept()
    
    # 确保子控件的鼠标事件不会干扰主窗口拖动
    def eventFilter(self, obj, event):
        if obj == self.collapse_btn:
            if event.type() == event.Type.MouseButtonPress:
                # 直接调用主窗口的鼠标按下事件
                self.mousePressEvent(event)
                return True
            elif event.type() == event.Type.MouseMove:
                # 直接调用主窗口的鼠标移动事件
                self.mouseMoveEvent(event)
                return True
            elif event.type() == event.Type.MouseButtonRelease:
                # 先处理主窗口的鼠标释放事件
                self.mouseReleaseEvent(event)
                # 如果是点击（移动距离很小），则触发按钮的点击事件
                if (event.pos() - self.last_pos).manhattanLength() < 5:
                    self.toggle_collapse()
                return True
        return super().eventFilter(obj, event)

# ===================== 系统托盘图标【✅修复无图标警告】 =====================
def init_system_tray(app, main_win):
    tray_icon = QSystemTrayIcon(app)
    # ✅ 修复警告：改用PyQt6内置的默认图标，所有Windows环境都能识别，无警告
    tray_icon.setIcon(QIcon(QPixmap(16,16))) 
    tray_icon.setToolTip("快捷键助手 - 后台运行中")

    tray_menu = QMenu()
    show_action = QAction("显示悬浮窗", app)
    show_action.triggered.connect(main_win.show)
    tray_menu.addAction(show_action)

    hide_action = QAction("隐藏悬浮窗", app)
    hide_action.triggered.connect(main_win.hide)
    tray_menu.addAction(hide_action)

    tray_menu.addSeparator()

    exit_action = QAction("退出程序", app)
    exit_action.triggered.connect(app.quit)
    tray_menu.addAction(exit_action)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    tray_icon.activated.connect(lambda reason: main_win.show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    return tray_icon

# ===================== 程序入口 =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("微软雅黑"))
    app.setQuitOnLastWindowClosed(False)

    float_app = FloatShortcutMain(app)
    float_app.show()

    tray = init_system_tray(app, float_app)

    sys.exit(app.exec())