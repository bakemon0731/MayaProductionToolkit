# =========================================
# Maya Production Toolkit
# Main Window
# =========================================
import os
import sys
import importlib
import traceback

import maya.cmds as cmds

# =========================================
# パス設定
# =========================================

SCRIPT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if SCRIPT_DIR not in sys.path:

    sys.path.insert(0, SCRIPT_DIR)


# =========================================
# ローカルモジュール
# =========================================

from mpt_ui.widgets.tool_card_widget import ToolCardWidget

from mpt_ui import tool_registry

from mpt_ui.tool_manager import ToolManager

try:

    from PySide6 import QtCore, QtWidgets

    from shiboken6 import wrapInstance

    WINDOW_FLAG = QtCore.Qt.WindowType.Window
    ALIGN_CENTER = QtCore.Qt.AlignmentFlag.AlignCenter
    STYLED_BACKGROUND = QtCore.Qt.WidgetAttribute.WA_StyledBackground

except ImportError:

    from PySide2 import QtCore, QtWidgets

    from shiboken2 import wrapInstance

    WINDOW_FLAG = QtCore.Qt.Window
    ALIGN_CENTER = QtCore.Qt.AlignCenter
    STYLED_BACKGROUND = QtCore.Qt.WA_StyledBackground



# =========================================
# 02. ウィンドウ管理
# =========================================

WINDOW = None

WINDOW_NAME = "MayaProductionToolkitWindow"


# =========================================
# 03. メインウィンドウクラス
# =========================================

class ProductionToolkitWindow(QtWidgets.QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setObjectName(
            WINDOW_NAME
        )

        self.setWindowTitle(
            "Maya Production Toolkit"
        )

        self.setWindowFlags(
            WINDOW_FLAG
        )

        self.resize(
            1400,
            900
        )

        self.setMinimumSize(
            1100,
            750
        )

        # ツール管理クラスを生成
        self.tool_manager = ToolManager()

        # いま開いているツールのページ(ホームのときはNone)
        self.tool_page = None

        # 画面を切り替えるための入れ物(QStackedWidget)
        # 0番目がホーム画面。ツールを開くと、その上にツールのページを重ねる。
        self.stack = QtWidgets.QStackedWidget()

        shell_layout = QtWidgets.QVBoxLayout(self)

        shell_layout.setContentsMargins(0, 0, 0, 0)

        shell_layout.addWidget(self.stack)

        # ホーム画面のページを作って登録
        self.home_page = self.build_home_page()

        self.stack.addWidget(self.home_page)

        self.stack.setCurrentWidget(self.home_page)

    # =====================================
    # 04. UI構築
    # =====================================

    def build_home_page(self):

        # ホーム画面は「1枚のページ(QWidget)」として作る。
        # ウィンドウそのものではないので、ツールのページと入れ替えられる。
        page = QtWidgets.QWidget()

        page.setObjectName("homePage")

        # ---------------------------------
        # メインレイアウト
        # ---------------------------------

        main_layout = QtWidgets.QVBoxLayout(page)

        main_layout.setContentsMargins(
            28, 24, 28, 24
        )

        main_layout.setSpacing(20)

        # ---------------------------------
        # HEADER
        # ---------------------------------

        eyebrow = QtWidgets.QLabel(
            "MAYA / PRODUCTION ENVIRONMENT"
        )

        eyebrow.setObjectName(
            "eyebrowLabel"
        )

        title = QtWidgets.QLabel(
            "MAYA PRODUCTION TOOLKIT"
        )

        title.setObjectName(
            "titleLabel"
        )

        description = QtWidgets.QLabel(
            "Artist Workflow & Automation System"
        )

        description.setObjectName(
            "descriptionLabel"
        )

        main_layout.addWidget(eyebrow)

        main_layout.addWidget(title)

        main_layout.addWidget(description)

        # ---------------------------------
        # 機能一覧の見出し
        # ---------------------------------

        section_title = QtWidgets.QLabel(
            "利用可能な機能"
        )

        section_title.setObjectName(
            "sectionTitle"
        )

        main_layout.addWidget(
            section_title
        )

        # ---------------------------------
        # スクロールエリア
        # ---------------------------------

        scroll_area = QtWidgets.QScrollArea()

        scroll_area.setWidgetResizable(True)

        scroll_area.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        scroll_area.setObjectName(
            "toolScrollArea"
        )

        main_layout.addWidget(
            scroll_area,
            1
        )

        # ---------------------------------
        # カード配置用Widget
        # ---------------------------------

        card_container = QtWidgets.QWidget()

        card_container.setObjectName(
            "cardContainer"
        )

        card_layout = QtWidgets.QGridLayout(
            card_container
        )

        card_layout.setContentsMargins(
            2, 2, 2, 12
        )

        card_layout.setSpacing(16)

        card_layout.setColumnStretch(0, 1)

        card_layout.setColumnStretch(1, 1)

        scroll_area.setWidget(
            card_container
        )

        # =================================
        # 05. 機能カード
        # =================================

        # tool_registryを最新の状態に更新
        importlib.reload(tool_registry)

        # 登録されている機能情報を取得
        tool_definitions = tool_registry.get_tool_definitions()

        # 機能情報を順番に読み込む
        for index, tool_info in enumerate(tool_definitions):

            # 2列で配置するための行・列を計算
            row = index // 2

            column = index % 2

            # カードを生成
            tool_card = ToolCardWidget(
                category=tool_info["category"],

                title=tool_info["title"],

                description=tool_info["description"],

                status=tool_info["status"],

                enabled=tool_info["enabled"]
            )

            # クリック時に共通の起動処理を呼び出す
            tool_card.clicked.connect(

                # カードをクリックしたとき、そのカードに対応する機能情報を launch_tool() に渡す
                lambda info=tool_info:
                    self.launch_tool(info)
            )

            # グリッドに配置
            card_layout.addWidget(

                tool_card,

                row,

                column
            )

        # ---------------------------------
        # 下部説明
        # ---------------------------------

        footer = QtWidgets.QLabel(
            "Maya Production Toolkit  |  "
            "Independent Production Tools"
        )

        footer.setObjectName(
            "footerLabel"
        )

        main_layout.addWidget(
            footer
        )

        # =================================
        # 06. デザイン
        # =================================

        # デザインはホームのページだけに適用する。
        # (ウィンドウ全体に適用すると、ツール側の見た目に混ざってしまう)
        page.setStyleSheet("""

            QWidget#homePage {
                background-color: #171D27;
            }

            QLabel#eyebrowLabel {
                color: #68C8DC;
                font-size: 11px;
                font-weight: bold;
            }

            QLabel#titleLabel {
                color: #F0F3F7;
                font-size: 27px;
                font-weight: bold;
            }

            QLabel#descriptionLabel {
                color: #AAB6C5;
                font-size: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid #354253;
            }

            QLabel#sectionTitle {
                color: #F0F3F7;
                font-size: 15px;
                font-weight: bold;
            }

            QLabel#footerLabel {
                color: #778697;
                font-size: 10px;
                padding-top: 8px;
                border-top: 1px solid #354253;
            }

            QScrollArea#toolScrollArea {
                background-color: #171D27;
                border: none;
            }

            QWidget#cardContainer {
                background-color: #171D27;
            }

            QFrame#toolCard {
                background-color: #222B35;
                border: 1px solid #354253;
                border-radius: 9px;
            }

            QLabel#toolCardCategory {
                color: #68C8DC;
                font-size: 10px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#toolCardTitle {
                color: #F0F3F7;
                font-size: 15px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#toolCardDescription {
                color: #AAB6C5;
                font-size: 11px;
                background: transparent;
            }

            QLabel#statusAvailable {
                color: #C5F2D9;
                background-color: #285D48;
                border: 1px solid #397D61;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
            }

            QLabel#statusPreparing {
                color: #FFE6A9;
                background-color: #725A2D;
                border: 1px solid #A9823D;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
            }

            QLabel#statusPlanned {
                color: #C5D0DB;
                background-color: #394653;
                border: 1px solid #586979;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
            }

            QPushButton#toolCardButton {
                background-color: #24647A;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }

            QPushButton#toolCardButton:hover {
                background-color: #32849C;
            }

            QPushButton#toolCardButton:pressed {
                background-color: #19495C;
            }

            QPushButton#toolCardButton:disabled {
                background-color: #354253;
                color: #7C8998;
            }

            QToolTip {
                background-color: #222B35;
                color: #F0F3F7;
                border: 1px solid #68C8DC;
                padding: 7px;
                border-radius: 4px;
            }

        """)

        return page

    # =====================================
    # 07. 機能起動
    # =====================================

    def launch_tool(self, tool_info):

        tool_title = (
            tool_info.get("title", "不明な機能")
            if isinstance(tool_info, dict)
            else "不明な機能"
        )

        try:

            # 新しいウィンドウは作らず、このウィンドウの中に開く
            self.open_tool(tool_info)

        except Exception:

            error_text = traceback.format_exc()

            print(error_text)

            QtWidgets.QMessageBox.critical(

                self,

                "機能起動エラー",

                tool_title
                + "を起動できませんでした。\n\n"
                + error_text

            )

    # =====================================
    # 08. ツールをこのウィンドウの中に開く
    # =====================================

    def open_tool(self, tool_info):

        tool_title = tool_info.get(
            "title",
            "不明な機能"
        )

        # すでに開いているツールがあれば、先に片付ける
        self.close_tool_page()

        # ツール本体のWidgetを作る(ここではまだ表示しない)
        # 作成に失敗したら例外になり、ホーム画面のまま残る
        tool_widget = self.tool_manager.create_widget(
            tool_info
        )

        # 背景色が確実に描かれるようにする
        tool_widget.setAttribute(
            STYLED_BACKGROUND,
            True
        )

        # ---------------------------------
        # ツール用のページ
        #   上: 「ホームに戻る」バー
        #   下: ツール本体
        # ---------------------------------

        page = QtWidgets.QWidget()

        page.setObjectName("toolHostPage")

        page.setStyleSheet(
            "QWidget#toolHostPage { background-color: #171D27; }"
        )

        page_layout = QtWidgets.QVBoxLayout(page)

        page_layout.setContentsMargins(0, 0, 0, 0)

        page_layout.setSpacing(0)

        # --- 上のバー ---

        bar = QtWidgets.QFrame()

        bar.setObjectName("hostBar")

        bar_layout = QtWidgets.QHBoxLayout(bar)

        bar_layout.setContentsMargins(16, 8, 16, 8)

        bar_layout.setSpacing(14)

        back_button = QtWidgets.QPushButton(
            "← ホームに戻る"
        )

        back_button.setObjectName("hostBackButton")

        back_button.setToolTip(
            "ツール選択画面(ホーム)に戻ります。"
        )

        # ボタンを押したら show_home() を呼ぶ
        back_button.clicked.connect(
            self.show_home
        )

        title_label = QtWidgets.QLabel(
            tool_title
        )

        title_label.setObjectName("hostTitleLabel")

        bar_layout.addWidget(back_button)

        bar_layout.addWidget(title_label)

        bar_layout.addStretch()

        # バーだけに適用するデザイン
        bar.setStyleSheet("""

            QFrame#hostBar {
                background-color: #1D2530;
                border-bottom: 1px solid #354253;
            }

            QPushButton#hostBackButton {
                background-color: #24647A;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                padding: 7px 14px;
                border: none;
                border-radius: 5px;
            }

            QPushButton#hostBackButton:hover {
                background-color: #32849C;
            }

            QPushButton#hostBackButton:pressed {
                background-color: #19495C;
            }

            QLabel#hostTitleLabel {
                color: #F0F3F7;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }

        """)

        page_layout.addWidget(bar)

        # ツール本体を、残りの領域いっぱいに配置
        page_layout.addWidget(tool_widget, 1)

        # ---------------------------------
        # ページを登録して、表示を切り替える
        # ---------------------------------

        self.tool_page = page

        self.stack.addWidget(page)

        self.stack.setCurrentWidget(page)

        self.setWindowTitle(
            "Maya Production Toolkit - " + tool_title
        )

    # =====================================
    # 09. ホーム画面に戻る
    # =====================================

    def show_home(self, checked=False):

        # 先にホームを表示してから、ツールのページを片付ける
        self.stack.setCurrentWidget(self.home_page)

        self.setWindowTitle(
            "Maya Production Toolkit"
        )

        self.close_tool_page()

    # =====================================
    # 10. 開いているツールのページを片付ける
    # =====================================

    def close_tool_page(self):

        if self.tool_page is None:

            return

        self.stack.removeWidget(self.tool_page)

        # すぐに消さず、安全なタイミングで削除する
        self.tool_page.deleteLater()

        self.tool_page = None


# =========================================
# 08. ホーム画面起動
# =========================================

WINDOW = None


def show_ui():

    global WINDOW

    # Mayaのメインウィンドウ取得用モジュール
    from maya import OpenMayaUI as omui
    
    maya_ptr = omui.MQtUtil.mainWindow()

    if not maya_ptr:

        raise RuntimeError(
            "Mayaのメインウィンドウを取得できません。"
        )

    maya_window = wrapInstance(
        int(maya_ptr),
        QtWidgets.QWidget
    )

    # -------------------------------------
    # 古いホーム画面を閉じる
    # -------------------------------------

    old_windows = maya_window.findChildren(
        QtWidgets.QWidget,
        WINDOW_NAME
    )

    for old_window in old_windows:

        old_window.close()

        old_window.deleteLater()

    WINDOW = ProductionToolkitWindow(
        maya_window
    )

    WINDOW.show()

    return WINDOW