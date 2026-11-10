from unittest import result

import maya.cmds as cmds

def validate_ngons(obj):

    name = obj.split('|')[-1] 

    shapes = cmds.listRelatives(obj,shapes=True,noIntermediate=True,fullPath=True,type="mesh") or []

    # Meshがない場合
    if not shapes:
        result = {
            "object": obj,
            "check": "N-gon",
            "status": "NG",
            "message": "Meshが見つかりません",
            "details": []
        }

        print(name,"-> Meshが見つかりません")
        return result

    # 検出したN-gonの情報を保存する
    ngon_faces = []

    for shape in shapes:
        face_count = cmds.polyEvaluate(shape, face=True)

        for face_index in range(face_count):
            face = shape + ".f[" + str(face_index) + "]"

            #面ごとの頂点情報を取得
            face_info = cmds.polyInfo(face,faceToVertex=True)or{}

            if not face_info:
                continue

            vertex_text = face_info[0].split(":", 1)[1].strip()
            vertex_indices = vertex_text.split()
            vertex_count = len(vertex_indices)

            #面を構成する頂点の数を数え、5以上ならN-gon候補として記録する仕組み
            if vertex_count > 4:
               ngon_faces.append({
                   "shape": shape,
                   "face_index": face_index,
                   "vertex_count": vertex_count
               })

        # 検証結果を決定する
        if ngon_faces:
            status = "NG"
            message = "N-gonが見つかりました"
            print(name,"-> N-gonあり")

            for face_data in ngon_faces:
                print(" 面番号:", face_data["face_index"],
                      "頂点数:", face_data["vertex_count"]
                )
        else:
            status = "OK"
            message = "N-gonはありません"
            print(name,"-> N-gonなし")


        #検証結果を辞書として返す
        result = {
            "object": obj,
            "check": "N-gon",
            "status": status,
            "message": message,
            "details": ngon_faces
        }

        return result


def validate_selected_ngons():
    selected = cmds.ls(selection=True, long=True,type="transform") or []

    if not selected:
        print("オブジェクトを選択してください")
        return []

    results = []

    for obj in selected:
        result = validate_ngons(obj)
        results.append(result)

    return results


if __name__ == "__main__":
    results = validate_selected_ngons()
    print("検証データ:", results)