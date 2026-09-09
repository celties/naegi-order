#!/usr/bin/env python3
"""前島園芸 苗木注文書管理アプリの死活監視。

Streamlit Cloud のアプリは中身が iframe (/~/+) 内に描画されるため、
HTTP ステータスやトップページの HTML では正常・異常を判別できない。
実際にヘッドレスブラウザで開き、描画されたテキストを見て判定する。

終了コード: 0=正常, 1=異常, 2=判定不能（監視側の問題）
"""
import json
import subprocess
import sys

URL = "https://naegi-order-haskb4ymaybahmhm2k2rls.streamlit.app/"

# 正常なら必ず出るはずの文字列
OK_MARKERS = ["前島園芸", "注文書をアップロード"]
# マスタ(苗木早見表)が読めているか
MASTER_MARKER = "マスタ読み込み済み"
# Streamlit Cloud が出す代表的な障害メッセージ
BAD_MARKERS = [
    "Error installing requirements",   # 依存インストール失敗（apt/pip）
    "Error running app",               # 起動時例外
    "Oh no",
    "resource limits",                 # メモリ超過
    "has gone to sleep",               # スリープ
    "Traceback (most recent call last)",
]


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
                       check=False)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def fetch_app_text(timeout_s=120):
    """アプリ本体フレームの表示テキストを返す"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=90000)
            best = ""
            waited = 0
            while waited < timeout_s:
                page.wait_for_timeout(5000)
                waited += 5
                for fr in page.frames:
                    if "statuspage" in fr.url:      # Streamlit の障害情報バナーは対象外
                        continue
                    try:
                        t = fr.evaluate("document.body ? document.body.innerText : ''") or ""
                    except Exception:
                        continue
                    if len(t) > len(best):
                        best = t
                # 正常判定に足る内容が揃ったら待たずに抜ける
                if any(m in best for m in OK_MARKERS) or any(m in best for m in BAD_MARKERS):
                    break
            page.screenshot(path="health_check.png")
            return best
        finally:
            browser.close()


def main():
    try:
        ensure_playwright()
        text = fetch_app_text()
    except Exception as e:
        print(json.dumps({"status": "UNKNOWN", "reason": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2

    found = [m for m in OK_MARKERS if m in text]
    bad = [m for m in BAD_MARKERS if m in text]
    master = MASTER_MARKER in text

    if bad or not found:
        status = "NG"
    elif not master:
        status = "WARN"          # 画面は出るがマスタが読めていない
    else:
        status = "OK"

    print(json.dumps({
        "status": status,
        "url": URL,
        "errors_found": bad,
        "ok_markers_found": found,
        "master_loaded": master,
        "rendered_chars": len(text),
        "excerpt": text[:300],
    }, ensure_ascii=False, indent=2))
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
