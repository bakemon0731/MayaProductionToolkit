import re

import maya.cmds as cmds


# =========================================
# 01. 設定
# =========================================

REQUIRED_PREFIX = "SM_"


def build_fixed_name(object_name):
    """現在の命名規則に合う名前を生成する。

    validate_names.py の規則は「SM_ + 半角英数字」なので、
    Prefixを付けるだけでなく、Suffix内の不正文字も取り除く。
    """

    suffix = object_name

    if suffix.startswith(REQUIRED_PREFIX):
        suffix = suffix[len(REQUIRED_PREFIX):]

    suffix = re.sub(
        r"[^A-Za-z0-9]",
        "",
        suffix
    )

    if not suffix:
        suffix = "Mesh"

    return REQUIRED_PREFIX + suffix


# =========================================
# 02. メッシュ判定
# =========================================

def has_mesh_shape(obj):

    shapes = cmds.listRelatives(
        obj,
        shapes=True,
        noIntermediate=True,
        fullPath=True
    ) or []

    return any(
        cmds.nodeType(shape) == "mesh"
        for shape in shapes
    )


# =========================================
# 03. 1オブジェクトの命名規則を修正
# =========================================

def fix_object_name(obj):
    """DAGフルパスで指定された1つのTransform名を修正する。

    選択状態には依存しない。
    戻り値のobjectには、処理後のDAGフルパスを格納する。
    """

    try:

        if not obj or not cmds.objExists(obj):
            return {
                "object": obj or "不明",
                "status": "ERROR",
                "message": "修正対象のオブジェクトが見つかりません。",
                "details": []
            }

        # Transformとして一意に解決できるか確認
        matches = cmds.ls(
            obj,
            long=True,
            type="transform"
        ) or []

        if len(matches) != 1:
            return {
                "object": obj,
                "status": "ERROR",
                "message": (
                    "修正対象を一意に特定できません。"
                    "DAGフルパスを確認してください。"
                ),
                "details": [matches]
            }

        object_path = matches[0]
        object_name = object_path.split("|")[-1]

        # メッシュShapeの存在確認
        if not has_mesh_shape(object_path):
            return {
                "object": object_path,
                "status": "SKIP",
                "message": "メッシュShapeがありません。",
                "details": []
            }

        # 修正後の名前を作成
        new_name = build_fixed_name(object_name)

        # 生成された名前と現在の名前が同じなら、既に適合している。
        if new_name == object_name:
            return {
                "object": object_path,
                "status": "OK",
                "message": "すでに命名規則を満たしています。",
                "details": []
            }

        # 親階層を保持して、変更後のパスを特定できるようにする
        parent_path = object_path.rsplit("|", 1)[0]

        # オブジェクト名を変更
        renamed_name = cmds.rename(
            object_path,
            new_name
        )

        # cmds.rename()の戻り値は短い名前の場合があるため、
        # 元の親階層と組み合わせて変更後のパスを取得する。
        renamed_leaf = renamed_name.split("|")[-1]

        if parent_path:
            expected_path = parent_path + "|" + renamed_leaf
        else:
            expected_path = "|" + renamed_leaf

        renamed_paths = cmds.ls(
            expected_path,
            long=True,
            type="transform"
        ) or []

        if len(renamed_paths) != 1:
            raise RuntimeError(
                "変更後のオブジェクトを一意に取得できませんでした。"
            )

        renamed_path = renamed_paths[0]
        actual_name = renamed_path.split("|")[-1]

        return {
            "object": renamed_path,
            "status": "OK",
            "message": "命名規則を自動修正しました。",
            "details": [
                {
                    "変更前": object_name,
                    "変更後": actual_name,
                    "変更前パス": object_path,
                    "変更後パス": renamed_path
                }
            ]
        }

    except Exception as error:

        return {
            "object": obj or "不明",
            "status": "ERROR",
            "message": "命名規則の修正に失敗しました。",
            "details": [str(error)]
        }


# =========================================
# 04. 選択オブジェクトの命名規則を修正
# =========================================

def fix_selected_names():
    """選択されたTransformを1つずつ修正する互換用関数。"""

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:
        return [{
            "object": "不明",
            "status": "ERROR",
            "message": "オブジェクトが選択されていません。",
            "details": []
        }]

    return [
        fix_object_name(obj)
        for obj in selected
    ]
