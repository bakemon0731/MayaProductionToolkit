# =========================================
# Maya Production Toolkit
# Launcher
# =========================================

import os
import sys
import importlib


# =========================================
# 01. プロジェクトパス
# =========================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

if SCRIPT_DIR not in sys.path:

    sys.path.insert(
        0,
        SCRIPT_DIR
    )



# =========================================
# 02. ホーム画面起動
# =========================================

def show_ui():

    # カードの部品を再読み込み
    import mpt_ui.widgets.tool_card_widget
    importlib.reload(
        mpt_ui.widgets.tool_card_widget
    )

    # ツール登録情報を再読み込み
    import mpt_ui.tool_registry
    importlib.reload(
        mpt_ui.tool_registry
    )

    # ツール管理クラスを再読み込み
    import mpt_ui.tool_manager
    importlib.reload(
        mpt_ui.tool_manager
    )

    # メイン画面を再読み込み
    import mpt_ui.main_window
    importlib.reload(
        mpt_ui.main_window
    )

    # MPT起動
    window = mpt_ui.main_window.show_ui()

    # -------------------------------------
    # アップデート通知
    # -------------------------------------

    try:

        import mpt_ui.update_notice
        importlib.reload(
            mpt_ui.update_notice
        )

        mpt_ui.update_notice.show_update_notice(
            window
        )

    except Exception:

        import traceback
        traceback.print_exc()

    return window

