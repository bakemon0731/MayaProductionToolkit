import maya.cmds as cmds

import fix_history

# 1つのオブジェクトの履歴を調べる
def validate_history(obj):
    name = obj.split("|")[-1]

    # UIの個別修正と同じ共通分析を利用する。
    analysis = fix_history.analyze_history(obj)
    history_nodes = analysis["history"]

    # 検証結果を決定する。対応外履歴が混在する場合はNGを維持しつつ、
    # UIに「自動修正対象外」と伝えて修正ボタンを表示しない。
    if history_nodes:
        status = "NG"

        if analysis["unsupported"]:
            message = (
                "構築履歴が残っています（自動修正対象外の履歴を含みます）"
            )
        else:
            block_reason = fix_history.get_history_fix_block_reason(obj)
            if block_reason:
                message = "構築履歴が残っています（自動修正対象外: {}）".format(
                    block_reason
                )
            else:
                message = "構築履歴が残っています（自動修正可能）"

        print(name, "-> 構築履歴あり")
        print("履歴ノード:", history_nodes)

        if analysis["unsupported"]:
            print("自動修正対象外:", analysis["unsupported"])
    else:
        status = "OK"
        message = "構築履歴がありません"
        print(name, "->構築履歴なし")

    # 検証結果を辞書として返す
    result = {
        "object": obj,
        "check": "Construction History",
        "status": status,
        "message": message,
        "details": [
            "{} ({})".format(node, cmds.nodeType(node))
            for node in history_nodes
        ]
    }

    return result


#選択オブジェクトを取得し、1つずつ検証する
def validate_selected_history():
    selected = cmds.ls(selection=True, long=True, type="transform") or []

    if not selected:
        print("オブジェクトを選択してください")
        return[]

    results = []

    for obj in selected:
        result = validate_history(obj)
        results.append(result)

    return results



if __name__ == "__main__":
    results = validate_selected_history()
    print("検証データ:", results)