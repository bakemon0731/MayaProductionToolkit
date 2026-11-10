# =========================================
# Maya Production Toolkit
# Tool Registry
# =========================================


def get_tool_definitions():

    """
    ホーム画面に表示する機能の情報を返す。

    各機能について、
    ・カテゴリー
    ・タイトル
    ・説明
    ・利用状態
    ・起動するPythonモジュール
    ・起動する関数

    を管理する。
    """

    tools = [

        # =================================
        # 機能01：Maya → Unreal Export
        # =================================

        {
            "id": "maya_unreal_export",

            "category": "ASSET PIPELINE",

            "title": "Maya → Unreal Export Toolkit",

            "description": (
                "アセット検証・自動修正・FBX書き出し・"
                "Unreal Engineへの自動インポートを行います。"
            ),

            "status": "利用可能",

            "enabled": True,

            "module": "validation_ui_pyside",

            "function": "show_ui",

            # ホーム画面の中に組み込むときに呼ぶ関数
            "widget_function": "create_widget"
        },

        # =================================
        # 機能02：Phong → Arnold
        # =================================

        {
            "id": "phong_to_arnold",

            "category": "MATERIAL TOOLS",

            "title": "Phong → Arnold Converter",

            "description": (
                "Phongマテリアルの検出・変換・管理を行い、"
                "Arnold aiStandardSurfaceへ変換します。"
            ),

            "status": "利用可能",

            "enabled": True,

            "module": "material_tools.phong_to_arnold_ui",

            "function": "show_ui",

            # ホーム画面の中に組み込むときに呼ぶ関数
            "widget_function": "create_widget"
        },

        # =================================
        # 機能03：Scene Utilities
        # =================================

        {
            "id": "scene_utilities",

            "category": "SCENE MANAGEMENT",

            "title": "Scene Utilities",

            "description": (
                "シーン整理・不要ノードの検出・"
                "オブジェクト管理などを行います。"
            ),

            "status": "追加予定",

            "enabled": False,

            "module": None,

            "function": None,

            "widget_function": None
        },

        # =================================
        # 機能04：Artist Utilities
        # =================================

        {
            "id": "artist_utilities",

            "category": "ARTIST UTILITIES",

            "title": "Artist Utilities",

            "description": (
                "日常的な制作作業を効率化する"
                "補助ツールをまとめます。"
            ),

            "status": "追加予定",

            "enabled": False,

            "module": None,

            "function": None,

            "widget_function": None
        }

    ]

    return tools