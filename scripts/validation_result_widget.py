import re

# =========================================
# 00. Qtライブラリ読み込み
# =========================================

try:

    from PySide6 import QtCore, QtWidgets

except ImportError:

    from PySide2 import QtCore, QtWidgets


# =========================================
# 01. Qtバージョン互換処理
# =========================================

def get_qt_enum(owner, modern_group, value_name, legacy_name):

    group = getattr(
        owner,
        modern_group,
        None
    )

    if group is not None:

        return getattr(
            group,
            value_name
        )

    return getattr(
        owner,
        legacy_name
    )


ALIGN_CENTER = get_qt_enum(
    QtCore.Qt,
    "AlignmentFlag",
    "AlignCenter",
    "AlignCenter"
)

NO_EDIT_TRIGGERS = get_qt_enum(
    QtWidgets.QAbstractItemView,
    "EditTrigger",
    "NoEditTriggers",
    "NoEditTriggers"
)

SELECT_ROWS = get_qt_enum(
    QtWidgets.QAbstractItemView,
    "SelectionBehavior",
    "SelectRows",
    "SelectRows"
)

SINGLE_SELECTION = get_qt_enum(
    QtWidgets.QAbstractItemView,
    "SelectionMode",
    "SingleSelection",
    "SingleSelection"
)

RESIZE_TO_CONTENTS = get_qt_enum(
    QtWidgets.QHeaderView,
    "ResizeMode",
    "ResizeToContents",
    "ResizeToContents"
)

RESIZE_STRETCH = get_qt_enum(
    QtWidgets.QHeaderView,
    "ResizeMode",
    "Stretch",
    "Stretch"
)


# =========================================
# 02. ステータスバッジ
# =========================================

class StatusBadgeLabel(QtWidgets.QLabel):

    STATUS_STYLES = {

        "OK": {
            "background": "#285D48",
            "color": "#C5F2D9",
            "border": "#397D61"
        },

        "NG": {
            "background": "#713B40",
            "color": "#FFD6D9",
            "border": "#A44C55"
        },

        "WARNING": {
            "background": "#725A2D",
            "color": "#FFE6A9",
            "border": "#A9823D"
        },

        "ERROR": {
            "background": "#762D36",
            "color": "#FFE0E2",
            "border": "#B34855"
        },

        "SKIP": {
            "background": "#394653",
            "color": "#C5D0DB",
            "border": "#586979"
        }

    }

    STATUS_DESCRIPTIONS = {

        "OK": "検証に合格しました。",

        "NG": "命名規則などの設定に違反しています。",

        "WARNING": "問題の可能性があります。内容を確認してください。",

        "ERROR": "検証または処理中にエラーが発生しました。",

        "SKIP": "この項目は検証対象外です。"

    }

    def __init__(self, status, parent=None):

        super().__init__(
            status,
            parent
        )

        style = self.STATUS_STYLES.get(
            status,
            self.STATUS_STYLES["SKIP"]
        )

        self.setAlignment(
            ALIGN_CENTER
        )

        self.setFixedHeight(23)

        self.setMinimumWidth(65)

        self.setStyleSheet("""
            QLabel {
                background-color: %s;
                color: %s;
                border: 1px solid %s;
                border-radius: 11px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }
        """ % (
            style["background"],
            style["color"],
            style["border"]
        ))

        self.setToolTip(
            self.STATUS_DESCRIPTIONS.get(
                status,
                "不明なステータスです。"
            )
        )


# =========================================
# 03. 検証結果表示ウィジェット
# =========================================

class StatusResultWidget(QtWidgets.QWidget):

    # 修正ボタンが押されたとき、親画面へ対象行の情報を通知する。
    # 実際のMaya修正処理は、このシグナルを受け取る側で実装する。
    fix_requested = QtCore.Signal(dict)

    # 検証項目名と、自動修正処理を識別するキーの対応表。
    # ここに登録した項目だけが「修正」ボタンの対象になる。
    FIXABLE_CHECKS = {
        "命名規則": "rename",
    }

    VALID_STATUSES = {
        "OK",
        "NG",
        "WARNING",
        "ERROR",
        "SKIP"
    }

    def __init__(self, parent=None):

        super().__init__(parent)

        self.raw_text = ""

        # =================================
        # メインレイアウト
        # =================================

        main_layout = QtWidgets.QVBoxLayout(self)

        main_layout.setContentsMargins(
            0, 0, 0, 0
        )

        main_layout.setSpacing(8)

        # =================================
        # 01. サマリー表示
        # =================================

        self.summary_label = QtWidgets.QLabel(
            "検証結果はまだありません。"
        )

        self.summary_label.setObjectName(
            "resultSummaryLabel"
        )

        main_layout.addWidget(
            self.summary_label
        )

        # =================================
        # 02. 検証結果テーブル
        # =================================

        self.result_table = QtWidgets.QTableWidget()

        self.result_table.setObjectName(
            "statusResultTable"
        )

        # 既存の4列に「修正」列を追加する。
        self.result_table.setColumnCount(5)

        self.result_table.setHorizontalHeaderLabels([
            "オブジェクト",
            "検証項目",
            "状態",
            "内容",
            "修正"
        ])

        self.result_table.verticalHeader().setVisible(
            False
        )

        self.result_table.setEditTriggers(
            NO_EDIT_TRIGGERS
        )

        self.result_table.setSelectionBehavior(
            SELECT_ROWS
        )

        self.result_table.setSelectionMode(
            SINGLE_SELECTION
        )

        self.result_table.setWordWrap(True)

        self.result_table.setShowGrid(False)

        self.result_table.setAlternatingRowColors(
            True
        )

        header = self.result_table.horizontalHeader()

        # 「内容」列だけを余った幅に合わせる。
        # 最終列をStretchにすると修正ボタン列が横に広がるため、
        # 最終列はResizeToContentsにする。
        header.setStretchLastSection(False)

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
            RESIZE_STRETCH
        )

        header.setSectionResizeMode(
            4,
            RESIZE_TO_CONTENTS
        )

        self.result_table.setColumnWidth(
            0, 120
        )

        self.result_table.setColumnWidth(
            1, 125
        )

        self.result_table.setColumnWidth(
            2, 80
        )

        self.result_table.setColumnWidth(
            4, 76
        )

        main_layout.addWidget(
            self.result_table,
            3
        )

        # =================================
        # 03. 詳細ログ見出し
        # =================================

        detail_label = QtWidgets.QLabel(
            "実行ログ / 詳細情報"
        )

        detail_label.setObjectName(
            "resultDetailLabel"
        )

        main_layout.addWidget(
            detail_label
        )

        # =================================
        # 04. 詳細ログ
        # =================================

        self.log_view = QtWidgets.QPlainTextEdit()

        self.log_view.setObjectName(
            "resultLogView"
        )

        self.log_view.setReadOnly(True)

        self.log_view.setPlaceholderText(
            "検証結果の詳細がここに表示されます。"
        )

        self.log_view.setMinimumHeight(
            130
        )

        main_layout.addWidget(
            self.log_view,
            2
        )

    # =====================================
    # 04. 検証結果の解析
    # =====================================

    def parse_results(self, text):

        rows = []

        current_object = "不明"

        current_check = "不明"

        current_row = None

        lines = text.splitlines()

        for line in lines:

            stripped = line.strip()

            if not stripped:

                current_row = None

                continue

            # ---------------------------------
            # 見出しの解析
            # ---------------------------------

            if stripped.startswith("====="):

                heading = stripped.strip(
                    "= "
                )

                current_row = None

                # 厳格チェックの「判定」欄は、上の検証結果の
                # 再掲(NGだけの一覧)なので、表には登録しない。
                # (登録すると同じNGが二重に数えられる)
                if heading == "厳格チェック判定":

                    break

                if heading == "修正後の再検証結果":

                    current_check = "再検証"

                elif heading.endswith("チェック結果"):

                    current_check = heading.replace(
                        "チェック結果",
                        ""
                    ).strip()

                elif heading.endswith("の結果"):

                    current_check = heading.replace(
                        "の結果",
                        ""
                    ).strip()

                continue

            # ---------------------------------
            # 再検証結果の一行形式
            # ---------------------------------

            match = re.match(
                r"対象:\s*(.*?)\s*\|\s*検証:\s*(.*?)\s*\|\s*状態:\s*(OK|NG|WARNING|ERROR|SKIP)\s*\|\s*内容:\s*(.*)",
                stripped
            )

            if match:

                rows.append({

                    "object": match.group(1),

                    "check": match.group(2),

                    "status": match.group(3),

                    "detail": match.group(4)

                })

                current_row = len(rows) - 1

                continue

            # ---------------------------------
            # オブジェクト名
            # ---------------------------------

            if stripped.startswith("オブジェクト:"):

                current_object = stripped.replace(
                    "オブジェクト:",
                    "",
                    1
                ).strip()

                current_row = None

                continue

            if stripped.startswith("対象:"):

                current_object = stripped.replace(
                    "対象:",
                    "",
                    1
                ).strip()

                current_row = None

                continue

            # ---------------------------------
            # 検証項目名の行
            # ---------------------------------
            # 「検証: Construction History」のような行で
            # 検証項目名を更新する。これがないと、次の「状態:」の行が
            # 直前の項目名(例: UV)のまま登録されてしまう。

            if stripped.startswith("検証:"):

                current_check = stripped.split(
                    ":",
                    1
                )[1].strip()

                current_row = None

                continue

            # ---------------------------------
            # [OK] 検証項目形式
            # ---------------------------------

            match = re.match(
                r"^\[(OK|NG|WARNING|ERROR|SKIP)\]\s*(.*)$",
                stripped
            )

            if match:

                status = match.group(1)

                check_name = match.group(2).strip()

                rows.append({

                    "object": current_object,

                    "check": check_name,

                    "status": status,

                    "detail": ""

                })

                current_check = check_name

                current_row = len(rows) - 1

                continue

            # ---------------------------------
            # 結果：OK / 状態：OK
            # ---------------------------------

            status_match = re.match(
                r"^(結果|状態):\s*(OK|NG|WARNING|ERROR|SKIP)$",
                stripped
            )

            if status_match:

                status = status_match.group(2)

                rows.append({

                    "object": current_object,

                    "check": current_check,

                    "status": status,

                    "detail": ""

                })

                current_row = len(rows) - 1

                continue

            # ---------------------------------
            # 説明・内容の追加
            # ---------------------------------

            if stripped.startswith("説明:"):

                detail = stripped.split(
                    ":",
                    1
                )[1].strip()

                if current_row is not None:

                    rows[current_row]["detail"] = detail

                continue

            if stripped.startswith("内容:"):

                detail = stripped.split(
                    ":",
                    1
                )[1].strip()

                if current_row is not None:

                    rows[current_row]["detail"] = detail

                continue

        return rows

    # =====================================
    # 05. 修正対象の判定
    # =====================================

    def get_fix_action(self, row_data):
        """検証結果から、自動修正に対応する処理キーを取得する。

        OKやWARNING、ERROR、SKIPには修正ボタンを表示しない。
        未登録の検証項目にも修正ボタンを表示しない。
        """

        if row_data.get("status") != "NG":
            return None

        check_name = row_data.get("check", "")

        return self.FIXABLE_CHECKS.get(check_name)

    # =====================================
    # 06. 修正要求の通知
    # =====================================

    def emit_fix_request(self, row_data, fix_action):
        """修正ボタンのクリックを、親ウィジェットへ通知する。

        このウィジェット自身はMayaシーンを変更しない。
        実際の修正は、シグナルを受け取る側に任せる。
        """

        request = dict(row_data)
        request["fix_action"] = fix_action

        self.fix_requested.emit(request)

    # =====================================
    # 07. 結果表示の更新
    # =====================================

    def setPlainText(self, text):

        self.raw_text = str(text)

        # ---------------------------------
        # 詳細ログの更新
        # ---------------------------------

        self.log_view.setPlainText(
            self.raw_text
        )

        # ---------------------------------
        # 検証結果の解析
        # ---------------------------------

        rows = self.parse_results(
            self.raw_text
        )

        self.result_table.setRowCount(0)

        counts = {

            "OK": 0,

            "NG": 0,

            "WARNING": 0,

            "ERROR": 0,

            "SKIP": 0

        }

        # ---------------------------------
        # テーブルに結果を登録
        # ---------------------------------

        for row_data in rows:

            row = self.result_table.rowCount()

            self.result_table.insertRow(row)

            # オブジェクト名
            full_object_name = row_data["object"]

            object_name = full_object_name.split("|")[-1]

            object_item = QtWidgets.QTableWidgetItem(
                object_name
            )

            object_item.setToolTip(
                full_object_name
            )

            self.result_table.setItem(
                row,
                0,
                object_item
            )

            # 検証項目
            check_item = QtWidgets.QTableWidgetItem(
                row_data["check"]
            )

            self.result_table.setItem(
                row,
                1,
                check_item
            )

            # ---------------------------------
            # ステータスバッジ
            # ---------------------------------
            badge = StatusBadgeLabel(
                row_data["status"]
            )

            # バッジ配置用のコンテナ
            badge_container = QtWidgets.QWidget()

            # 水平方向のレイアウト
            badge_layout = QtWidgets.QHBoxLayout(
            badge_container
            )

            # 余白をなくす
            badge_layout.setContentsMargins(
            0, 0, 0, 0
            )

            badge_layout.setSpacing(0)

            # バッジを水平・垂直方向の中央に配置
            badge_layout.addWidget(
            badge,
            0,
            ALIGN_CENTER
            )

            # テーブルにコンテナを配置
            self.result_table.setCellWidget(
            row,
            2,
            badge_container
            )

            # 詳細情報
            detail_item = QtWidgets.QTableWidgetItem(
                row_data["detail"]
            )

            detail_item.setToolTip(
                row_data["detail"]
            )

            self.result_table.setItem(
                row,
                3,
                detail_item
            )

            # ---------------------------------
            # 修正ボタン
            # ---------------------------------
            # NGかつ自動修正に対応する項目だけボタンを表示する。
            fix_action = self.get_fix_action(row_data)

            if fix_action:

                fix_button = QtWidgets.QPushButton(
                    "修正"
                )

                fix_button.setObjectName(
                    "validationFixButton"
                )

                fix_button.setFixedWidth(58)
                fix_button.setFixedHeight(25)

                fix_button.setToolTip(
                    "この検証項目を自動修正します。"
                )

                fix_button.setStyleSheet("""
                    QPushButton#validationFixButton {
                        background-color: #285D48;
                        color: #E4FFF0;
                        border: 1px solid #397D61;
                        border-radius: 4px;
                        padding: 2px 8px;
                        font-size: 10px;
                        font-weight: bold;
                    }

                    QPushButton#validationFixButton:hover {
                        background-color: #34785B;
                    }

                    QPushButton#validationFixButton:pressed {
                        background-color: #1F4938;
                    }
                """)

                # ループ変数の値を固定して、クリック時に
                # 正しい行のデータが通知されるようにする。
                fix_button.clicked.connect(
                    lambda checked=False,
                    data=dict(row_data),
                    action=fix_action:
                        self.emit_fix_request(data, action)
                )

                fix_container = QtWidgets.QWidget()
                fix_layout = QtWidgets.QHBoxLayout(
                    fix_container
                )

                fix_layout.setContentsMargins(
                    2, 0, 2, 0
                )

                fix_layout.setSpacing(0)
                fix_layout.addWidget(
                    fix_button,
                    0,
                    ALIGN_CENTER
                )

                self.result_table.setCellWidget(
                    row,
                    4,
                    fix_container
                )

            else:

                no_fix_item = QtWidgets.QTableWidgetItem(
                    "—"
                )

                no_fix_item.setTextAlignment(
                    ALIGN_CENTER
                )

                self.result_table.setItem(
                    row,
                    4,
                    no_fix_item
                )

            self.result_table.setRowHeight(
                row,
                42
            )

            counts[row_data["status"]] += 1

        # ---------------------------------
        # サマリー表示
        # ---------------------------------

        if rows:

            self.summary_label.setText(

                "検証結果　"
                "OK: {}　"
                "WARNING: {}　"
                "NG: {}　"
                "ERROR: {}　"
                "SKIP: {}".format(

                    counts["OK"],

                    counts["WARNING"],

                    counts["NG"],

                    counts["ERROR"],

                    counts["SKIP"]

                )

            )

        else:

            self.summary_label.setText(
                "一覧表示できる検証結果はありません。詳細ログを確認してください。"
            )

    # =====================================
    # 06. 既存コードとの互換性
    # =====================================

    def toPlainText(self):

        return self.raw_text

    def setReadOnly(self, value):

        self.log_view.setReadOnly(value)

    def setPlaceholderText(self, text):

        self.log_view.setPlaceholderText(text)