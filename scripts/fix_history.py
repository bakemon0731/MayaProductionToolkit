import maya.cmds as cmds


# =========================================
# 01. 自動削除してよい履歴ノードの判定
# =========================================

# ポリゴンを編集したときに作られるノードは、
# 型名がすべて "poly" で始まる。
#   例: polyCube / polyExtrudeFace / polyUnite(Combine) /
#       polyBevel3 / polyMergeVert / polyTweak ...
# これらは「操作の記録」であり、削除しても
# 現在の形状は結果としてメッシュに残る。
MODELING_PREFIX = "poly"

# "poly" で始まらないが、ポリゴン編集に付随して作られるノード
MODELING_EXTRA_TYPES = {
    "groupParts",
    "createColorSet",
    "deleteColorSet",
}

# 注意:
# skinCluster / blendShape / cluster などのデフォーマーや、
# アニメーションのノード(animCurve など)はここに含めない。
# 削除すると見た目や動作が変わる可能性があるため、
# 今までどおり「対象外」として自動削除を見送る。


def is_modeling_history_type(node_type):
    """ポリゴン編集の履歴ノード(自動削除してよい種類)ならTrueを返す。"""

    if node_type.startswith(MODELING_PREFIX):
        return True

    return node_type in MODELING_EXTRA_TYPES


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
        if not is_modeling_history_type(node_type)
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

def fix_selected_history():
    """選択されたメッシュのポリゴンモデリング履歴を削除する。"""

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    results = []

    # オブジェクトが選択されていない場合
    if not selected:
        return [{
            "object": None,
            "status": "ERROR",
            "message": "オブジェクトが選択されていません"
        }]

    for obj in selected:
        try:
            analysis = analyze_history(obj)

            # メッシュ以外はスキップ
            if not analysis["mesh_shapes"]:
                results.append({
                    "object": obj,
                    "status": "SKIP",
                    "message": "メッシュShapeがありません"
                })
                continue

            # 既に履歴がない場合
            if not analysis["history"]:
                results.append({
                    "object": obj,
                    "status": "OK",
                    "message": "Construction Historyはありません"
                })
                continue

            # 許可する種類以外の履歴があれば、自動削除しない
            if analysis["unsupported"]:
                results.append({
                    "object": obj,
                    "status": "SKIP",
                    "message": (
                        "ポリゴンモデリング以外の履歴があるため、"
                        "自動削除を見送りました"
                    ),
                    "details": [
                        {
                            "node": node,
                            "type": analysis["types"][node]
                        }
                        for node in analysis["unsupported"]
                    ]
                })
                continue

            # 削除前の形状情報を記録
            before = get_geometry_stats(obj)

            before_bounds = before["bounds"]

            before_vertices = before["vertices"]

            before_faces = before["faces"]

            # 削除前のマテリアル割り当てを記録
            before_shading = get_shading_engines(obj)

            # Construction Historyを削除
            cmds.delete(
                obj,
                constructionHistory=True
            )

            # 削除後の形状情報を取得
            after_history = get_history_nodes(obj)

            after_shading = get_shading_engines(obj)

            after = get_geometry_stats(obj)

            after_bounds = after["bounds"]

            after_vertices = after["vertices"]

            after_faces = after["faces"]

            # ワールド境界の差を比較
            differences = [
                abs(before_bounds[i] - after_bounds[i])
                for i in range(6)
            ]

            bounds_unchanged = all(
                difference < 0.0001
                for difference in differences
            )

            # 頂点数と面数が維持されているか確認
            geometry_unchanged = (
                before_vertices == after_vertices
                and before_faces == after_faces
            )

            # マテリアルの割り当てが維持されているか確認
            shading_unchanged = (
                before_shading == after_shading
            )

            # 履歴がなくなり、形状・マテリアルも維持されていれば成功
            if (
                not after_history
                and bounds_unchanged
                and geometry_unchanged
                and shading_unchanged
            ):
                ok_result = {
                    "object": obj,
                    "status": "OK",
                    "message": (
                        "Construction Historyを削除しました。"
                        "ワールド境界・頂点数・面数・"
                        "マテリアル割り当ては維持されています"
                    )
                }

                # 履歴ではないために残ったノードがあれば、隠さず知らせる
                kept_nodes = [
                    node
                    for node in get_raw_history(obj)
                    if node not in after_history
                ]

                if kept_nodes:
                    ok_result["details"] = [{
                        "残したノード(履歴ではないため問題なし)": ", ".join(
                            "{} ({})".format(
                                node,
                                cmds.nodeType(node)
                            )
                            for node in kept_nodes
                        )
                    }]

                results.append(ok_result)

            else:
                results.append({
                    "object": obj,
                    "status": "ERROR",
                    "message": (
                        "削除後の履歴または形状が"
                        "期待どおりではありません"
                    ),
                    "details": {
                        "残っている履歴": (
                            ", ".join(
                                "{} ({})".format(
                                    node,
                                    cmds.nodeType(node)
                                )
                                for node in after_history
                            )
                            or "なし"
                        ),
                        "境界ボックス": (
                            "変化なし"
                            if bounds_unchanged
                            else "{} -> {}".format(
                                [round(v, 4) for v in before_bounds],
                                [round(v, 4) for v in after_bounds]
                            )
                        ),
                        "頂点数": "{} -> {}".format(
                            before_vertices,
                            after_vertices
                        ),
                        "面数": "{} -> {}".format(
                            before_faces,
                            after_faces
                        ),
                        "マテリアル割り当て": "{} -> {}".format(
                            before_shading,
                            after_shading
                        )
                    }
                })

        except Exception as error:
            results.append({
                "object": obj,
                "status": "ERROR",
                "message": str(error)
            })

    return results