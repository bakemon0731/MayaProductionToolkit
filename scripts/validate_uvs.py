import maya.cmds as cmds


def validate_uvs(obj):
    name = obj.split("|")[-1]

    shapes = cmds.listRelatives(obj,shapes=True,noIntermediate=True,fullPath=True,type="mesh") or []

    # Meshが見つからない場合
    if not shapes:
        result = {
            "object": obj,
            "check": "UV",
            "status": "NG",
            "message": "Meshが見つかりません",
            "details": []
        }

        print(name, "-> Meshが見つかりません")
        return result

    # ShapeごとのUV情報を保存する
    uv_details = []
    problems = []

    for shape in shapes:
        uv_sets = cmds.polyUVSet(shape,query=True,allUVSets=True) or []

        # UVセットが存在しない場合
        if not uv_sets:
            uv_details.append({
                "shape": shape,
                "uv_set": None,
                "uv_count": 0
            })

            problems.append("UVセットなし")
            print(name, "-> UVセットなし")
            continue

        # 今回は最初のUVセットを検証する
        uv_set = uv_sets[0]

        uv_count = cmds.polyEvaluate(shape,uvcoord=True,uvSetName=uv_set) or 0

        uv_details.append({
            "shape": shape,
            "uv_set": uv_set,
            "uv_count": uv_count
        })

        print("オブジェクト:", name)
        print("UVセット:", uv_set)
        print("UV座標数:", uv_count)

        if uv_count > 0:
            print(name, "-> UV座標あり")
        else:
            problems.append("UV座標なし")
            print(name, "-> UV座標なし")

    # オブジェクト全体の検証結果を決定する
    if problems:
        status = "NG"
        message = " / ".join(problems)
    else:
        status = "OK"
        message = "UV座標があります"

    # 検証結果を辞書として返す
    result = {
        "object": obj,
        "check": "UV",
        "status": status,
        "message": message,
        "details": uv_details
    }

    return result


def validate_selected_uvs():
    selected = cmds.ls(selection=True,long=True,type="transform") or []

    if not selected:
        print("オブジェクトを選択してください")
        return []

    results = []

    for obj in selected:
        result = validate_uvs(obj)
        results.append(result)

    return results


if __name__ == "__main__":
    results = validate_selected_uvs()
    print("検証データ:", results)