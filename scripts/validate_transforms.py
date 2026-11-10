from email import message
from unittest import result

import maya.cmds as cmds

#浮動小数点数の誤差を考慮するための許容値
TOLERANCE = 0.001

def validate_transform(obj):
    name = obj.split("|")[-1]

    # Transformの値を取得する
    translate = cmds.getAttr(obj + ".translate")[0]
    rotate = cmds.getAttr(obj + ".rotate")[0]
    scale = cmds.getAttr(obj + ".scale")[0]

    problems = []

    # Translateが基準値（0）から外れているか
    if any(abs(value) > TOLERANCE for value in translate):
        problems.append("Translate")

     # Rotateが基準値（0）から外れているか
    if any(abs(value) > TOLERANCE for value in rotate):
        problems.append("Rotate")

     # Scaleが基準値（1）から外れているか
    if any(abs(value - 1.0) > TOLERANCE for value in scale):
        problems.append("Scale")

    #　検証結果を決定する
    if problems:
        status = "NG"
        message = "基準値から外れています:"+",".join(problems)
        print(name, "-> Transform要確認:",",".join(problems))
    else:
        status = "OK"
        message = "Transformは基準値です"
        print(name,"-> Transform OK")

    #　検証結果を辞書として返す
    result = {
        "object": obj,
        "check": "Transform",
        "status": status,
        "message": message,
        "details":problems
        }

    return result


def validate_selected_transforms():
    selected = cmds.ls(selection=True,long=True,type="transform") or []

    if not selected:
        print("オブジェクトを選択してください")
        return []

    results = []

    for obj in selected:
        result = validate_transform(obj)
        results.append(result)

    return results


if __name__ == "__main__":
    results = validate_selected_transforms()
    print("検証データ:", results)