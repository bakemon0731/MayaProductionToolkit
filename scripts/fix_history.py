import hashlib
import math
import struct

import maya.cmds as cmds
import maya.api.OpenMaya as om


# =========================================
# 01. 自動削除してよい履歴ノードの判定
# =========================================

MODELING_PREFIX = "poly"

# "poly" で始まらないが、ポリゴン編集に付随して作られるノード
MODELING_EXTRA_TYPES = {
    "groupParts",
    "createColorSet",
    "deleteColorSet",
}


def _flatten_matrix_value(value):
    """cmds.getAttr() のmatrix戻り値を16要素のfloat配列にする。"""

    while (
        isinstance(value, (tuple, list))
        and len(value) == 1
        and isinstance(value[0], (tuple, list))
    ):
        value = value[0]

    if not isinstance(value, (tuple, list)) or len(value) != 16:
        raise ValueError("16要素のMatrixを取得できません")

    matrix = [float(component) for component in value]

    if not all(math.isfinite(component) for component in matrix):
        raise ValueError("Matrixに有限でない値が含まれています")

    return matrix


def _is_safe_transform_geometry(node, target):
    """限定した条件を満たす transformGeometry だけを自動削除候補にする。

    条件:
      - inputGeometry の入力元が1つで、対象の履歴チェーン内にある
      - 入力元が既知のポリゴンモデリング履歴
      - outputGeometry の出力先が対象Transform配下の表示Mesh Shape.inMeshだけ
      - transform / invertTransform / freezeNormals / reverseNormals に外部入力がない
      - invertTransform=False、freezeNormals=0、reverseNormals=False
      - Matrixが有限値で、線形部分が特異行列ではない

    MatrixがIdentityであることは要求しない。静的な変換は
    constructionHistory=True による履歴削除時に最終ジオメトリへ焼き込まれ、
    その結果は fix_object_history() の前後比較で検証する。
    """

    try:
        if not cmds.objExists(node) or cmds.nodeType(node) != "transformGeometry":
            return False

        target = _resolve_transform(target)
        target_shapes = set(get_mesh_shapes(target))
        if not target_shapes:
            return False

        # inputGeometry の入力元が一つであること。
        input_sources = cmds.listConnections(
            node + ".inputGeometry",
            source=True,
            destination=False,
            plugs=True
        ) or []
        if len(input_sources) != 1:
            return False

        source_node = input_sources[0].split(".", 1)[0]
        if not cmds.objExists(source_node):
            return False

        source_type = cmds.nodeType(source_node)
        if not (
            source_type.startswith(MODELING_PREFIX)
            or source_type in MODELING_EXTRA_TYPES
        ):
            return False

        # 入力元が実際にこの対象オブジェクトの履歴に含まれること。
        target_history = set(get_history_nodes(target))
        if source_node not in target_history:
            return False

        # 出力先は対象の表示Shape.inMeshひとつだけ。
        output_destinations = cmds.listConnections(
            node + ".outputGeometry",
            source=False,
            destination=True,
            plugs=True
        ) or []
        if len(output_destinations) != 1:
            return False

        destination_node, separator, destination_attr = output_destinations[0].partition(".")
        if not separator or destination_attr.split("[")[0] != "inMesh":
            return False

        destination_shapes = cmds.ls(
            destination_node,
            long=True,
            type="mesh"
        ) or []
        if len(destination_shapes) != 1 or destination_shapes[0] not in target_shapes:
            return False

        # 外部ノードが設定値を駆動するケースは対象外。
        for attribute in (
            "transform",
            "invertTransform",
            "freezeNormals",
            "reverseNormals",
        ):
            incoming = cmds.listConnections(
                node + "." + attribute,
                source=True,
                destination=False,
                plugs=True
            ) or []
            if incoming:
                return False

        if bool(cmds.getAttr(node + ".invertTransform")):
            return False
        if int(cmds.getAttr(node + ".freezeNormals")) != 0:
            return False
        if bool(cmds.getAttr(node + ".reverseNormals")):
            return False

        matrix = _flatten_matrix_value(cmds.getAttr(node + ".transform"))

        # Mayaの4x4アフィン行列として扱えることを確認。
        if any(abs(matrix[index]) > 1.0e-8 for index in (3, 7, 11)):
            return False
        if abs(matrix[15] - 1.0) > 1.0e-8:
            return False

        # 3x3線形部分の行列式。ゼロスケール等の退化変換は拒否する。
        a, b, c = matrix[0], matrix[1], matrix[2]
        d, e, f = matrix[4], matrix[5], matrix[6]
        g, h, i = matrix[8], matrix[9], matrix[10]
        determinant = (
            a * (e * i - f * h)
            - b * (d * i - f * g)
            + c * (d * h - e * g)
        )
        if abs(determinant) <= 1.0e-12:
            return False

        return True

    except Exception:
        # Maya APIの取得に失敗した場合は安全側に倒して自動修正しない。
        return False


def is_modeling_history_type(node_type, node=None, target=None):
    """自動削除を許可する履歴ノードならTrueを返す。

    poly系と既存の補助ノードは従来どおり許可する。
    transformGeometryは接続・設定を検査した場合だけ許可する。
    """

    if node_type.startswith(MODELING_PREFIX):
        return True

    if node_type in MODELING_EXTRA_TYPES:
        return True

    if node_type == "transformGeometry" and node and target:
        return _is_safe_transform_geometry(node, target)

    return False


# 「履歴」としては扱わないノード(マテリアル割り当ての管理用)。
#
#   shadingEngine : マテリアルの割り当て先(例: initialShadingGroup)
#   groupId       : 面ごとのマテリアル割り当てを管理するID
#
# どちらもCombineなどのあとに listHistory の結果へ混ざるが、
# モデリング操作の記録ではない。実際に、Mayaの
# 「Construction Historyの削除」を実行しても groupId は
# 残り続けるため、「履歴が残っている」とは判定しない。
NON_HISTORY_TYPES = {
    "shadingEngine",
    "groupId",
}


def get_raw_history(obj):
    """listHistoryの結果をそのまま返す(除外なし)。"""

    return cmds.listHistory(
        obj,
        pruneDagObjects=True
    ) or []


def get_history_nodes(obj):
    """Construction Historyのノード一覧を返す(割り当て管理用は除く)。"""

    return [
        node
        for node in get_raw_history(obj)
        if cmds.nodeType(node) not in NON_HISTORY_TYPES
    ]


def get_shading_engines(obj):
    """オブジェクトに割り当てられているマテリアル(shadingEngine)を返す。"""

    shapes = cmds.listRelatives(
        obj,
        shapes=True,
        noIntermediate=True,
        fullPath=True
    ) or []

    if not shapes:
        return []

    engines = cmds.listConnections(
        shapes,
        type="shadingEngine"
    ) or []

    return sorted(set(engines))


def get_mesh_shapes(obj):
    """実際に表示されるメッシュShapeを返す(中間オブジェクトは除く)。

    Combineの履歴が残っている間は、結合前の元メッシュが
    「中間オブジェクト」として同じTransformの下に残ることがある。
    Transformをまとめて数えると、削除の前後で頂点数・面数が
    食い違って見えるため、中間オブジェクトを除いたShapeだけで数える。
    """

    shapes = cmds.listRelatives(
        obj,
        shapes=True,
        noIntermediate=True,
        fullPath=True
    ) or []

    return [
        shape
        for shape in shapes
        if cmds.nodeType(shape) == "mesh"
    ]


def get_geometry_stats(obj):
    """境界ボックス・頂点数・面数を、表示メッシュShapeだけで調べる。"""

    shapes = get_mesh_shapes(obj)

    if not shapes:
        return {"bounds": [0] * 6, "vertices": 0, "faces": 0}

    vertices = 0

    faces = 0

    for shape in shapes:
        vertices += cmds.polyEvaluate(shape, vertex=True)
        faces += cmds.polyEvaluate(shape, face=True)

    return {
        "bounds": cmds.exactWorldBoundingBox(shapes),
        "vertices": vertices,
        "faces": faces
    }


# =========================================
# 02. 履歴の調査(UIと自動修正で共通に使う)
# =========================================

def analyze_history(obj):
    """1つのオブジェクトの履歴を調べ、結果を辞書で返す。

    戻り値:
        mesh_shapes : メッシュShapeのリスト
        history     : 履歴ノードのリスト
        types       : {ノード名: ノードの型}
        unsupported : 自動削除できない履歴ノードのリスト
    """

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

    history = get_history_nodes(obj)

    history_types = {
        node: cmds.nodeType(node)
        for node in history
    }

    unsupported_nodes = [
        node
        for node, node_type in history_types.items()
        if not is_modeling_history_type(node_type, node=node, target=obj)
    ]

    return {
        "mesh_shapes": mesh_shapes,
        "history": history,
        "types": history_types,
        "unsupported": unsupported_nodes
    }


# =========================================
# 03. 履歴の削除
# =========================================

def _resolve_transform(obj):
    """DAGフルパスからTransformを一意に取得する。"""

    if not obj or not cmds.objExists(obj):
        raise RuntimeError("修正対象のオブジェクトが見つかりません。")

    matches = cmds.ls(
        obj,
        long=True,
        type="transform"
    ) or []

    if len(matches) != 1:
        raise RuntimeError(
            "修正対象を一意に特定できません。DAGフルパスを確認してください。"
        )

    return matches[0]


def get_world_mesh_signature(obj):
    """表示対象の全Mesh Shapeについて、ワールド頂点座標の署名を作る。

    全頂点の座標を 0.0001 単位で量子化してSHA-256へ追加する。
    頂点数・Shapeパスも署名に含める。
    """

    shapes = get_mesh_shapes(obj)
    signatures = []

    for shape in shapes:
        selection = om.MSelectionList()
        selection.add(shape)
        dag_path = selection.getDagPath(0)
        mesh_fn = om.MFnMesh(dag_path)
        points = mesh_fn.getPoints(om.MSpace.kWorld)

        digest = hashlib.sha256()
        digest.update(shape.encode("utf-8"))
        digest.update(struct.pack("<Q", len(points)))

        for point in points:
            quantized = (
                int(round(float(point.x) * 10000.0)),
                int(round(float(point.y) * 10000.0)),
                int(round(float(point.z) * 10000.0)),
            )
            digest.update(struct.pack("<qqq", *quantized))

        signatures.append((shape, len(points), digest.hexdigest()))

    return tuple(signatures)


def _bounds_unchanged(before_bounds, after_bounds, tolerance=0.0001):
    if len(before_bounds) != 6 or len(after_bounds) != 6:
        return False

    return all(
        abs(float(before_bounds[index]) - float(after_bounds[index])) < tolerance
        for index in range(6)
    )


def get_history_fix_block_reason(obj):
    """自動修正を実行できない理由を返す。実行可能なら空文字列。"""

    try:
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            return "Reference内のオブジェクトは自動修正できません"
    except Exception:
        # Reference情報を判定できない状態では処理を続行しない。
        return "Reference状態を確認できません"

    # Transformだけでなく、表示対象のShapeもロック状態を確認する。
    nodes_to_check = [obj] + get_mesh_shapes(obj)

    try:
        for node in nodes_to_check:
            lock_states = cmds.lockNode(node, query=True, lock=True) or []
            if any(lock_states):
                return "ノードがロックされています: {}".format(node)
    except Exception:
        return "ノードのロック状態を確認できません"

    try:
        if not cmds.undoInfo(query=True, state=True):
            return "MayaのUndoが無効なため、安全に修正できません"
    except Exception:
        return "MayaのUndo状態を確認できません"

    return ""


def fix_object_history(obj):
    """指定した1つのTransformだけConstruction Historyを修正する。

    現在のMaya選択状態には依存しない。
    ポリゴンモデリング系の許可済み履歴だけを対象とし、削除後に
    履歴・ワールド頂点・境界ボックス・頂点数・面数・マテリアルを検証する。
    検証に失敗した場合はUndo Chunkを戻す。
    """

    target = obj
    chunk_open = False
    delete_attempted = False

    try:
        target = _resolve_transform(obj)

        analysis = analyze_history(target)

        block_reason = get_history_fix_block_reason(target)
        if block_reason:
            return {
                "object": target,
                "status": "SKIP",
                "message": block_reason
            }

        if not analysis["mesh_shapes"]:
            return {
                "object": target,
                "status": "SKIP",
                "message": "メッシュShapeがありません"
            }

        if not analysis["history"]:
            return {
                "object": target,
                "status": "OK",
                "message": "Construction Historyは既にありません"
            }

        if analysis["unsupported"]:
            details = [
                {
                    "node": node,
                    "type": analysis["types"][node]
                }
                for node in analysis["unsupported"]
            ]
            return {
                "object": target,
                "status": "SKIP",
                "message": (
                    "ポリゴンモデリング以外の履歴が含まれるため、"
                    "自動削除を見送りました"
                ),
                "details": details
            }

        # 削除前の状態を記録する。
        before = get_geometry_stats(target)
        before_signature = get_world_mesh_signature(target)
        before_shading = get_shading_engines(target)

        cmds.undoInfo(
            openChunk=True,
            chunkName="MPT_DeleteConstructionHistory"
        )
        chunk_open = True

        delete_attempted = True
        cmds.delete(
            target,
            constructionHistory=True
        )

        # 削除後の状態を検証する。
        after_analysis = analyze_history(target)
        after = get_geometry_stats(target)
        after_signature = get_world_mesh_signature(target)
        after_shading = get_shading_engines(target)

        bounds_ok = _bounds_unchanged(
            before["bounds"],
            after["bounds"]
        )
        counts_ok = (
            before["vertices"] == after["vertices"]
            and before["faces"] == after["faces"]
        )
        vertices_ok = before_signature == after_signature
        shading_ok = before_shading == after_shading
        history_cleared = not after_analysis["history"]

        if not all((bounds_ok, counts_ok, vertices_ok, shading_ok, history_cleared)):
            # Undoはチャンクを閉じてから実行する。
            cmds.undoInfo(closeChunk=True)
            chunk_open = False
            cmds.undo()

            # Undo後も元の履歴とジオメトリが戻ったか確認する。
            restored_analysis = analyze_history(target)
            restored_stats = get_geometry_stats(target)
            restored_signature = get_world_mesh_signature(target)
            restored_shading = get_shading_engines(target)

            rollback_ok = (
                restored_analysis["history"] == analysis["history"]
                and restored_signature == before_signature
                and restored_shading == before_shading
                and _bounds_unchanged(
                    before["bounds"],
                    restored_stats["bounds"]
                )
                and before["vertices"] == restored_stats["vertices"]
                and before["faces"] == restored_stats["faces"]
            )

            return {
                "object": target,
                "status": "ERROR",
                "message": (
                    "削除後の検証に失敗したため、Undoで処理を取り消しました"
                    if rollback_ok
                    else "削除後の検証に失敗し、Undo後の復元確認にも失敗しました"
                ),
                "details": {
                    "履歴削除": history_cleared,
                    "ワールド頂点": vertices_ok,
                    "境界ボックス": bounds_ok,
                    "頂点数・面数": counts_ok,
                    "マテリアル": shading_ok,
                    "Undo復元確認": rollback_ok
                }
            }

        cmds.undoInfo(closeChunk=True)
        chunk_open = False

        return {
            "object": target,
            "status": "OK",
            "message": (
                "Construction Historyを削除しました。"
                "ワールド頂点・境界ボックス・頂点数・面数・"
                "マテリアル割り当ては維持されています"
            ),
            "details": [
                "削除ノード数: {}".format(len(analysis["history"])),
                "ワールド頂点: 一致",
                "マテリアル割り当て: 一致"
            ]
        }

    except Exception as error:
        # 例外発生時もチャンクを閉じ、可能な限り今回の処理だけを戻す。
        if chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass
            chunk_open = False

        rollback_message = ""
        if delete_attempted:
            try:
                cmds.undo()
                rollback_message = "Undoを実行しました"
            except Exception as undo_error:
                rollback_message = "Undoにも失敗しました: {}".format(undo_error)

        return {
            "object": target,
            "status": "ERROR",
            "message": "Construction Historyの修正中にエラーが発生しました: {}".format(error),
            "details": rollback_message
        }


def fix_selected_history():
    """選択されたTransformに対する互換API。

    実際の修正処理はfix_object_historyへ委譲し、
    テーブルの個別修正と同じ安全確認・検証を利用する。
    """

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:
        return [{
            "object": None,
            "status": "ERROR",
            "message": "オブジェクトが選択されていません"
        }]

    return [
        fix_object_history(obj)
        for obj in selected
    ]
