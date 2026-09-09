#!/usr/bin/env python3
"""毎朝の死活監視ラッパー。

health_check.py を実行し、異常なら macOS の通知を出す。
結果は常に monitor.log に追記するので、後から履歴を確認できる。

launchd から毎朝呼ばれる想定。
"""
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "monitor.log")
APP_URL = "https://naegi-order-haskb4ymaybahmhm2k2rls.streamlit.app/"


def notify(title, message):
    """macOS の通知センターに出す。失敗しても監視自体は続ける。"""
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{esc(message)}" with title "{esc(title)}" sound name "Basso"'],
            check=False, timeout=20)
    except Exception:
        pass


def log(line):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        proc = subprocess.run([sys.executable, os.path.join(HERE, "health_check.py")],
                              capture_output=True, text=True, timeout=900, cwd=HERE)
        raw = proc.stdout.strip()
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception as e:
        log(f"[{stamp}] UNKNOWN 監視スクリプトが失敗: {type(e).__name__}: {e}")
        notify("⚠️ 苗木アプリ 監視エラー",
               "監視スクリプト自体が失敗しました。アプリの状態は未確認です。")
        return 2

    status = data.get("status", "UNKNOWN")
    master = data.get("master_loaded")
    errs = data.get("errors_found") or []

    log(f"[{stamp}] {status} master={master} errors={errs}")

    if status == "OK":
        return 0                      # 正常時は通知しない（毎朝の通知は邪魔なので）

    if status == "NG":
        detail = f"障害表示: {', '.join(errs)}" if errs else "アプリ画面が表示されていません"
        notify("⚠️ 苗木注文アプリが開けません", f"{detail}｜{APP_URL}")
    elif status == "WARN":
        notify("⚠️ 苗木注文アプリ 要確認",
               "画面は出ますが苗木早見表が読み込めていません。")
    else:
        notify("⚠️ 苗木アプリ 監視エラー",
               f"判定不能: {str(data.get('reason', ''))[:120]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
