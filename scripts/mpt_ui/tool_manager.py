# =========================================
# Maya Production Toolkit
# Tool Manager
# =========================================

import importlib
import sys


class ToolManager:

    # =====================================
    # 01. 共通処理: 登録情報から関数を取り出す
    # =====================================

    def _load_function(self, tool_info, function_key):

        """
        tool_registryの登録情報から、モジュールを読み込み、
        function_keyで指定された名前の関数を取り出す。

        function_key:
            "function"        -> 単独ウィンドウで起動する関数(show_ui)
            "widget_function" -> 画面部品だけを作って返す関数(create_widget)
        """

        # ---------------------------------
        # 01. 登録情報の確認
        # ---------------------------------

        if not isinstance(tool_info, dict):

            raise TypeError(
                "ツール情報の形式が正しくありません。"
            )

        tool_title = tool_info.get(
            "title",
            "不明な機能"
        )

        if not tool_info.get("enabled", False):

            raise RuntimeError(
                f"{tool_title}は現在利用できません。"
            )

        # ---------------------------------
        # 02. 起動情報の取得
        # ---------------------------------

        module_name = tool_info.get("module")

        function_name = tool_info.get(function_key)

        if not module_name or not function_name:

            raise ValueError(
                f"{tool_title}の起動情報"
                f"({function_key})が登録されていません。"
            )

        # ---------------------------------
        # 03. モジュールの読み込み
        # ---------------------------------

        if module_name in sys.modules:

            module = importlib.reload(
                sys.modules[module_name]
            )

        else:

            module = importlib.import_module(
                module_name
            )

        # ---------------------------------
        # 04. 関数の取得
        # ---------------------------------

        function = getattr(
            module,
            function_name,
            None
        )

        if function is None:

            raise AttributeError(
                f"{module_name}に"
                f"{function_name}が存在しません。"
            )

        if not callable(function):

            raise TypeError(
                f"{function_name}は実行可能な関数ではありません。"
            )

        return function

    # =====================================
    # 02. 単独ウィンドウで起動(従来の方法)
    # =====================================

    def launch(self, tool_info):

        """
        登録された機能を、独立したウィンドウとして起動する。
        """

        launch_function = self._load_function(
            tool_info,
            "function"
        )

        return launch_function()

    # =====================================
    # 03. 画面部品だけを作る(ホーム画面への組み込み用)
    # =====================================

    def create_widget(self, tool_info, parent=None):

        """
        登録された機能の画面部品(QWidget)を作って返す。
        ウィンドウとしては表示しない。表示する場所は呼び出し側が決める。
        """

        widget_function = self._load_function(
            tool_info,
            "widget_function"
        )

        return widget_function(parent)