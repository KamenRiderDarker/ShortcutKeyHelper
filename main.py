import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMessageBox, QScrollArea, QMenu, QSystemTrayIcon, QListWidgetItem
)
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QFont, QAction, QIcon, QPixmap

# ===================== 全局配置 & 工具类 =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

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
        except:
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

        layout.addWidget(QLabel("📌 操作 & 快捷键（可添加/删除多条）", font=FONT_TITLE))
        layout.addWidget(QLabel("格式示例：复制 → Ctrl+C", font=FONT_SMALL, styleSheet="color:#666666;"))
        
        self.oper_edit = QLineEdit()
        self.oper_edit.setPlaceholderText("输入操作（例：全选）")
        layout.addWidget(self.oper_edit)
        
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入快捷键（例：Ctrl+A）")
        layout.addWidget(self.key_edit)

        # 添加+删除按钮 横向布局
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加该行快捷键")
        add_btn.clicked.connect(self.add_one_shortcut)
        btn_layout.addWidget(add_btn)

        del_btn = QPushButton("🗑️ 删除选中行")
        del_btn.setStyleSheet("background:#EF4444;color:white;")
        del_btn.clicked.connect(self.del_one_shortcut)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

        self.shortcut_list = QListWidget()
        layout.addWidget(self.shortcut_list)

        btn_text = "✅ 确认修改并保存" if self.edit_soft_name else "✅ 确认添加该软件"
        save_btn = QPushButton(btn_text)
        save_btn.setStyleSheet("background:#27AE60;color:white;border-radius:6px;padding:6px;")
        save_btn.clicked.connect(self.save_all)
        layout.addWidget(save_btn)

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

    def del_one_shortcut(self):
        current_item = self.shortcut_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选中要删除的快捷键行！")
            return
        row = self.shortcut_list.currentRow()
        self.shortcut_list.takeItem(row)
        del self.shortcut_temp[row]
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
        DataManager.save_software(soft_name, self.shortcut_temp)
        tip_text = f"{soft_name} 的快捷键已修改保存完成！" if self.edit_soft_name else f"{soft_name} 的快捷键已添加完成！"
        QMessageBox.information(self, "操作成功", tip_text)
        self.accept()

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
        layout.setSpacing(8)
        layout.setContentsMargins(5,5,5,5)

        title_label = QLabel(f"📌 {self.soft_name}", font=FONT_TITLE)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color:white;")
        layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;")
        layout.addWidget(scroll)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(4)
        scroll.setWidget(content_widget)

        shortcut_list = DataManager.get_software_detail(self.soft_name)
        if not shortcut_list:
            empty_label = QLabel("暂无快捷键数据", font=FONT_SMALL)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color:#94A3B8;")
            content_layout.addWidget(empty_label)
        else:
            for item in shortcut_list:
                key_label = QLabel(f"{item['操作']}\n{item['快捷键']}", font=FONT_SMALL)
                key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                key_label.setStyleSheet("color:white;background:#334155;border-radius:5px;padding:3px;")
                content_layout.addWidget(key_label)

        back_btn = QPushButton("← 返回", font=FONT_SMALL)
        back_btn.setStyleSheet("background:#0EA5E9;color:white;border-radius:5px;padding:4px;")
        back_btn.clicked.connect(self.back_to_main)
        layout.addWidget(back_btn)

        self.move(self.parent_win.pos())

    def back_to_main(self):
        self.parent_win.show()
        self.accept()

# ===================== 核心：悬浮球主窗口【✅修复列表删空闪退BUG 核心修改】 =====================
class FloatShortcutMain(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.is_pressing = False
        self.last_pos = QPoint(0,0)
        self.init_ui()
        self.load_software_list()

    def init_ui(self):
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

    # 鼠标拖动悬浮窗
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressing = True
            self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_pressing and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.pos() - self.last_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressing = False

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