import os
import sys
import importlib
import traceback

import maya.cmds as cmds

# =========================================
# 00. Qtライブラリ読み込み
# =========================================

try:

    # Maya 2025以降
    from PySide6 import QtCore, QtWidgets

    from shiboken6 import wrapInstance

    QT_BINDING = "PySide6"

    QMessageBoxIcon = QtWidgets.QMessageBox.Icon

    QMessageBoxStandardButton = (
        QtWidgets.QMessageBox.StandardButton
    )

    WINDOW_FLAG = QtCore.Qt.WindowType.Window

except ImportError:

    try:

        # Maya 2024以前
        from PySide2 import QtCore, QtWidgets

        from shiboken2 import wrapInstance

        QT_BINDING = "PySide2"

        QMessageBoxIcon = QtWidgets.QMessageBox

        QMessageBoxStandardButton = QtWidgets.QMessageBox

        WINDOW_FLAG = QtCore.Qt.Window

    except ImportError as error:

        raise ImportError(
            "PySide2またはPySide6を読み込めません。\n"
            "Maya付属のPython環境で実行してください。"
        ) from error


from maya import OpenMayaUI as omui


# =========================================
# 01. パス設定
# =========================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UE_SCRIPT_DIR = os.path.join(
    SCRIPT_DIR,
    "ue"
)

for directory in [SCRIPT_DIR, UE_SCRIPT_DIR]:

    if directory not in sys.path:

        sys.path.insert(
            0,
            directory
        )


# =========================================
# モジュール読み込み
# =========================================

import validate_names
import validate_transforms
import validate_history
import validate_ngons
import validate_uvs

import fix_names
import fix_transforms
import fix_history

import export_fbx
import validation_result_widget


# =========================================
# 03. ウィンドウ管理
# =========================================

WINDOW = None

WINDOW_NAME = "ExportToolkitTestWindow"


print(
    "Export Toolkit Qt Binding: {}".format(
        QT_BINDING
    )
)


# =========================================
# 04. 個別検証
# =========================================

def run_validation(
    result_view,
    check_function,
    check_title
):

    try:

        results = check_function() or []

        if not results:

            result_view.setPlainText(
                "検証結果がありません。\n"
                "オブジェクトを選択してください。"
            )

            return []

        lines = []

        lines.append(
            "===== {}チェック結果 =====".format(
                check_title
            )
        )

        lines.append("")

        for result in results:

            lines.append(
                "オブジェクト: {}".format(
                    result.get("object", "不明")
                )
            )

            lines.append(
                "結果: {}".format(
                    result.get("status", "不明")
                )
            )

            lines.append(
                "説明: {}".format(
                    result.get("message", "")
                )
            )

            details = result.get("details", [])

            if details:

                lines.append("追加情報:")

                for detail in details:

                    if isinstance(detail, dict):

                        for key, value in detail.items():

                            lines.append(
                                " {}: {}".format(
                                    key,
                                    value
                                )
                            )

                    else:

                        lines.append(
                            " " + str(detail)
                        )

            lines.append("")

        output_text = "\n".join(lines)

        result_view.setPlainText(
            output_text
        )

        print(output_text)

        return results

    except Exception as error:

        message = "検証エラー: {}".format(error)

        result_view.setPlainText(message)

        print(message)

        return []


# =========================================
# 05. 全項目チェック
# =========================================

def run_all_validations(
    result_view,
    validation_checks,
    display=True
):

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:

        if display:

            result_view.setPlainText(
                "オブジェクトを選択してください。"
            )

        return {
            "results": [],
            "errors": []
        }

    all_results = []

    errors = []

    # -------------------------------------
    # 5種類の検証を実行
    # -------------------------------------

    for label, check_function in validation_checks:

        try:

            results = check_function() or []

            all_results.extend(results)

        except Exception as caught_exception:

            errors.append({

                "check": label,

                "type": type(
                    caught_exception
                ).__name__,

                "message": str(
                    caught_exception
                )

            })

    # -------------------------------------
    # オブジェクト単位で結果を整理
    # -------------------------------------

    object_results = {}

    for result in all_results:

        object_name = (
            result.get("object")
            or "不明"
        )

        if object_name not in object_results:

            object_results[object_name] = []

        object_results[object_name].append(result)

    lines = []

    lines.append(
        "===== 全項目チェック結果 ====="
    )

    lines.append("")

    # -------------------------------------
    # 検証結果を表示
    # -------------------------------------

    for object_name, results in object_results.items():

        lines.append(
            "オブジェクト: {}".format(
                object_name
            )
        )

        lines.append("")

        for result in results:

            lines.append(
                "[{}] {}".format(
                    result.get("status", "不明"),
                    result.get("check", "不明")
                )
            )

            lines.append(
                " 説明: {}".format(
                    result.get("message", "")
                )
            )

            details = result.get("details", [])

            if details:

                lines.append(" 追加情報:")

                for detail in details:

                    if isinstance(detail, dict):

                        for key, value in detail.items():

                            lines.append(
                                "  {}: {}".format(
                                    key,
                                    value
                                )
                            )

                    else:

                        lines.append(
                            "  " + str(detail)
                        )

            lines.append("")

    # -------------------------------------
    # ステータス集計
    # -------------------------------------

    ok_count = sum(
        1
        for result in all_results
        if result.get("status") == "OK"
    )

    ng_count = sum(
        1
        for result in all_results
        if result.get("status") == "NG"
    )

    skip_count = sum(
        1
        for result in all_results
        if result.get("status") == "SKIP"
    )

    warning_count = sum(
        1
        for result in all_results
        if result.get("status") == "WARNING"
    )

    result_error_count = sum(
        1
        for result in all_results
        if result.get("status") == "ERROR"
    )

    exception_count = len(errors)

    error_count = (
        result_error_count
        + exception_count
    )

    # -------------------------------------
    # 実行サマリー
    # -------------------------------------

    lines.append(
        "===== 実行サマリー ====="
    )

    lines.append(
        "検証対象オブジェクト数: {}".format(
            len(selected)
        )
    )

    lines.append(
        "取得した検証結果数: {}".format(
            len(all_results)
        )
    )

    lines.append(
        "OK件数: {}".format(ok_count)
    )

    lines.append(
        "WARNING件数: {}".format(
            warning_count
        )
    )

    lines.append(
        "NG件数: {}".format(ng_count)
    )

    lines.append(
        "SKIP件数: {}".format(skip_count)
    )

    lines.append(
        "ERROR件数: {}".format(error_count)
    )

    lines.append(
        "例外が発生した数: {}".format(
            exception_count
        )
    )

    # -------------------------------------
    # エラー詳細
    # -------------------------------------

    if errors:

        lines.append("")

        lines.append(
            "===== エラー詳細 ====="
        )

        for error_info in errors:

            lines.append(
                "検証項目: {}".format(
                    error_info["check"]
                )
            )

            lines.append(
                "エラーの種類: {}".format(
                    error_info["type"]
                )
            )

            lines.append(
                "エラーの詳細: {}".format(
                    error_info["message"]
                )
            )

            lines.append("")

    output_text = "\n".join(lines)

    if display:

        result_view.setPlainText(
            output_text
        )

        print(output_text)

    return {

        "results": all_results,

        "errors": errors

    }


# =========================================
# 06. 書き出し前の検証判定
# =========================================

def check_export_validation(
    result_view,
    validation_checks,
    export_mode
):

    # -------------------------------------
    # クイックモード
    # -------------------------------------

    if export_mode == "quick":

        message = (
            "===== クイックモード =====\n\n"
            "アセット検証を省略します。\n"
            "検証を行わず、FBX書き出しへ進みます。\n\n"
            "※命名規則・Transform・History・N-gon・UVの\n"
            "検証は実行されていません。"
        )

        result_view.setPlainText(message)

        print(message)

        return True

    # -------------------------------------
    # モードの確認
    # -------------------------------------

    if export_mode != "strict":

        result_view.setPlainText(
            "書き出しモードが不正です。\n"
            "処理を中止しました。"
        )

        return False

    # -------------------------------------
    # 厳格チェック
    # -------------------------------------

    validation_data = run_all_validations(
        result_view,
        validation_checks,
        display=True
    )

    results = validation_data["results"]

    errors = validation_data["errors"]

    # -------------------------------------
    # 検証結果がない場合
    # -------------------------------------

    if not results:

        lines = [

            result_view.toPlainText(),

            "",

            "===== 書き出し判定 =====",

            "検証結果を取得できませんでした。",

            "FBX書き出しを中止しました。"

        ]

        result_view.setPlainText(
            "\n".join(lines)
        )

        return False

    # -------------------------------------
    # OK以外の結果を抽出
    # -------------------------------------

    failed_results = [

        result

        for result in results

        if result.get("status") != "OK"

    ]

    # -------------------------------------
    # 書き出し可否の判定
    # -------------------------------------

    if failed_results or errors:

        lines = [

            result_view.toPlainText(),

            "",

            "===== 厳格チェック判定 =====",

            "検証に問題があるため、書き出しを中止しました。",

            ""

        ]

        for result in failed_results:

            lines.append(
                "対象: {}".format(
                    result.get("object", "不明")
                )
            )

            lines.append(
                "検証: {}".format(
                    result.get("check", "不明")
                )
            )

            lines.append(
                "状態: {}".format(
                    result.get("status", "不明")
                )
            )

            lines.append(
                "内容: {}".format(
                    result.get("message", "")
                )
            )

            lines.append("")

        if errors:

            lines.append(
                "===== 検証例外 ====="
            )

            for error_info in errors:

                lines.append(
                    "検証項目: {}".format(
                        error_info["check"]
                    )
                )

                lines.append(
                    "エラー: {}".format(
                        error_info["message"]
                    )
                )

                lines.append("")

        output_text = "\n".join(lines)

        result_view.setPlainText(
            output_text
        )

        print(output_text)

        return False

    # -------------------------------------
    # 全項目合格
    # -------------------------------------

    print(
        "厳格チェックに合格しました。"
    )

    return True


# =========================================
# 07. 確認ダイアログ
# =========================================

def ask_confirmation(
    parent,
    title,
    message
):

    dialog = QtWidgets.QMessageBox(parent)

    dialog.setIcon(
        QMessageBoxIcon.Warning
    )

    dialog.setWindowTitle(title)

    dialog.setText(message)

    dialog.setStandardButtons(

        QMessageBoxStandardButton.Yes
        |
        QMessageBoxStandardButton.No

    )

    dialog.button(
        QMessageBoxStandardButton.Yes
    ).setText("実行する")

    dialog.button(
        QMessageBoxStandardButton.No
    ).setText("キャンセル")

    dialog.setDefaultButton(
        QMessageBoxStandardButton.No
    )

    exec_function = getattr(
        dialog,
        "exec",
        None
    )

    if exec_function is not None:

        answer = exec_function()

    else:

        answer = dialog.exec_()

    return (
        answer
        == QMessageBoxStandardButton.Yes
    )


# =========================================
# 08. 自動修正結果の表示
# =========================================

def append_fix_results(
    lines,
    fix_results
):

    for result in fix_results:

        object_name = result.get(
            "object",
            "不明"
        )

        if isinstance(object_name, str):

            object_name = object_name.split("|")[-1]

        lines.append(
            "対象: {}".format(object_name)
        )

        lines.append(
            "状態: {}".format(
                result.get("status", "不明")
            )
        )

        lines.append(
            "内容: {}".format(
                result.get("message", "")
            )
        )

        details = result.get(
            "details",
            []
        )

        # detailsが辞書のときも、項目名と値を表示できるようにする
        if isinstance(details, dict):

            details = [details]

        if details:

            lines.append("追加情報:")

            for detail in details:

                if isinstance(detail, dict):

                    for key, value in detail.items():

                        lines.append(
                            " {}: {}".format(
                                key,
                                value
                            )
                        )

                else:

                    lines.append(
                        " " + str(detail)
                    )

        lines.append("")


# =========================================
# 09. 修正後の再検証
# =========================================

def finish_fix_and_revalidate(
    result_view,
    validation_checks,
    selected,
    fix_results,
    operation_title
):

    lines = []

    lines.append(
        "===== {}の結果 =====".format(
            operation_title
        )
    )

    if not fix_results:

        lines.append(
            "修正結果がありません。"
        )

        result_view.setPlainText(
            "\n".join(lines)
        )

        return

    append_fix_results(
        lines,
        fix_results
    )

    # -------------------------------------
    # ERRORを抽出
    # -------------------------------------

    fix_errors = [

        result

        for result in fix_results

        if result.get("status") == "ERROR"

    ]

    if fix_errors:

        lines.append(
            "修正エラーが発生したため、再検証を中止しました。"
        )

        result_view.setPlainText(
            "\n".join(lines)
        )

        return

    # -------------------------------------
    # 修正に成功したオブジェクトを取得
    # -------------------------------------

    fix_successes = [

        result

        for result in fix_results

        if result.get("status") == "OK"
        and result.get("object")

    ]

    successful_objects = [

        result.get("object")

        for result in fix_successes

    ]

    if not successful_objects:

        lines.append(
            "修正に成功したメッシュがないため、再検証を中止しました。"
        )

        result_view.setPlainText(
            "\n".join(lines)
        )

        return

    # -------------------------------------
    # 修正前・修正後のパスを対応付ける
    # -------------------------------------

    selection_mapping = {}

    for result in fix_results:

        details = result.get(
            "details",
            []
        )

        for detail in details:

            if isinstance(detail, dict):

                old_path = detail.get(
                    "変更前パス"
                )

                new_path = detail.get(
                    "変更後パス"
                )

                if old_path and new_path:

                    selection_mapping[old_path] = new_path

    selection_to_restore = [

        selection_mapping.get(obj, obj)

        for obj in selected

    ]

    # -------------------------------------
    # 修正後の再検証
    # -------------------------------------

    validation_data = None

    selection_restore_error = None

    try:

        cmds.select(
            successful_objects,
            replace=True
        )

        validation_data = run_all_validations(
            result_view,
            validation_checks,
            display=False
        )

    except Exception as error:

        lines.append("")

        lines.append(
            "再検証中にエラーが発生しました: {}".format(
                error
            )
        )

    finally:

        # 元の選択状態を復元
        try:

            valid_selection = [

                obj

                for obj in selection_to_restore

                if cmds.objExists(obj)

            ]

            if valid_selection:

                cmds.select(
                    valid_selection,
                    replace=True
                )

            else:

                cmds.select(clear=True)

        except Exception as error:

            selection_restore_error = str(error)

    # -------------------------------------
    # 再検証結果が取得できなかった場合
    # -------------------------------------

    if validation_data is None:

        if selection_restore_error:

            lines.append(
                "選択状態の復元エラー: {}".format(
                    selection_restore_error
                )
            )

        result_view.setPlainText(
            "\n".join(lines)
        )

        print("\n".join(lines))

        return

    # -------------------------------------
    # 再検証結果を取得
    # -------------------------------------

    validation_results = validation_data["results"]

    validation_errors = validation_data["errors"]

    failed_results = [

        result

        for result in validation_results

        if result.get("status") != "OK"

    ]

    lines.append("")

    lines.append(
        "===== 修正後の再検証結果 ====="
    )

    lines.append(
        "検証件数: {}".format(
            len(validation_results)
        )
    )

    lines.append(
        "要確認件数: {}".format(
            len(failed_results)
        )
    )

    # -------------------------------------
    # 個別の検証結果
    # -------------------------------------

    for result in validation_results:

        object_name = result.get(
            "object",
            "不明"
        )

        if isinstance(object_name, str):

            object_name = object_name.split("|")[-1]

        lines.append(
            "対象: {} | 検証: {} | 状態: {} | 内容: {}".format(
                object_name,
                result.get("check"),
                result.get("status"),
                result.get("message")
            )
        )

    # -------------------------------------
    # 再検証エラー
    # -------------------------------------

    if validation_errors:

        lines.append("")

        lines.append(
            "===== 再検証エラー ====="
        )

        for error_info in validation_errors:

            lines.append(
                "検証項目: {}".format(
                    error_info["check"]
                )
            )

            lines.append(
                "種類: {}".format(
                    error_info["type"]
                )
            )

            lines.append(
                "内容: {}".format(
                    error_info["message"]
                )
            )

    # -------------------------------------
    # 選択状態の復元エラー
    # -------------------------------------

    if selection_restore_error:

        lines.append("")

        lines.append(
            "選択状態の復元エラー: {}".format(
                selection_restore_error
            )
        )

    # -------------------------------------
    # 最終結果表示
    # -------------------------------------

    output_text = "\n".join(lines)

    result_view.setPlainText(
        output_text
    )

    print(output_text)


# =========================================
# 10. 命名規則自動修正
# =========================================

def run_name_auto_fix(
    result_view,
    validation_checks,
    parent
):

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:

        result_view.setPlainText(
            "オブジェクトが選択されていません。\n"
            "命名規則の自動修正を中止しました。"
        )

        return

    fix_candidates = []

    skipped_objects = []

    for obj in selected:

        object_name = obj.split("|")[-1]

        shapes = cmds.listRelatives(
            obj,
            shapes=True,
            noIntermediate=True,
            fullPath=True
        ) or []

        mesh_shapes = [

            shape

            for shape in shapes

            if cmds.nodeType(shape) == "mesh"

        ]

        if not mesh_shapes:

            skipped_objects.append(
                object_name
            )

            continue

        if not object_name.startswith("SM_"):

            fix_candidates.append(
                object_name
            )

    if not fix_candidates:

        result_view.setPlainText(
            "命名規則の修正対象がありません。\n"
            "すべてのメッシュがSM_で始まっています。"
        )

        return

    fix_list = "\n".join(

        "- " + name

        for name in fix_candidates

    )

    skipped_list = "\n".join(

        "- " + name

        for name in skipped_objects

    ) if skipped_objects else "なし"

    message = (

        "命名規則の自動修正対象を確認してください。\n\n"

        "【修正対象】\n"

        + fix_list

        + "\n\n【スキップ対象】\n"

        + skipped_list

        + "\n\n対象のオブジェクト名の先頭にSM_を追加します。\n\n"

        "続行しますか？"

    )

    confirmed = ask_confirmation(
        parent,
        "命名規則自動修正の確認",
        message
    )

    if not confirmed:

        result_view.setPlainText(
            "命名規則の自動修正をキャンセルしました。"
        )

        return

    try:

        importlib.reload(fix_names)

        fix_results = fix_names.fix_selected_names()

        finish_fix_and_revalidate(
            result_view,
            validation_checks,
            selected,
            fix_results,
            "命名規則自動修正"
        )

    except Exception as error:

        message = (
            "命名規則の自動修正中にエラーが発生しました: {}".format(
                error
            )
        )

        result_view.setPlainText(message)

        print(message)


# =========================================
# 11. Transform自動修正
# =========================================

def run_transform_auto_fix(
    result_view,
    validation_checks,
    parent
):

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:

        result_view.setPlainText(
            "オブジェクトが選択されていません。\n"
            "Transform自動修正を中止しました。"
        )

        return

    fix_candidates = []

    skipped_objects = []

    for obj in selected:

        shapes = cmds.listRelatives(
            obj,
            shapes=True,
            noIntermediate=True,
            fullPath=True
        ) or []

        mesh_shapes = [

            shape

            for shape in shapes

            if cmds.nodeType(shape) == "mesh"

        ]

        object_name = obj.split("|")[-1]

        if mesh_shapes:

            fix_candidates.append(object_name)

        else:

            skipped_objects.append(object_name)

    if not fix_candidates:

        lines = [

            "Transform自動修正の対象となるメッシュがありません。",

            "",

            "スキップ対象:"

        ]

        for name in skipped_objects:

            lines.append("- " + name)

        result_view.setPlainText(
            "\n".join(lines)
        )

        return

    fix_list = "\n".join(

        "- " + name

        for name in fix_candidates

    )

    skipped_list = "\n".join(

        "- " + name

        for name in skipped_objects

    ) if skipped_objects else "なし"

    message = (

        "Transform自動修正の対象を確認してください。\n\n"

        "【修正対象（メッシュ）】\n"

        + fix_list

        + "\n\n【スキップ対象（メッシュShapeなし）】\n"

        + skipped_list

        + "\n\nTranslate・Rotate・Scaleを基準値に戻します。\n"

        "ワールド境界を確認しながら処理します。\n\n"

        "続行しますか？"

    )

    confirmed = ask_confirmation(
        parent,
        "Transform自動修正の確認",
        message
    )

    if not confirmed:

        result_view.setPlainText(
            "Transform自動修正をキャンセルしました。"
        )

        return

    try:

        importlib.reload(fix_transforms)

        fix_results = fix_transforms.fix_selected_transforms()

        finish_fix_and_revalidate(
            result_view,
            validation_checks,
            selected,
            fix_results,
            "Transform自動修正"
        )

    except Exception as error:

        message = (
            "Transform自動修正中にエラーが発生しました: {}".format(
                error
            )
        )

        result_view.setPlainText(message)

        print(message)


# =========================================
# 12. Construction History自動修正
# =========================================

def run_history_auto_fix(
    result_view,
    validation_checks,
    parent
):

    importlib.reload(fix_history)

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:

        result_view.setPlainText(
            "オブジェクトが選択されていません。\n"
            "Construction History削除を中止しました。"
        )

        return

    history_candidates = []

    skipped_objects = []

    for obj in selected:

        object_name = obj.split("|")[-1]

        # 履歴の調査は fix_history 側の共通関数に任せる
        analysis = fix_history.analyze_history(obj)

        if not analysis["mesh_shapes"]:

            skipped_objects.append(
                (
                    object_name,
                    "メッシュShapeがありません"
                )
            )

            continue

        if not analysis["history"]:

            skipped_objects.append(
                (
                    object_name,
                    "Construction Historyがありません"
                )
            )

            continue

        if analysis["unsupported"]:

            node_details = ", ".join(

                "{} ({})".format(
                    node,
                    analysis["types"][node]
                )

                for node in analysis["unsupported"]

            )

            skipped_objects.append(
                (
                    object_name,
                    "対応対象外の履歴: " + node_details
                )
            )

        else:

            history_candidates.append(
                object_name
            )

    if not history_candidates:

        lines = [

            "Construction Historyの削除対象がありません。",

            "",

            "スキップ対象:"

        ]

        for name, reason in skipped_objects:

            lines.append(
                "- {}：{}".format(
                    name,
                    reason
                )
            )

        result_view.setPlainText(
            "\n".join(lines)
        )

        return

    history_list = "\n".join(

        "- " + name

        for name in history_candidates

    )

    skipped_list = "\n".join(

        "- {}：{}".format(
            name,
            reason
        )

        for name, reason in skipped_objects

    ) if skipped_objects else "なし"

    message = (

        "Construction Historyの処理対象を確認してください。\n\n"

        "【削除対象】\n"

        + history_list

        + "\n\n【スキップ対象】\n"

        + skipped_list

        + "\n\n削除対象のメッシュからConstruction Historyを削除します。\n"

        "削除後はモデリング操作の履歴を編集できなくなります。\n\n"

        "続行しますか？"

    )

    confirmed = ask_confirmation(
        parent,
        "Construction History削除の確認",
        message
    )

    if not confirmed:

        result_view.setPlainText(
            "Construction Historyの削除をキャンセルしました。"
        )

        return

    try:

        fix_results = fix_history.fix_selected_history()

        finish_fix_and_revalidate(
            result_view,
            validation_checks,
            selected,
            fix_results,
            "Construction History自動修正"
        )

    except Exception as error:

        message = (
            "Construction History削除中にエラーが発生しました: {}".format(
                error
            )
        )

        result_view.setPlainText(message)

        print(message)


# =========================================
# 13. FBX書き出し
# =========================================

def run_validate_and_export(
    result_view,
    validation_checks,
    mode_widget
):

    # -------------------------------------
    # 選択状態の確認
    # -------------------------------------

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:

        result_view.setPlainText(
            "オブジェクトを選択してください。\n"
            "FBX書き出しを中止しました。"
        )

        return

    # -------------------------------------
    # 書き出しモード取得
    # -------------------------------------

    export_mode = mode_widget.currentData()

    mode_name = (

        "厳格チェック"

        if export_mode == "strict"

        else "クイックモード"

    )

    # -------------------------------------
    # 書き出し前の検証
    # -------------------------------------

    can_export = check_export_validation(
        result_view,
        validation_checks,
        export_mode
    )

    if not can_export:

        return

    # -------------------------------------
    # FBX書き出し
    # -------------------------------------

    try:

        importlib.reload(export_fbx)

        export_result = export_fbx.export_selected_fbx()

        if not isinstance(export_result, dict):

            result_view.setPlainText(
                "FBX書き出し結果の形式が正しくありません。"
            )

            return

        status = export_result.get("status")

        lines = [

            "===== FBX書き出し結果 =====",

            "",

            "書き出しモード: {}".format(
                mode_name
            )

        ]

        if status == "OK":

            lines.append(
                "FBX書き出しが完了しました。"
            )

            lines.append(
                "保存先: {}".format(
                    export_result.get(
                        "file_path",
                        "不明"
                    )
                )
            )

        elif status == "CANCELLED":

            lines.append(
                "FBX書き出しはキャンセルされました。"
            )

        else:

            lines.append(
                "FBX書き出しに失敗しました。"
            )

            lines.append(
                "エラー: {}".format(
                    export_result.get(
                        "message",
                        "詳細不明"
                    )
                )
            )

        output_text = "\n".join(lines)

        result_view.setPlainText(output_text)

        print(output_text)

        return export_result

    except Exception as error:

        message = (
            "FBX書き出し中にエラーが発生しました: {}".format(
                error
            )
        )

        result_view.setPlainText(message)

        print(message)

        return


# =========================================
# 14. 検証・FBX書き出し・UEインポート
# =========================================

def run_validate_export_and_import(
    result_view,
    validation_checks,
    destination_input,
    mode_widget
):

    # -------------------------------------
    # 選択状態の確認
    # -------------------------------------

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:

        result_view.setPlainText(
            "オブジェクトを選択してください。\n"
            "UEへの送信を中止しました。"
        )

        return

    # -------------------------------------
    # 書き出しモード取得
    # -------------------------------------

    export_mode = mode_widget.currentData()

    mode_name = (

        "厳格チェック"

        if export_mode == "strict"

        else "クイックモード"

    )

    # -------------------------------------
    # UE保存先確認
    # -------------------------------------

    destination_path = destination_input.text().strip()

    if not destination_path.startswith("/Game/"):

        result_view.setPlainText(
            "UEの保存先が正しくありません。\n\n"
            "保存先は /Game/ から始まる必要があります。\n"
            "例：/Game/Environment/Rocks"
        )

        return

    # -------------------------------------
    # 書き出し前の検証
    # -------------------------------------

    can_export = check_export_validation(
        result_view,
        validation_checks,
        export_mode
    )

    if not can_export:

        return

    # -------------------------------------
    # FBX書き出し
    # -------------------------------------

    try:

        importlib.reload(export_fbx)

        export_result = export_fbx.export_selected_fbx()

    except Exception as error:

        result_view.setPlainText(
            "FBX書き出し中にエラーが発生しました。\n\n"
            + str(error)
        )

        print(traceback.format_exc())

        return

    if not isinstance(export_result, dict):

        result_view.setPlainText(
            "FBX書き出し結果の形式が正しくありません。\n"
            "UEへの送信を中止しました。"
        )

        return

    export_status = export_result.get("status")

    if export_status == "CANCELLED":

        result_view.setPlainText(
            "FBX書き出しがキャンセルされました。\n"
            "UEへの送信を中止しました。"
        )

        return

    if export_status != "OK":

        result_view.setPlainText(
            "FBX書き出しに失敗しました。\n\n"
            + str(
                export_result.get(
                    "message",
                    "詳細不明"
                )
            )
        )

        return

    # -------------------------------------
    # FBXパス確認
    # -------------------------------------

    fbx_path = export_result.get("file_path")

    if not fbx_path or not os.path.isfile(fbx_path):

        result_view.setPlainText(
            "FBXファイルが見つかりません。\n"
            "UEへの送信を中止しました。\n\n"
            "取得したパス: {}".format(fbx_path)
        )

        return

    # -------------------------------------
    # UE連携モジュール読み込み
    # -------------------------------------

    try:

        import send_fbx_to_ue

        importlib.reload(send_fbx_to_ue)

    except Exception as error:

        message = (
            "UE連携モジュールの読み込みに失敗しました。\n\n"
            + str(error)
            + "\n\nFBXは書き出し済みです。\n"
            "保存先: {}".format(fbx_path)
        )

        result_view.setPlainText(message)

        print(traceback.format_exc())

        return

    # -------------------------------------
    # UEへ送信
    # -------------------------------------

    lines = [

        "===== UEへのアセット送信 =====",

        "",

        "書き出しモード: {}".format(
            mode_name
        ),

        "FBX書き出し: 成功",

        "FBX保存先: {}".format(
            fbx_path
        ),

        "UE保存先: {}".format(
            destination_path
        ),

        "",

        "Unreal Engineに接続しています..."

    ]

    result_view.setPlainText(
        "\n".join(lines)
    )

    print("\n".join(lines))

    try:

        import_result = send_fbx_to_ue.import_fbx_to_ue(

            fbx_path=fbx_path,

            destination_path=destination_path

        )

    except Exception as error:

        message = (
            "UEへのFBX送信中にエラーが発生しました。\n\n"
            + str(error)
            + "\n\nFBXは書き出し済みです。\n"
            "保存先: {}".format(fbx_path)
        )

        result_view.setPlainText(message)

        print(traceback.format_exc())

        return

    # -------------------------------------
    # インポート結果
    # -------------------------------------

    lines.append("")

    if (

        isinstance(import_result, dict)

        and import_result.get("status") == "OK"

    ):

        lines.append(
            "===== 処理完了 ====="
        )

        lines.append(
            "FBX書き出し: 成功"
        )

        lines.append(
            "UEインポート: 成功"
        )

        lines.append("")

        lines.append(
            "===== インポートしたアセット ====="
        )

        for asset_path in import_result.get(
            "imported_assets",
            []
        ):

            lines.append(
                "- {}".format(asset_path)
            )

    else:

        lines.append(
            "===== UEインポート失敗 ====="
        )

        if isinstance(import_result, dict):

            lines.append(
                import_result.get(
                    "message",
                    "エラー詳細不明"
                )
            )

            lines.append(
                "詳細: {}".format(
                    import_result.get(
                        "details",
                        ""
                    )
                )
            )

        else:

            lines.append(
                "UE連携モジュールから不正な結果が返されました。"
            )

        lines.append("")

        lines.append(
            "FBXは書き出し済みです。"
        )

        lines.append(
            "保存先: {}".format(fbx_path)
        )

    # -------------------------------------
    # 最終結果表示
    # -------------------------------------

    output_text = "\n".join(lines)

    result_view.setPlainText(output_text)

    print(output_text)

# =========================================
# UI作成
# =========================================

def create_widget(parent=None):

    """ツール本体のWidgetを作って返す(表示はしない)。

    ホーム画面の中に組み込むときは、この関数を使う。
    単独のウィンドウで開くときは、下にある show_ui() を使う。
    """

    global WINDOW

    # -------------------------------------
    # モジュール再読み込み
    # -------------------------------------

    importlib.reload(validate_names)

    importlib.reload(validate_transforms)

    importlib.reload(validate_history)

    importlib.reload(validate_ngons)

    importlib.reload(validate_uvs)

    importlib.reload(fix_names)

    importlib.reload(fix_transforms)

    importlib.reload(fix_history)

    importlib.reload(export_fbx)

    importlib.reload(validation_result_widget)

    # -------------------------------------
    # 検証関数一覧
    # -------------------------------------

    validation_checks = [

        (
            "命名規則",
            validate_names.validate_selected_names
        ),

        (
            "Transform",
            validate_transforms.validate_selected_transforms
        ),

        (
            "Construction History",
            validate_history.validate_selected_history
        ),

        (
            "N-gon",
            validate_ngons.validate_selected_ngons
        ),

        (
            "UV",
            validate_uvs.validate_selected_uvs
        )

    ]

    # =====================================
    # ウィンドウ
    # =====================================

    WINDOW = QtWidgets.QWidget(
        parent
    )

    WINDOW.setObjectName(
        WINDOW_NAME
    )

    WINDOW.setWindowTitle(
        "MayaからUEへ書き出しツール"
    )

    WINDOW.resize(
        1100,
        760
    )

    WINDOW.setMinimumSize(
        900,
        600
    )

    WINDOW.setMinimumWidth(500)

    WINDOW.setToolTip(
        "Mayaのアセット検証・自動修正・FBX書き出し・"
        "Unreal Engineへのインポートを行うツールです。"
    )

    # =====================================
    # メインレイアウト
    # =====================================

    main_layout = QtWidgets.QVBoxLayout(
        WINDOW
    )

    main_layout.setContentsMargins(
        24,
        24,
        24,
        24
    )

    main_layout.setSpacing(16)

    # =====================================
    # HEADER
    # =====================================

    eyebrow = QtWidgets.QLabel(
        "MAYA / UNREAL ENGINE"
    )

    eyebrow.setObjectName(
        "eyebrowLabel"
    )

    title = QtWidgets.QLabel(
        "UEエクスポートMayaツール"
    )

    title.setObjectName(
        "titleLabel"
    )

    description = QtWidgets.QLabel(
        "Asset Validation & Export System"
    )

    description.setObjectName(
        "descriptionLabel"
    )

    main_layout.addWidget(eyebrow)

    main_layout.addWidget(title)

    main_layout.addWidget(description)

    # =====================================
    # メインコンテンツ：左右分割
    # =====================================

    # Qt5・Qt6両方に対応した横方向設定
    try:
        splitter_orientation = (
            QtCore.Qt.Orientation.Horizontal
        )

    except AttributeError:
        splitter_orientation = QtCore.Qt.Horizontal

    # -------------------------------------
    #  QSplitter作成
    # -------------------------------------

    content_splitter = QtWidgets.QSplitter(
        splitter_orientation
    )

    content_splitter.setObjectName(
        "mainContentSplitter"
    )

    # パネルを0幅まで縮小できないようにする
    content_splitter.setChildrenCollapsible(
        False
    )

    # 左右の境界線
    content_splitter.setHandleWidth(6)

    # -------------------------------------
    #  左側：操作パネル
    # -------------------------------------

    left_scroll = QtWidgets.QScrollArea()

    left_scroll.setObjectName("leftScrollArea")

    left_scroll.setWidgetResizable(True)

    left_scroll.setMinimumWidth(420)


    left_scroll.setToolTip(
        "検証・自動修正・FBX書き出しなどの操作を行います。"
    )

    left_panel = QtWidgets.QWidget()

    left_panel.setObjectName("leftPanel")


    left_layout = QtWidgets.QVBoxLayout(
        left_panel
    )

    left_layout.setContentsMargins(
        4,
        4,
        12,
        4
    )

    left_layout.setSpacing(16)

    # 操作パネルをスクロール領域に設定
    left_scroll.setWidget(
        left_panel
    )

    # -------------------------------------
    #  右側：結果表示パネル
    # -------------------------------------

    right_panel = QtWidgets.QWidget()

    right_panel.setObjectName("rightPanel")


    right_layout = QtWidgets.QVBoxLayout(
        right_panel
    )

    right_layout.setContentsMargins(
        12,
        4,
        4,
        4
    )

    right_layout.setSpacing(10)

    # -------------------------------------
    #  左右パネルをSplitterに登録
    # -------------------------------------
    content_splitter.addWidget(
        left_scroll
    )

    content_splitter.addWidget(
        right_panel
    )

    # 左右のサイズ比率
    content_splitter.setStretchFactor(
        0,
        1
    )

    content_splitter.setStretchFactor(
        1,
        1
    )

    # 初期幅：左500px、右600px
    content_splitter.setSizes(
        [500,600]
    )

    # =====================================
    # 01. 項目検証機能
    # =====================================

    validation_group = QtWidgets.QGroupBox(
        "01 / 項目検証機能"
    )

    validation_group.setToolTip(
        "選択したアセットの品質を確認する機能です。\n"
        "個別チェックまたは全項目一括チェックを実行できます。"
    )

    validation_layout = QtWidgets.QGridLayout(
        validation_group
    )

    validation_layout.setContentsMargins(
        14,
        24,
        14,
        14
    )

    validation_layout.setSpacing(10)

    # -------------------------------------
    # 全項目チェック
    # -------------------------------------

    all_button = QtWidgets.QPushButton(
        "全項目一括チェック"
    )

    all_button.setObjectName(
        "allCheckButton"
    )

    all_button.setToolTip(
        "選択したメッシュに対して5種類の検証を一括実行します。\n\n"
        "命名規則・Transform・Construction History・N-gon・UVを確認します。\n"
        "検証結果は下の結果表示欄に出力されます。"
    )

    all_button.clicked.connect(

        lambda checked=False:

            run_all_validations(
                result_view,
                validation_checks
            )

    )

    validation_layout.addWidget(
        all_button,
        0,
        0,
        1,
        2
    )

    # -------------------------------------
    # 個別検証ボタンの説明
    # -------------------------------------

    validation_tooltips = {

        "命名規則":

            "Static Meshの名前が命名規則に従っているか検証します。\n"
            "例：SM_Rock、SM_Tree",

        "Transform":

            "Translate・Rotate・Scaleを検証します。\n"
            "Freeze Transformが適切に実行されているか確認します。",

        "Construction History":

            "メッシュに残っているConstruction Historyを検証します。\n"
            "不要なモデリング履歴が残っていないか確認します。",

        "N-gon":

            "5頂点以上のポリゴンが存在するか検証します。\n"
            "N-gonがあるメッシュを検出します。",

        "UV":

            "メッシュにUVが存在するか検証します。\n"
            "UVが存在しないメッシュを検出します。"

    }

    # -------------------------------------
    # 個別検証ボタン
    # -------------------------------------

    for index, (label, check_function) in enumerate(
        validation_checks
    ):

        button = QtWidgets.QPushButton(label)

        button.setObjectName(
            "checkButton"
        )

        button.setToolTip(
            validation_tooltips.get(
                label,
                "選択したオブジェクトを検証します。"
            )
        )

        button.clicked.connect(

            lambda checked=False,
            func=check_function,
            check_title=label:

                run_validation(
                    result_view,
                    func,
                    check_title
                )

        )

        row = 1 + index // 2

        column = index % 2

        validation_layout.addWidget(
            button,
            row,
            column
        )

    left_layout.addWidget(
        validation_group
    )

    # =====================================
    # 02. 自動修正機能
    # =====================================

    auto_fix_group = QtWidgets.QGroupBox(
        "02 / 自動修正機能"
    )

    auto_fix_group.setToolTip(
        "選択したメッシュの問題を自動的に修正します。\n"
        "修正内容によっては元に戻せない場合があります。"
    )

    auto_fix_layout = QtWidgets.QGridLayout(
        auto_fix_group
    )

    auto_fix_layout.setContentsMargins(
        14,
        24,
        14,
        14
    )

    auto_fix_layout.setSpacing(10)

    # -------------------------------------
    # Transform自動修正
    # -------------------------------------

    transform_fix_button = QtWidgets.QPushButton(
        "Transform自動修正・再検証"
    )

    transform_fix_button.setObjectName(
        "fixButton"
    )

    transform_fix_button.setToolTip(
        "選択したメッシュのTranslate・Rotate・Scaleを修正します。\n"
        "実行前に確認ダイアログが表示されます。\n"
        "修正後は自動的に再検証します。"
    )

    transform_fix_button.clicked.connect(

        lambda checked=False:

            run_transform_auto_fix(
                result_view,
                validation_checks,
                WINDOW
            )

    )

    # -------------------------------------
    # Construction History自動修正
    # -------------------------------------

    history_fix_button = QtWidgets.QPushButton(
        "Construction History削除・再検証"
    )

    history_fix_button.setObjectName(
        "fixButton"
    )

    history_fix_button.setToolTip(
        "選択したメッシュのConstruction Historyを削除します。\n"
        "対応対象外の履歴は削除せずスキップします。\n"
        "削除前に確認ダイアログが表示されます。"
    )

    history_fix_button.clicked.connect(

        lambda checked=False:

            run_history_auto_fix(
                result_view,
                validation_checks,
                WINDOW
            )

    )

    # -------------------------------------
    # 命名規則自動修正
    # -------------------------------------

    name_fix_button = QtWidgets.QPushButton(
        "命名規則自動修正・再検証"
    )

    name_fix_button.setObjectName(
        "fixButton"
    )

    name_fix_button.setToolTip(
        "命名規則に違反したStatic Meshの名前にSM_を追加します。\n"
        "例：Rock → SM_Rock\n"
        "修正後は自動的に再検証します。"
    )

    name_fix_button.clicked.connect(

        lambda checked=False:

            run_name_auto_fix(
                result_view,
                validation_checks,
                WINDOW
            )

    )

    # -------------------------------------
    # ボタン配置
    # -------------------------------------

    auto_fix_layout.addWidget(
        transform_fix_button,
        0,
        0
    )

    auto_fix_layout.addWidget(
        history_fix_button,
        0,
        1
    )

    auto_fix_layout.addWidget(
        name_fix_button,
        1,
        0,
        1,
        2
    )

    left_layout.addWidget(
        auto_fix_group
    )

    # =====================================
    # 03. FBX書き出し・UE連携
    # =====================================

    export_group = QtWidgets.QGroupBox(
        "03 / FBX書き出し・UE連携"
    )

    export_group.setToolTip(
        "アセットをFBXとして書き出します。\n"
        "UE連携を選択すると、Unreal Engineへ直接インポートします。"
    )

    export_layout = QtWidgets.QVBoxLayout(
        export_group
    )

    export_layout.setContentsMargins(
        14,
        24,
        14,
        14
    )

    export_layout.setSpacing(10)

    # -------------------------------------
    # 書き出しモード
    # -------------------------------------

    mode_label = QtWidgets.QLabel(
        "書き出しモード"
    )

    mode_label.setObjectName(
        "ueDestinationLabel"
    )

    mode_label.setToolTip(
        "書き出し前にアセット検証を行うか選択します。"
    )

    export_mode_combo = QtWidgets.QComboBox()

    export_mode_combo.setObjectName(
        "exportModeCombo"
    )

    export_mode_combo.addItem(
        "厳格チェック",
        "strict"
    )

    export_mode_combo.addItem(
        "クイックモード",
        "quick"
    )

    # 初期状態は厳格チェック
    export_mode_combo.setCurrentIndex(0)

    export_mode_combo.setToolTip(
        "厳格チェック：5種類の検証を実行し、すべてOKの場合だけ書き出します。\n\n"
        "クイックモード：検証を省略して、そのままFBXを書き出します。"
    )

    mode_layout = QtWidgets.QHBoxLayout()

    mode_layout.addWidget(
        mode_label
    )

    mode_layout.addWidget(
        export_mode_combo,
        1
    )

    export_layout.addLayout(
        mode_layout
    )

    # -------------------------------------
    # モード説明
    # -------------------------------------

    mode_description = QtWidgets.QLabel()

    mode_description.setObjectName(
        "modeDescriptionLabel"
    )

    mode_description.setWordWrap(True)

    def update_mode_description():

        current_mode = export_mode_combo.currentData()

        if current_mode == "strict":

            mode_description.setText(

                "品質優先：命名規則・Transform・History・"
                "N-gon・UVを検証します。\n"
                "問題が検出された場合、書き出しを停止します。"

            )

        else:

            mode_description.setText(

                "速度優先：アセット検証を省略し、"
                "すぐにFBXを書き出します。\n"
                "検証を通していないアセットが出力される可能性があります。"

            )

    export_mode_combo.currentIndexChanged.connect(
        update_mode_description
    )

    update_mode_description()

    mode_description.setToolTip(
        "現在選択している書き出しモードの動作説明です。"
    )

    export_layout.addWidget(
        mode_description
    )

    # -------------------------------------
    # UE保存先
    # -------------------------------------

    destination_layout = QtWidgets.QHBoxLayout()

    destination_label = QtWidgets.QLabel(
        "UE保存先"
    )

    destination_label.setObjectName(
        "ueDestinationLabel"
    )

    destination_label.setToolTip(
        "Unreal EngineのContent Browser内での保存先です。"
    )

    ue_destination_input = QtWidgets.QLineEdit(
        "/Game/MayaImports"
    )

    ue_destination_input.setObjectName(
        "ueDestinationInput"
    )

    ue_destination_input.setPlaceholderText(
        "例：/Game/Environment/Rocks"
    )

    ue_destination_input.setToolTip(
        "UEのContent Browser内の保存先を指定します。\n"
        "Windowsのフォルダパスではなく、/Game/から始まるパスを入力してください。"
    )

    destination_layout.addWidget(
        destination_label
    )

    destination_layout.addWidget(
        ue_destination_input,
        1
    )

    export_layout.addLayout(
        destination_layout
    )

    # -------------------------------------
    # FBX単体書き出し
    # -------------------------------------

    export_button = QtWidgets.QPushButton(
        "FBXを書き出す"
    )

    export_button.setObjectName(
        "exportButton"
    )

    export_button.setToolTip(
        "選択したアセットをFBXとして書き出します。\n"
        "上の書き出しモードに従って検証を行います。\n"
        "UEへのインポートは行いません。"
    )

    export_button.clicked.connect(

        lambda checked=False:

            run_validate_and_export(
                result_view,
                validation_checks,
                export_mode_combo
            )

    )

    export_layout.addWidget(
        export_button
    )

    # -------------------------------------
    # UEへ送信
    # -------------------------------------

    export_to_ue_button = QtWidgets.QPushButton(
        "FBXを書き出してUEへ送信"
    )

    export_to_ue_button.setObjectName(
        "sendToUEButton"
    )

    export_to_ue_button.setToolTip(
        "選択したアセットをFBXとして書き出し、\n"
        "起動中のUnreal Engineへ自動インポートします。\n\n"
        "上の書き出しモードに従って検証を行います。"
    )

    export_to_ue_button.clicked.connect(

        lambda checked=False:

            run_validate_export_and_import(
                result_view,
                validation_checks,
                ue_destination_input,
                export_mode_combo
            )

    )

    export_layout.addWidget(
        export_to_ue_button
    )

    left_layout.addWidget(
        export_group
    )

    # 左側の余白
    left_layout.addStretch(1)

    # =====================================
    # 04. 検証結果表示
    # =====================================

    report_group = QtWidgets.QGroupBox(
        "04 / 検証結果表示"
    )

    report_group.setToolTip(
        "検証・自動修正・FBX書き出し・UEインポートの結果を表示します。"
    )

    report_layout = QtWidgets.QVBoxLayout(
        report_group
    )

    report_layout.setContentsMargins(
        14, 24, 14, 14
    )

    report_layout.setSpacing(10)


    # -------------------------------------
    # 検証結果表示ウィジェット
    # -------------------------------------

    result_view = validation_result_widget.StatusResultWidget()

    result_view.setObjectName(
        "resultView"
    )

    result_view.setReadOnly(True)

    result_view.setPlaceholderText(
        "検証・自動修正・FBX書き出し・UEインポートの結果がここに表示されます。"
    )

    result_view.setToolTip(
        "検証結果を一覧表示します。\n"
        "OK・NG・WARNINGなどの状態を色付きバッジで確認できます。\n"
        "下部には実行ログと詳細情報が表示されます。"
    )


    report_layout.addWidget(
        result_view,
        1
    )


    # -------------------------------------
    # 右側パネルに追加
    # -------------------------------------

    right_layout.addWidget(
        report_group,
        1
    )

    # =====================================
    # 左右レイアウトをメイン画面に追加
    # =====================================

    main_layout.addWidget(
        content_splitter,
        1
    )

    # =====================================
    #  デザイン
    # =====================================

    WINDOW.setStyleSheet("""

        QWidget#ExportToolkitTestWindow {
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
            padding-bottom: 8px;
            border-bottom: 1px solid #354253;
        }

        QGroupBox {
            color: #68C8DC;
            font-size: 12px;
            font-weight: bold;
            border: 1px solid #354253;
            border-radius: 8px;
            margin-top: 12px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 6px;
            background-color: #171D27;
        }

        QPushButton#allCheckButton {
            background-color: #24647A;
            color: #FFFFFF;
            font-size: 13px;
            font-weight: bold;
            padding: 14px;
            border: none;
            border-radius: 6px;
        }

        QPushButton#allCheckButton:hover {
            background-color: #32849C;
        }

        QPushButton#checkButton {
            background-color: #252F3C;
            color: #D6E1EA;
            font-size: 12px;
            padding: 12px 8px;
            border: 1px solid #354253;
            border-radius: 6px;
        }

        QPushButton#checkButton:hover {
            background-color: #354759;
            border: 1px solid #68C8DC;
        }

        QPushButton#fixButton {
            background-color: #35483F;
            color: #D7E9DF;
            font-size: 12px;
            font-weight: bold;
            padding: 12px 8px;
            border: 1px solid #4E7561;
            border-radius: 6px;
        }

        QPushButton#fixButton:hover {
            background-color: #416A55;
            border: 1px solid #72B993;
        }

        QPushButton#fixButton:pressed {
            background-color: #294638;
        }

        QLabel#ueDestinationLabel {
            color: #D6E1EA;
            font-size: 12px;
            font-weight: bold;
        }

        QLineEdit#ueDestinationInput {
            background-color: #222B35;
            color: #D6E1EA;
            font-size: 12px;
            padding: 9px;
            border: 1px solid #354253;
            border-radius: 5px;
        }

        QLineEdit#ueDestinationInput:focus {
            border: 1px solid #68C8DC;
        }

        QComboBox#exportModeCombo {
            background-color: #252F3C;
            color: #F0F3F7;
            font-size: 12px;
            padding: 8px;
            border: 1px solid #354253;
            border-radius: 5px;
        }

        QComboBox#exportModeCombo:hover {
            border: 1px solid #68C8DC;
        }

        QLabel#modeDescriptionLabel {
            color: #AAB6C5;
            font-size: 11px;
            padding: 8px;
            background-color: #222B35;
            border: 1px solid #354253;
            border-radius: 5px;
        }

        QPushButton#exportButton {
            background-color: #24647A;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: bold;
            padding: 15px;
            border: none;
            border-radius: 6px;
        }

        QPushButton#exportButton:hover {
            background-color: #32849C;
        }

        QPushButton#exportButton:pressed {
            background-color: #19495C;
        }

        QPushButton#sendToUEButton {
            background-color: #574C78;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: bold;
            padding: 15px;
            border: none;
            border-radius: 6px;
        }

        QPushButton#sendToUEButton:hover {
            background-color: #70619A;
        }

        QPushButton#sendToUEButton:pressed {
            background-color: #44395F;
        }

        QToolTip {
            background-color: #222B35;
            color: #F0F3F7;
            font-size: 11px;
            padding: 8px;
            border: 1px solid #68C8DC;
            border-radius: 5px;
        }
                         
        QSplitter#mainContentSplitter::handle {
        background-color: #354253;
        width: 6px;
        }

        QSplitter#mainContentSplitter::handle:hover {
        background-color: #68C8DC;
        }

        QScrollArea {
        border: none;
        background-color: transparent;
        }
                         
        QWidget#leftPanel {
        background-color: #171D27;
        }

        QWidget#rightPanel {
        background-color: #171D27;
        }

        QSplitter#mainContentSplitter::handle {
            background-color: #354253;
            width: 6px;
        }

        QSplitter#mainContentSplitter::handle:hover {
            background-color: #68C8DC;
        }

        QLabel#resultDetailLabel {
        color: #68C8DC;
        font-size: 11px;
        font-weight: bold;
        padding-top: 5px;
        }

        QPlainTextEdit#resultLogView {
        background-color: #222B35;
        color: #D6E1EA;
        font-size: 11px;
        border: 1px solid #354253;
        border-radius: 5px;
        padding: 10px;
        }
        
    """)

    return WINDOW


# =========================================
# 単独ウィンドウで起動する場合
# =========================================

def show_ui():

    global WINDOW

    # -------------------------------------
    # Mayaのメインウィンドウ
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
    # 古いウィンドウを削除
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
    # ツール本体を作り、独立したウィンドウとして表示
    # -------------------------------------

    WINDOW = create_widget(
        maya_window
    )

    WINDOW.setWindowFlags(
        WINDOW_FLAG
    )

    WINDOW.show()

    print(
        "Maya → Unreal Export Toolkitを起動しました。"
    )

    return WINDOW