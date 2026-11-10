
# =========================================
# Maya Production Toolkit
# Update Notice
# =========================================

import os
import json

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets


# =========================================
# 01. パス設定
# =========================================

# release_notes.json
SCRIPT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

RELEASE_NOTES_PATH = os.path.join(
    SCRIPT_DIR,
    "release_notes.json"
)

# ユーザーごとの既読情報
USER_DATA_DIR = os.path.join(
    os.path.expanduser("~"),
    ".maya_production_toolkit"
)

LAST_SEEN_PATH = os.path.join(
    USER_DATA_DIR,
    "last_seen_update.json"
)


# =========================================
# 02. 更新情報の読み込み
# =========================================

def load_release_notes():

    if not os.path.exists(RELEASE_NOTES_PATH):
        return []

    with open(
        RELEASE_NOTES_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data.get("releases", [])


# =========================================
# 03. 既読バージョンの取得
# =========================================

def load_last_seen_version():

    if not os.path.exists(LAST_SEEN_PATH):
        return None

    try:

        with open(
            LAST_SEEN_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data.get("last_seen_version")

    except (OSError, ValueError, TypeError):

        return None


# =========================================
# 04. 未読アップデートの取得
# =========================================

def get_unread_releases():

    releases = load_release_notes()

    if not releases:
        return []

    last_seen = load_last_seen_version()

    if not last_seen:

        # 初回起動時は最新の更新だけ表示
        return [releases[-1]]

    versions = [
        release["version"]
        for release in releases
    ]

    if last_seen not in versions:

        # 保存されているバージョンが
        # 履歴に存在しない場合
        return [releases[-1]]

    last_index = versions.index(last_seen)

    # 既読バージョンより新しいものだけ取得
    return releases[last_index + 1:]


# =========================================
# 05. 既読情報の保存
# =========================================

def save_last_seen_version(version):

    os.makedirs(
        USER_DATA_DIR,
        exist_ok=True
    )

    data = {
        "last_seen_version": version
    }

    temp_path = LAST_SEEN_PATH + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    # 書き込み完了後に置き換える
    os.replace(
        temp_path,
        LAST_SEEN_PATH
    )


# =========================================
# 06. 通知Window
# =========================================

class UpdateNoticeWindow(QtWidgets.QDialog):

    def __init__(self, releases, parent=None):

        super().__init__(parent)

        self.releases = releases

        self.setWindowTitle(
            "MPT - アップデートのお知らせ"
        )

        self.setMinimumSize(
            720,
            400
        )

        self.build_ui()

    def build_ui(self):

        layout = QtWidgets.QVBoxLayout(self)

        # タイトル
        title = QtWidgets.QLabel(
            "MAYA PRODUCTION TOOLKIT"
        )

        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #68C8DC;
        """)

        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "アップデートのお知らせ"
        )

        subtitle.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: white;
        """)

        layout.addWidget(subtitle)

        # 更新内容
        content = QtWidgets.QTextBrowser()

        content.setOpenExternalLinks(False)

        content.setPlainText(
            self.create_release_text()
        )

        content.setStyleSheet("""
            QTextBrowser {
                background-color: #222B35;
                color: #F0F3F7;
                border: 1px solid #354253;
                padding: 12px;
                font-size: 12px;
            }
        """)

        layout.addWidget(content)

        # 閉じるボタン
        close_button = QtWidgets.QPushButton(
            "確認しました"
        )

        close_button.setMinimumHeight(36)

        close_button.clicked.connect(
            self.accept
        )

        layout.addWidget(close_button)

        self.setStyleSheet("""
            QDialog {
                background-color: #171D27;
            }

            QPushButton {
                background-color: #24647A;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }

            QPushButton:hover {
                background-color: #32849C;
            }
        """)

    # -------------------------------------
    # 更新内容の文章生成
    # -------------------------------------

    def create_release_text(self):

        lines = []

        for release in self.releases:

            lines.append(
                "■ Version "
                + release["version"]
            )

            lines.append(
                release.get("date", "")
            )

            lines.append(
                release.get("title", "")
            )

            lines.append("")

            for change in release.get("changes", []):

                lines.append(
                    "  ・" + change
                )

            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        return "\n".join(lines)


# =========================================
# 07. 通知の起動
# =========================================

def show_update_notice(parent=None):

    releases = get_unread_releases()

    if not releases:
        return

    window = UpdateNoticeWindow(
        releases,
        parent
    )

    # PySide6 / PySide2 両対応
    if hasattr(window, "exec"):
        window.exec()
    else:
        window.exec_()

    # Windowを閉じた後に既読状態を保存
    latest_version = releases[-1]["version"]

    save_last_seen_version(
        latest_version
    )
