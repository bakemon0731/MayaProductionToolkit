"""Maya Transform validation fixes.

This module provides both a per-object API for the result-table action and
an existing selection-based compatibility function.
"""

import hashlib
import struct

import maya.cmds as cmds
import maya.api.OpenMaya as om


# Transform validation uses this tolerance in validate_transforms.py.
TRANSFORM_TOLERANCE = 0.001

# World-space vertex positions are compared with a tighter tolerance.
WORLD_POSITION_TOLERANCE = 0.0001


# =========================================
# 01. Target resolution and mesh inspection
# =========================================

def _resolve_transform(obj):
    """Resolve one unambiguous transform from a DAG path or node name."""

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


def _get_mesh_shapes(transform_path):
    """Return non-intermediate mesh Shape DAG paths under the transform."""

    shapes = cmds.listRelatives(
        transform_path,
        shapes=True,
        noIntermediate=True,
        fullPath=True
    ) or []

    return [
        shape
        for shape in shapes
        if cmds.nodeType(shape) == "mesh"
    ]


def _capture_world_mesh_points(shape_paths):
    """Create a compact signature of every mesh vertex in world space.

    A SHA-256 digest is used instead of keeping every vertex in Python lists.
    This keeps memory usage much lower for large production meshes. Each
    coordinate is quantized at WORLD_POSITION_TOLERANCE before hashing.
    """

    snapshots = []

    for shape_path in shape_paths:
        selection = om.MSelectionList()
        selection.add(shape_path)
        dag_path = selection.getDagPath(0)

        mesh_fn = om.MFnMesh(dag_path)
        points = mesh_fn.getPoints(om.MSpace.kWorld)

        digest = hashlib.sha256()

        for point in points:
            quantized = (
                int(round(float(point.x) / WORLD_POSITION_TOLERANCE)),
                int(round(float(point.y) / WORLD_POSITION_TOLERANCE)),
                int(round(float(point.z) / WORLD_POSITION_TOLERANCE)),
            )
            digest.update(struct.pack("<qqq", *quantized))

        snapshots.append({
            "shape": shape_path,
            "vertex_count": len(points),
            "signature": digest.hexdigest(),
        })

    return tuple(snapshots)


def _compare_world_mesh_points(before, after):
    """Compare compact world-space vertex signatures."""

    if len(before) != len(after):
        return False

    for before_shape, after_shape in zip(before, after):
        if before_shape["shape"] != after_shape["shape"]:
            return False

        if before_shape["vertex_count"] != after_shape["vertex_count"]:
            return False

        if before_shape["signature"] != after_shape["signature"]:
            return False

    return True


# =========================================
# 02. Transform state and safety checks
# =========================================

def _read_transform_values(transform_path):
    """Read local Translate / Rotate / Scale values."""

    return {
        "translate": tuple(cmds.getAttr(transform_path + ".translate")[0]),
        "rotate": tuple(cmds.getAttr(transform_path + ".rotate")[0]),
        "scale": tuple(cmds.getAttr(transform_path + ".scale")[0]),
    }


def _is_transform_reset(values):
    """Return True when Translate/Rotate are zero and Scale is one."""

    translate_reset = all(
        abs(value) <= TRANSFORM_TOLERANCE
        for value in values["translate"]
    )

    rotate_reset = all(
        abs(value) <= TRANSFORM_TOLERANCE
        for value in values["rotate"]
    )

    scale_reset = all(
        abs(value - 1.0) <= TRANSFORM_TOLERANCE
        for value in values["scale"]
    )

    return translate_reset and rotate_reset and scale_reset


def _check_transform_is_editable(transform_path, shape_paths, values):
    """Reject cases where automatically freezing could damage a scene."""

    try:
        if cmds.referenceQuery(
            transform_path,
            isNodeReferenced=True
        ):
            return "参照アセットは自動修正できません。参照元で修正してください。"
    except RuntimeError:
        # Non-referenced local nodes can raise RuntimeError in some Maya builds.
        pass

    locked_nodes = cmds.lockNode(
        transform_path,
        query=True,
        lock=True
    ) or [False]

    if any(locked_nodes):
        return "Transformノードがロックされているため修正できません。"

    # Avoid changing channels driven by animation, constraints, or connections.
    channels = (
        "tx", "ty", "tz",
        "rx", "ry", "rz",
        "sx", "sy", "sz",
    )

    for channel in channels:
        plug = transform_path + "." + channel

        if cmds.getAttr(plug, lock=True):
            return "{} がロックされているため修正できません。".format(channel)

        incoming = cmds.listConnections(
            plug,
            source=True,
            destination=False,
            plugs=True
        ) or []

        if incoming:
            return (
                "{} に入力接続があります。アニメーションやConstraint等の"
                "接続を確認してください。"
            ).format(channel)

    # Negative or zero scales need artist review before freezing.
    for value in values["scale"]:
        if abs(value) <= TRANSFORM_TOLERANCE:
            return "Scaleが0に近いため、自動修正できません。"
        if value < 0.0:
            return "負のScaleが含まれるため、自動修正せず手動確認してください。"

    # Instanced shapes are shared by multiple transforms. Freezing one parent
    # could affect other instances, so this tool deliberately refuses them.
    for shape_path in shape_paths:
        parents = cmds.listRelatives(
            shape_path,
            allParents=True,
            fullPath=True
        ) or []

        if len(parents) > 1:
            return "インスタンス化されたShapeは自動修正できません。"

        history = cmds.listHistory(
            shape_path,
            pruneDagObjects=True
        ) or []

        for history_node in history:
            node_type = cmds.nodeType(history_node)
            if node_type in ("skinCluster", "blendShape"):
                return (
                    "Skin ClusterまたはBlend Shapeが関連しています。"
                    "変形履歴を確認してから手動で修正してください。"
                )

    return None


def _rollback_if_changed(
    transform_path,
    shape_paths,
    before_values,
    before_points
):
    """Undo the just-created operation only when scene state actually changed."""

    try:
        current_values = _read_transform_values(transform_path)
        current_points = _capture_world_mesh_points(shape_paths)

        geometry_unchanged = _compare_world_mesh_points(
            before_points,
            current_points
        )

        transform_unchanged = (
            current_values == before_values
        )

        if geometry_unchanged and transform_unchanged:
            return True, "変更は検出されなかったためUndoは不要です。"

        cmds.undo()

        restored_values = _read_transform_values(transform_path)
        restored_points = _capture_world_mesh_points(shape_paths)

        restored_geometry = _compare_world_mesh_points(
            before_points,
            restored_points
        )

        values_restored = all(
            abs(restored_values[key][index] - before_values[key][index])
            <= TRANSFORM_TOLERANCE
            for key in ("translate", "rotate", "scale")
            for index in range(3)
        )

        if restored_geometry and values_restored:
            return True, "Undoによって修正前の状態へ戻しました。"

        return False, "Undo後も修正前の状態と一致しません。シーンを確認してください。"

    except Exception as error:
        return False, "Undoによる復元に失敗しました: {}".format(error)


# =========================================
# 03. 1オブジェクトのTransformを修正
# =========================================

def fix_object_transform(obj):
    """Freeze Transformations for exactly one DAG-path mesh transform.

    The function does not depend on Maya's current selection. It validates
    the target, captures all mesh vertices in world space, performs the
    operation in an undo chunk, and verifies the result. If verification
    fails, it attempts to roll back the operation.
    """

    transform_path = obj or "不明"
    undo_chunk_open = False
    before_values = None
    before_points = None
    shape_paths = None
    operation_started = False

    try:
        transform_path = _resolve_transform(obj)
        shape_paths = _get_mesh_shapes(transform_path)

        if not shape_paths:
            return {
                "object": transform_path,
                "status": "SKIP",
                "message": "メッシュShapeがありません。",
                "details": []
            }

        direct_children = cmds.listRelatives(
            transform_path,
            children=True,
            fullPath=True
        ) or []

        child_transforms = []

        for child in direct_children:
            try:
                is_transform = cmds.objectType(
                    child,
                    isAType="transform"
                )
            except Exception:
                is_transform = cmds.nodeType(child) in (
                    "transform",
                    "joint"
                )

            if is_transform:
                child_transforms.append(child)

        if child_transforms:
            return {
                "object": transform_path,
                "status": "SKIP",
                "message": (
                    "子Transformが存在するため、子階層への影響を避けて"
                    "自動修正を中止しました。"
                ),
                "details": child_transforms
            }

        before_values = _read_transform_values(transform_path)

        if _is_transform_reset(before_values):
            return {
                "object": transform_path,
                "status": "OK",
                "message": "Transformはすでに基準値です。",
                "details": []
            }

        safety_message = _check_transform_is_editable(
            transform_path,
            shape_paths,
            before_values
        )

        if safety_message:
            return {
                "object": transform_path,
                "status": "SKIP",
                "message": safety_message,
                "details": []
            }

        if not cmds.undoInfo(query=True, state=True):
            return {
                "object": transform_path,
                "status": "ERROR",
                "message": "MayaのUndoが無効です。安全のため修正を中止しました。",
                "details": []
            }

        # Snapshot all vertices, not just the bounding box. This detects
        # changes even when a deformation leaves the same overall bounds.
        before_points = _capture_world_mesh_points(shape_paths)

        # Put the operation into one named Undo chunk so it can be rolled back
        # as one user action if post-validation fails.
        cmds.undoInfo(
            openChunk=True,
            chunkName="MPT_FreezeTransforms"
        )
        undo_chunk_open = True
        operation_started = True

        cmds.makeIdentity(
            transform_path,
            apply=True,
            translate=True,
            rotate=True,
            scale=True
        )

        cmds.undoInfo(closeChunk=True)
        undo_chunk_open = False

        after_values = _read_transform_values(transform_path)
        after_points = _capture_world_mesh_points(shape_paths)

        transform_reset = _is_transform_reset(after_values)
        geometry_unchanged = _compare_world_mesh_points(
            before_points,
            after_points
        )

        if not transform_reset or not geometry_unchanged:
            rollback_ok, rollback_message = _rollback_if_changed(
                transform_path,
                shape_paths,
                before_values,
                before_points
            )

            details = [
                "修正後Transform: {}".format(after_values),
                "ワールド頂点検証: {}（座標量子化許容値: {:.4f}）".format(
                    "一致" if geometry_unchanged else "不一致",
                    WORLD_POSITION_TOLERANCE
                ),
                rollback_message,
            ]

            return {
                "object": transform_path,
                "status": "ERROR",
                "message": (
                    "修正後の検証に失敗しました。{}"
                    .format("修正前へ復元しました。" if rollback_ok else "復元状態を確認してください。")
                ),
                "details": details
            }

        return {
            "object": transform_path,
            "status": "OK",
            "message": (
                "Transformを修正しました。すべてのメッシュ頂点のワールド座標は"
                "許容誤差内で維持されています。"
            ),
            "details": [
                "修正前: {}".format(before_values),
                "修正後: {}".format(after_values),
                "ワールド頂点検証: {}（座標量子化許容値: {:.4f}）".format(
                    "一致" if geometry_unchanged else "不一致",
                    WORLD_POSITION_TOLERANCE
                ),
            ]
        }

    except Exception as error:
        if undo_chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
                undo_chunk_open = False
            except Exception:
                pass

        rollback_details = []

        # makeIdentity itself may fail after partially changing the scene.
        # Only attempt Undo when snapshots exist and the operation was started.
        if operation_started and before_values is not None and before_points is not None:
            rollback_ok, rollback_message = _rollback_if_changed(
                transform_path,
                shape_paths,
                before_values,
                before_points
            )
            rollback_details.append(rollback_message)
            if not rollback_ok:
                rollback_details.append(
                    "シーンの状態を確認し、必要に応じて手動でUndoしてください。"
                )

        return {
            "object": transform_path,
            "status": "ERROR",
            "message": "Transformの自動修正に失敗しました。",
            "details": [str(error)] + rollback_details
        }


# =========================================
# 04. 選択オブジェクト向け互換関数
# =========================================

def fix_selected_transforms():
    """Fix selected transforms using the safer per-object implementation."""

    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:
        return [{
            "object": None,
            "status": "ERROR",
            "message": "オブジェクトが選択されていません。"
        }]

    return [
        fix_object_transform(obj)
        for obj in selected
    ]
