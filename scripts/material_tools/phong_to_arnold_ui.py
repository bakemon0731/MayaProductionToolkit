import importlib
import traceback


# =========================================
# 00. Qtライブラリ読み込み
# =========================================

try:

    from PySide6 import QtCore, QtWidgets

    from shiboken6 import wrapInstance

    WINDOW_FLAG = QtCore.Qt.WindowType.Window

    WIDGET_FLAG = QtCore.Qt.WindowType.Widget

    ALIGN_CENTER = QtCore.Qt.AlignmentFlag.AlignCenter

    NO_EDIT_TRIGGERS = (
        QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
    )

    SELECT_ROWS = (
        QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
    )

    EXTENDED_SELECTION = (
        QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
    )

    RESIZE_TO_CONTENTS = (
        QtWidgets.QHeaderView.ResizeMode.ResizeToContents
    )

    STRETCH = (
        QtWidgets.QHeaderView.ResizeMode.Stretch
    )

    MESSAGE_YES = QtWidgets.QMessageBox.StandardButton.Yes

    MESSAGE_NO = QtWidgets.QMessageBox.StandardButton.No

except ImportError:

    from PySide2 import QtCore, QtWidgets

    from shiboken2 import wrapInstance

    WINDOW_FLAG = QtCore.Qt.Window

    WIDGET_FLAG = QtCore.Qt.Widget

    ALIGN_CENTER = QtCore.Qt.AlignCenter

    NO_EDIT_TRIGGERS = (
        QtWidgets.QAbstractItemView.NoEditTriggers
    )

    SELECT_ROWS = (
        QtWidgets.QAbstractItemView.SelectRows
    )

    EXTENDED_SELECTION = (
        QtWidgets.QAbstractItemView.ExtendedSelection
    )

    RESIZE_TO_CONTENTS = (
        QtWidgets.QHeaderView.ResizeToContents
    )

    STRETCH = (
        QtWidgets.QHeaderView.Stretch
    )

    MESSAGE_YES = QtWidgets.QMessageBox.Yes

    MESSAGE_NO = QtWidgets.QMessageBox.No


from maya import OpenMayaUI as omui

# Phongマテリアルの情報取得・変換モジュール
from material_tools import phong_to_arnold_converter


# =========================================
# 01. ウィンドウ管理
# =========================================

WINDOW = None

WINDOW_NAME = "PhongToArnoldConverterWindow"


# =========================================
# 02. UIクラス
# =========================================

class PhongToArnoldWindow(QtWidgets.QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setObjectName(
            WINDOW_NAME
        )

        self.setWindowTitle(
            "Phong → Arnold Converter"
        )

        self.setWindowFlags(
            WINDOW_FLAG
        )

        self.resize(
            1200,
            600
        )

        self.setMinimumSize(
            900,
            450
        )

        self.build_ui()

        # 起動時に一覧を取得
        self.refresh_material_list()

    # =====================================
    # 03. UI構築
    # =====================================

    def build_ui(self):

        # ---------------------------------
        # メインレイアウト
        # ---------------------------------

        main_layout = QtWidgets.QVBoxLayout(self)

        main_layout.setContentsMargins(
            24, 24, 24, 24
        )

        main_layout.setSpacing(16)

        # ---------------------------------
        # HEADER
        # ---------------------------------

        title = QtWidgets.QLabel(
            "Phong → Arnold Converter"
        )

        title.setObjectName(
            "titleLabel"
        )

        description = QtWidgets.QLabel(
            "Phongマテリアルの変換状態を確認し、"
            "Arnold Standard Surfaceへ変換します。"
        )

        description.setObjectName(
            "descriptionLabel"
        )

        main_layout.addWidget(title)

        main_layout.addWidget(description)

        # ---------------------------------
        # 検出件数
        # ---------------------------------

        self.summary_label = QtWidgets.QLabel(
            "マテリアル情報を取得しています..."
        )

        self.summary_label.setObjectName(
            "summaryLabel"
        )

        main_layout.addWidget(
            self.summary_label
        )

        # =================================
        # 変換対象一覧
        # =================================

        self.material_table = QtWidgets.QTableWidget()

        self.material_table.setObjectName(
            "materialTable"
        )

        # 列数を5列に設定
        self.material_table.setColumnCount(5)

        # 列の見出し
        self.material_table.setHorizontalHeaderLabels(
            [
                "Phongマテリアル",
                "変換状態",
                "Arnoldマテリアル",
                "Shading Group",
                "割り当て先"
            ]
        )

        # ---------------------------------
        # テーブルの操作設定
        # ---------------------------------

        # セルの直接編集を禁止
        self.material_table.setEditTriggers(
            NO_EDIT_TRIGGERS
        )

        # 行単位で選択
        self.material_table.setSelectionBehavior(
            SELECT_ROWS
        )

        # Ctrl・Shiftによる複数行選択
        self.material_table.setSelectionMode(
            EXTENDED_SELECTION
        )

        # ---------------------------------
        # テーブルの表示設定
        # ---------------------------------

        self.material_table.setAlternatingRowColors(
            True
        )

        self.material_table.setWordWrap(
            True
        )

        # 行番号を非表示
        self.material_table.verticalHeader().setVisible(
            False
        )

        # ---------------------------------
        # テーブルの列幅設定
        # ---------------------------------

        header = self.material_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            RESIZE_TO_CONTENTS
        )

        header.setSectionResizeMode(
            1,
            RESIZE_TO_CONTENTS
        )

        header.setSectionResizeMode(
            2,
            RESIZE_TO_CONTENTS
        )

        header.setSectionResizeMode(
            3,
            RESIZE_TO_CONTENTS
        )

        header.setSectionResizeMode(
            4,
            STRETCH
        )

        # ---------------------------------
        # 選択状態の変更を監視
        # ---------------------------------

        self.material_table.itemSelectionChanged.connect(
            self.update_convert_button_state
        )

        # テーブルを追加
        main_layout.addWidget(
            self.material_table,
            1
        )

        # =================================
        # ボタン
        # =================================

        button_layout = QtWidgets.QHBoxLayout()

        button_layout.addStretch()

        # ---------------------------------
        # 一覧更新ボタン
        # ---------------------------------

        self.refresh_button = QtWidgets.QPushButton(
            "一覧を更新"
        )

        self.refresh_button.setObjectName(
            "refreshButton"
        )

        self.refresh_button.clicked.connect(
            self.refresh_material_list
        )

        # ---------------------------------
        # 選択したマテリアルの変換ボタン
        # ---------------------------------

        self.convert_button = QtWidgets.QPushButton(
            "選択したマテリアルを変換"
        )

        self.convert_button.setObjectName(
            "convertButton"
        )

        self.convert_button.clicked.connect(
            self.convert_selected_material
        )

        self.convert_button.setEnabled(
            False
        )

        # ---------------------------------
        # 未変換マテリアルの一括変換ボタン
        # ---------------------------------

        self.convert_all_button = QtWidgets.QPushButton(
            "未変換を一括変換"
        )

        self.convert_all_button.setObjectName(
            "convertAllButton"
        )

        self.convert_all_button.clicked.connect(
            self.convert_all_unconverted_materials
        )

        self.convert_all_button.setEnabled(
            False
        )

        # ---------------------------------
        # 閉じるボタン
        # ---------------------------------

        self.close_button = QtWidgets.QPushButton(
            "閉じる"
        )

        self.close_button.setObjectName(
            "closeButton"
        )

        self.close_button.clicked.connect(
            self.close
        )

        # ---------------------------------
        # ボタンを配置
        # ---------------------------------

        button_layout.addWidget(
            self.refresh_button
        )

        button_layout.addWidget(
            self.convert_button
        )

        button_layout.addWidget(
            self.convert_all_button
        )

        button_layout.addWidget(
            self.close_button
        )

        main_layout.addLayout(
            button_layout
        )

        # =================================
        # デザイン
        # =================================

        self.setStyleSheet("""

            QWidget#PhongToArnoldConverterWindow {
                background-color: #171D27;
            }

            QLabel#titleLabel {
                color: #F0F3F7;
                font-size: 22px;
                font-weight: bold;
            }

            QLabel#descriptionLabel {
                color: #AAB6C5;
                font-size: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid #354253;
            }

            QLabel#summaryLabel {
                color: #68C8DC;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                background-color: #222B35;
                border: 1px solid #354253;
                border-radius: 5px;
            }

            QTableWidget#materialTable {
                background-color: #222B35;
                alternate-background-color: #283442;
                color: #D6E1EA;
                font-size: 12px;
                border: 1px solid #354253;
                gridline-color: #354253;
            }

            QTableWidget#materialTable::item {
                padding: 6px;
            }

            QTableWidget#materialTable::item:selected {
                background-color: #24647A;
                color: #FFFFFF;
            }

            QHeaderView::section {
                background-color: #354253;
                color: #F0F3F7;
                font-weight: bold;
                padding: 9px;
                border: none;
            }

            QPushButton#refreshButton {
                background-color: #24647A;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }

            QPushButton#refreshButton:hover {
                background-color: #32849C;
            }

            QPushButton#convertButton {
                background-color: #287B66;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }

            QPushButton#convertButton:hover {
                background-color: #34977D;
            }

            QPushButton#convertAllButton {
                background-color: #356B52;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }

            QPushButton#convertAllButton:hover {
                background-color: #468B69;
            }

            QPushButton#convertButton:disabled,
            QPushButton#convertAllButton:disabled {
                background-color: #354253;
                color: #778596;
            }

            QPushButton#closeButton {
                background-color: #354253;
                color: #D6E1EA;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }

            QPushButton#closeButton:hover {
                background-color: #46586B;
            }

            QToolTip {
                background-color: #222B35;
                color: #F0F3F7;
                border: 1px solid #68C8DC;
                padding: 7px;
                border-radius: 4px;
            }

        """)

    # =====================================
    # 04. 変換ボタンの有効・無効
    # =====================================

    def update_convert_button_state(self):

        """
        マテリアルが選択されている場合だけ
        選択変換ボタンを有効にする。
        """

        selected_rows = (
            self.material_table
            .selectionModel()
            .selectedRows()
        )

        has_selection = len(selected_rows) > 0

        self.convert_button.setEnabled(
            has_selection
        )

    # =====================================
    # 05. Phongマテリアル一覧の更新
    # =====================================

    def refresh_material_list(self):

        try:

            # ---------------------------------
            # Converterモジュールを再読み込み
            # ---------------------------------

            importlib.reload(
                phong_to_arnold_converter
            )

            # ---------------------------------
            # Phongマテリアル情報を取得
            # ---------------------------------

            material_infos = (
                phong_to_arnold_converter
                .get_phong_material_info()
            ) or []

            # ---------------------------------
            # 現在の一覧をクリア
            # ---------------------------------

            self.material_table.setRowCount(0)

            # =================================
            # 変換状態を取得
            # =================================

            conversion_info = {}

            # 同じPhongを何度も検索しない
            for info in material_infos:

                material = info.get(
                    "material"
                )

                if not material:

                    continue

                if material in conversion_info:

                    continue

                # 対応するArnoldマテリアルを検索
                arnold_material = (
                    phong_to_arnold_converter
                    .find_converted_arnold_material(
                        material
                    )
                )

                if arnold_material:

                    conversion_info[material] = {

                        "status": "変換済み",

                        "arnold_material": arnold_material

                    }

                else:

                    conversion_info[material] = {

                        "status": "未変換",

                        "arnold_material": "なし"

                    }

            # =================================
            # 取得した情報をテーブルに追加
            # =================================

            for info in material_infos:

                material = info.get(
                    "material",
                    "不明"
                )

                shading_engine = info.get(
                    "shading_engine"
                )

                members = info.get(
                    "members",
                    []
                ) or []

                # ---------------------------------
                # 変換状態を取得
                # ---------------------------------

                material_conversion = conversion_info.get(
                    material,
                    {
                        "status": "未変換",
                        "arnold_material": "なし"
                    }
                )

                status_text = material_conversion.get(
                    "status"
                )

                arnold_text = material_conversion.get(
                    "arnold_material"
                )

                # ---------------------------------
                # 表示する文字列を準備
                # ---------------------------------

                shading_engine_text = (
                    shading_engine
                    if shading_engine
                    else "なし"
                )

                members_text = (
                    "\n".join(
                        str(member)
                        for member in members
                    )
                    if members
                    else "割り当てなし"
                )

                values = [

                    material,

                    status_text,

                    arnold_text,

                    shading_engine_text,

                    members_text

                ]

                # ---------------------------------
                # テーブルに新しい行を追加
                # ---------------------------------

                row = self.material_table.rowCount()

                self.material_table.insertRow(row)

                for column, value in enumerate(values):

                    item = QtWidgets.QTableWidgetItem(
                        str(value)
                    )

                    # ---------------------------------
                    # 中央揃え
                    # ---------------------------------

                    if column in (1, 2):

                        item.setTextAlignment(
                            ALIGN_CENTER
                        )

                    self.material_table.setItem(
                        row,
                        column,
                        item
                    )

            # =================================
            # 検出件数を集計
            # =================================

            material_count = len(conversion_info)

            converted_count = sum(

                1

                for info in conversion_info.values()

                if info["status"] == "変換済み"

            )

            unconverted_count = (
                material_count - converted_count
            )

            info_count = len(material_infos)

            # ---------------------------------
            # 検出件数を表示
            # ---------------------------------

            self.summary_label.setText(

                "Phong: {}件　｜　変換済み: {}件"
                "　｜　未変換: {}件　｜　割り当て情報: {}件".format(

                    material_count,

                    converted_count,

                    unconverted_count,

                    info_count

                )

            )

            # ---------------------------------
            # テーブルの表示サイズを調整
            # ---------------------------------

            self.material_table.resizeRowsToContents()

            # ---------------------------------
            # Phongが見つからなかった場合
            # ---------------------------------

            if material_count == 0:

                self.summary_label.setText(
                    "Phongマテリアルは見つかりませんでした。"
                )

            # ---------------------------------
            # 選択状態を解除
            # ---------------------------------

            self.material_table.clearSelection()

            self.convert_button.setEnabled(
                False
            )

            # ---------------------------------
            # 未変換が存在する場合だけ
            # 一括変換ボタンを有効にする
            # ---------------------------------

            self.convert_all_button.setEnabled(
                unconverted_count > 0
            )

            print(
                "Phongマテリアル一覧を更新しました。"
            )

        except Exception as error:

            error_text = traceback.format_exc()

            print(error_text)

            self.summary_label.setText(
                "マテリアル情報の取得に失敗しました。"
            )

            self.convert_button.setEnabled(
                False
            )

            self.convert_all_button.setEnabled(
                False
            )

            QtWidgets.QMessageBox.critical(

                self,

                "取得エラー",

                "Phongマテリアル情報を取得できませんでした。\n\n"
                + str(error)

            )

    # =====================================
    # 06. 選択されたPhongマテリアルを取得
    # =====================================

    def get_selected_phong_materials(self):

        """
        テーブルで選択されたPhongマテリアルを取得する。

        複数Shading Groupによる重複も排除する。
        """

        selected_rows = (
            self.material_table
            .selectionModel()
            .selectedRows()
        )

        phong_materials = []

        for index in selected_rows:

            row = index.row()

            item = self.material_table.item(
                row,
                0
            )

            if not item:

                continue

            material = item.text()

            if material and material not in phong_materials:

                phong_materials.append(
                    material
                )

        return phong_materials

    # =====================================
    # 07. 未変換Phongマテリアルを取得
    # =====================================

    def get_unconverted_phong_materials(self):

        """
        テーブルから未変換のPhongマテリアルを取得する。

        同じPhongが複数行に表示されていても
        一度だけ取得する。
        """

        phong_materials = []

        for row in range(
            self.material_table.rowCount()
        ):

            material_item = self.material_table.item(
                row,
                0
            )

            status_item = self.material_table.item(
                row,
                1
            )

            if not material_item or not status_item:

                continue

            material = material_item.text()

            status = status_item.text()

            # 未変換だけを対象にする
            if status != "未変換":

                continue

            # 重複を防止
            if material not in phong_materials:

                phong_materials.append(
                    material
                )

        return phong_materials

    # =====================================
    # 08. 選択したマテリアルを変換
    # =====================================

    def convert_selected_material(self):

        """
        選択されたPhongマテリアルを変換する。
        """

        phong_materials = (
            self.get_selected_phong_materials()
        )

        self.execute_conversion(
            phong_materials,
            "選択したマテリアルの変換"
        )

    # =====================================
    # 09. 未変換マテリアルを一括変換
    # =====================================

    def convert_all_unconverted_materials(self):

        """
        シーン内の未変換Phongマテリアルを
        すべて変換する。
        """

        phong_materials = (
            self.get_unconverted_phong_materials()
        )

        self.execute_conversion(
            phong_materials,
            "未変換マテリアルの一括変換"
        )

    # =====================================
    # 10. 共通変換処理
    # =====================================

    def execute_conversion(
        self,
        phong_materials,
        operation_name
    ):

        """
        複数のPhongマテリアルを変換する。

        選択変換と一括変換の両方から呼び出す。
        """

        try:

            # ---------------------------------
            # 変換対象がない場合
            # ---------------------------------

            if not phong_materials:

                QtWidgets.QMessageBox.information(

                    self,

                    "変換対象なし",

                    "変換対象のPhongマテリアルがありません。"

                )

                return

            # ---------------------------------
            # 確認ダイアログ
            # ---------------------------------

            material_count = len(
                phong_materials
            )

            material_list = "\n".join(

                "- " + material

                for material in phong_materials[:10]

            )

            if material_count > 10:

                material_list += (

                    "\n...ほか {} 件".format(

                        material_count - 10

                    )

                )

            confirmation_message = (

                "{}を実行しますか？\n\n".format(
                    operation_name
                )

                + "対象: {}件\n\n".format(
                    material_count
                )

                + material_list

            )

            answer = QtWidgets.QMessageBox.question(

                self,

                "変換確認",

                confirmation_message,

                MESSAGE_YES | MESSAGE_NO

            )

            if answer != MESSAGE_YES:

                return

            # =================================
            # Converterモジュールの再読み込み
            # =================================

            importlib.reload(
                phong_to_arnold_converter
            )

            # =================================
            # 複数マテリアルの変換
            # =================================

            result = (

                phong_to_arnold_converter
                .auto_convert_phong_to_arnold(
                    phong_materials
                )

            )

            # =================================
            # 集計情報を取得
            # =================================

            summary = result.get(
                "summary",
                {}
            )

            success_count = summary.get(
                "success",
                0
            )

            skipped_count = summary.get(
                "skipped",
                0
            )

            error_count = summary.get(
                "errors",
                0
            )

            # =================================
            # 個別結果を整理
            # =================================

            detail_lines = []

            conversion_results = result.get(
                "results",
                []
            )

            for item in conversion_results:

                material = item.get(
                    "material",
                    "不明"
                )

                status = item.get(
                    "status",
                    "不明"
                )

                arnold_material = item.get(
                    "arnold_material"
                )

                status_label = {

                    "OK": "成功",

                    "SKIP": "スキップ",

                    "ERROR": "エラー"

                }.get(
                    status,
                    status
                )

                detail = "[{}] {}".format(
                    status_label,
                    material
                )

                if arnold_material:

                    detail += "\n    Arnold: {}".format(
                        arnold_material
                    )

                detail_lines.append(
                    detail
                )

            # =================================
            # 結果メッセージを作成
            # =================================

            result_message = (

                "変換処理が完了しました。\n\n"

                "対象: {}件\n"
                "成功: {}件\n"
                "スキップ: {}件\n"
                "エラー: {}件"

            ).format(

                material_count,

                success_count,

                skipped_count,

                error_count

            )

            # ---------------------------------
            # 個別結果を追加
            # ---------------------------------

            if detail_lines:

                display_details = detail_lines[:20]

                result_message += (

                    "\n\n===== 個別結果 =====\n\n"

                    + "\n\n".join(
                        display_details
                    )

                )

                if len(detail_lines) > 20:

                    result_message += (

                        "\n\n...ほか {} 件".format(

                            len(detail_lines) - 20

                        )

                    )

            # =================================
            # 結果を表示
            # =================================

            if error_count > 0:

                QtWidgets.QMessageBox.warning(

                    self,

                    "変換結果",

                    result_message

                )

            else:

                QtWidgets.QMessageBox.information(

                    self,

                    "変換結果",

                    result_message

                )

            # =================================
            # 変換後に一覧を更新
            # =================================

            self.refresh_material_list()

        except Exception as error:

            error_text = traceback.format_exc()

            print(error_text)

            QtWidgets.QMessageBox.critical(

                self,

                "変換処理エラー",

                "マテリアルの変換中にエラーが発生しました。\n\n"
                + str(error)

            )


# =========================================
# 11. UI起動
# =========================================

def show_ui():

    global WINDOW

    # -------------------------------------
    # Mayaのメインウィンドウを取得
    # -------------------------------------

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
    # 古いウィンドウを閉じる
    # -------------------------------------

    old_windows = maya_window.findChildren(
        QtWidgets.QWidget,
        WINDOW_NAME
    )

    for old_window in old_windows:

        old_window.close()

        old_window.deleteLater()

    WINDOW = None

    # -------------------------------------
    # 新しいウィンドウを生成
    # -------------------------------------

    WINDOW = PhongToArnoldWindow(
        maya_window
    )

    WINDOW.show()

    return WINDOW


# =========================================
# 12. ホーム画面に組み込む場合
# =========================================

def create_widget(parent=None):

    """ツール本体のWidgetを作って返す(表示はしない)。"""

    global WINDOW

    widget = PhongToArnoldWindow(parent)

    # PhongToArnoldWindowは、作られた時点で
    # 「独立したウィンドウ」の設定になっている。
    # ホーム画面の中に置くため、通常のWidgetに戻す。
    widget.setWindowFlags(
        WIDGET_FLAG
    )

    WINDOW = widget

    return widget