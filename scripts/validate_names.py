import maya.cmds as cmds
import re


def validate_name(name):
    pattern = r"^SM_[A-Za-z0-9]+$"
    return bool(re.match(pattern, name))


def validate_selected_names():
    selected = cmds.ls(
        selection=True,
        long=True,
        type="transform"
    ) or []

    if not selected:
        print("オブジェクトを選択してください")
        return []

    #空のリストを用意し、各オブジェクトの検証結果を追加していく
    results = []

    for obj in selected:
        name = obj.split("|")[-1]

        if validate_name(name):
            status = "OK"
            message = "命名規則に適合しています"
            print(name, "-> 命名規則OK")
        else:
            status = "NG"
            message = "命名規則に適合していません"
            print(name, "-> 命名規則NG")

        #辞書を用意
        result = {
            "object": obj,
            "check": "命名規則",
            "status": status,
            "message": message
        }

        #リストへ追加
        results.append(result)
      
    #すべてのオブジェクトを検証したら、結果のリストを返す
    return results


if __name__ == "__main__":
    results = validate_selected_names()

    print("検証データ:", results)

    #NGの結果だけを保存するリスト
    ng_results = []

    #検証結果を1件づつ確認する
    for item in results:
        if item["status"] == "NG":
            ng_results.append(item)

    #NGの件数と一覧を表示する
    print("NG件数:",len(ng_results))
    print("NG一覧",ng_results)