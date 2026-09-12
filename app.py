import os
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import pandas as pd
from google import genai
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import json
import io
import time
import difflib
import unicodedata
from datetime import datetime
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

st.set_page_config(
    page_title="前島園芸 苗木注文書管理",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
.stApp { background: #f0f7f0; }

/* サイドバーと展開ボタンを非表示 */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebarContent"] { display: none !important; }

/* ヘッダー非表示 */
[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }
.stDeployButton { display: none !important; }

/* ── ヒーローバナー ── */
.hero {
    background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 55%, #52b788 100%);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(29,67,50,0.25);
    position: relative;
    overflow: hidden;
}
.hero::after {
    content: "🍑  🍇  🍑  🍇  🍑  🍇";
    position: absolute;
    right: 30px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 2rem;
    opacity: 0.35;
    letter-spacing: 8px;
    pointer-events: none;
}
.hero h1 { font-size: 1.9rem; font-weight: 700; margin: 0 0 4px 0; color: white !important; }
.hero p  { font-size: 0.88rem; opacity: 0.85; margin: 0; color: white !important; }

/* ── 設定バー ── */
.settings-bar {
    background: white;
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 20px;
    border: 1px solid #d8edd8;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    display: flex;
    align-items: center;
    gap: 12px;
}
.master-badge {
    background: #d8f3dc;
    color: #1b4332;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
}

/* ── 見出し ── */
h2, h3 { color: #1b4332 !important; font-weight: 700 !important; }

/* ── ボタン ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-primaryFormSubmit"] {
    background: linear-gradient(135deg, #2d6a4f, #52b788) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
}
button[data-testid="baseButton-primary"]:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(45,106,79,0.35) !important;
}
button[data-testid="baseButton-secondary"] {
    background: white !important;
    color: #2d6a4f !important;
    border: 2px solid #52b788 !important;
}

/* ── ファイルアップローダー ── */
[data-testid="stFileUploaderDropzone"] {
    background: #f0f7f0 !important;
    border: 2px dashed #52b788 !important;
    border-radius: 10px !important;
}
/* 英語テキストを非表示にして日本語で上書き */
/* "Drag and drop file here" span */
[data-testid="stFileUploaderDropzone"] div > div > span:first-of-type {
    font-size: 0 !important;
    color: transparent !important;
}
[data-testid="stFileUploaderDropzone"] div > div > span:first-of-type::after {
    content: "ここに写真をドラッグ＆ドロップ";
    font-size: 14px !important;
    color: #2d6a4f !important;
    font-weight: 500 !important;
}
/* "Limit 200MB..." span */
[data-testid="stFileUploaderDropzone"] div > div > span:last-of-type {
    font-size: 0 !important;
    color: transparent !important;
}
[data-testid="stFileUploaderDropzone"] div > div > span:last-of-type::after {
    content: "対応形式: PDF・JPG・PNG・HEIC・TIFF（最大200MB）";
    font-size: 12px !important;
    color: #52b788 !important;
}
/* "Browse files" button → 写真を選択 */
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] {
    background: linear-gradient(135deg, #2d6a4f, #52b788) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    margin-top: 8px !important;
    position: relative !important;
    overflow: hidden !important;
    min-width: 130px !important;
    min-height: 38px !important;
    color: transparent !important;
}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] * {
    opacity: 0 !important;
    color: transparent !important;
}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"]::after {
    content: "🍑 写真を選択";
    font-size: 14px !important;
    color: white !important;
    font-weight: 700 !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    white-space: nowrap !important;
    pointer-events: none !important;
}

/* ── テキスト入力 ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 8px !important;
    border: 1.5px solid #b7d9b7 !important;
    background: #f9fcf9 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #52b788 !important;
    box-shadow: 0 0 0 2px rgba(82,183,136,0.2) !important;
}

/* ── セレクトボックス ── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 8px !important;
    border: 1.5px solid #b7d9b7 !important;
}

/* ── データフレーム ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #d8edd8 !important;
}

/* ── アラート ── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── スピナー ── */
[data-testid="stSpinner"] p { color: #2d6a4f !important; }
</style>

<div class="hero">
    <h1>🌱 前島園芸 苗木注文書管理</h1>
    <p>🍑 桃・🍇 葡萄の注文書を写真に撮ってアップロードするだけ — 自動で項目を読み取ります</p>
</div>
""", unsafe_allow_html=True)

# ─── 定数・マスタ読み込み ────────────────────────────────────────
# 注文書の記入順に合わせる（品種名→台木→本数→備考→金額）
COLUMNS = ["顧客ID", "注文日", "受付方法", "支払方法", "ふりがな", "お名前",
           "電話番号1", "電話番号2", "郵便番号", "住所",
           "品種名", "台木", "本数", "備考", "金額", "単価", "要確認", "元ファイル"]
UKETSUKE = ["", "電話", "FAX", "メール", "郵便", "来社"]
SHIHARAI = ["", "郵便振替", "銀行振込", "代金引換", "現金"]
MASTER_EXCEL = os.path.join(os.path.dirname(__file__), "苗木早見表　一覧.xlsx")
# 枠切れ・廃止のときは上から順に自動で切り替わる
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]
MODEL_LABELS = {
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite（最速・推奨）",
    "gemini-3.8-flash":      "Gemini 3.8 Flash（最新・高精度）",
    "gemini-2.5-flash":      "Gemini 2.5 Flash（安定）",
    "gemini-3.5-flash":      "Gemini 3.5 Flash",
    "gemini-flash-latest":   "Gemini Flash 最新版（自動追従）",
}

def load_master_from_excel():
    """苗木早見表から 品種名・台木・価格表・果樹の種類 を読み込む。

    「50音順」シートの構成:
      1列目=品種名（同じ品種が続く行は空欄）／2列目=台木
      3列目=税込み価格／4列目=果樹の種類
    価格は（品種名 × 台木）の組み合わせごとに決まる。
    """
    try:
        df = pd.read_excel(MASTER_EXCEL, sheet_name="50音順", header=None)
        d = df[[1, 2, 3, 4]].copy()
        d.columns = ["品種名", "台木", "価格", "種類"]
        d = d[~d["品種名"].astype(str).str.strip().eq("品種名")]   # 見出し行を除く
        d["品種名"] = d["品種名"].ffill()                          # 空欄は上の品種を引き継ぐ
        d["種類"] = d["種類"].ffill()
        d = d.dropna(subset=["台木"])
        d["品種名"] = d["品種名"].astype(str).str.strip()
        d["台木"] = d["台木"].astype(str).str.strip()
        d["価格"] = pd.to_numeric(d["価格"], errors="coerce")
        d = d[~d["品種名"].isin(["nan", ""]) & ~d["台木"].isin(["nan", "", "台木"])]

        prices, kinds = {}, {}
        for r in d.itertuples(index=False):
            if pd.notna(r.価格):
                prices[(r.品種名, r.台木)] = int(r.価格)
            if pd.notna(r.種類):
                kinds[r.品種名] = str(r.種類).strip()

        varieties  = list(dict.fromkeys(d["品種名"].tolist()))
        rootstocks = list(dict.fromkeys(d["台木"].tolist()))
        return varieties, rootstocks, prices, kinds
    except Exception:
        return [], [], {}, {}

def lookup_price(variety, rootstock, prices):
    """品種名と台木の組み合わせから税込み単価を引く。無ければ None。"""
    v, r = str(variety or "").strip(), str(rootstock or "").strip()
    if not v:
        return None
    if (v, r) in prices:
        return prices[(v, r)]
    # 台木が未記入でも、その品種の価格が1種類しかなければ確定できる
    cand = {p for (pv, _), p in prices.items() if pv == v}
    if len(cand) == 1:
        return cand.pop()
    return None

def price_rows(rows, prices):
    """各行に単価と金額を入れる。"""
    for row in rows:
        unit = lookup_price(row.get("品種名"), row.get("台木"), prices)
        qty = pd.to_numeric(str(row.get("本数", "")).strip() or "0", errors="coerce")
        row["単価"] = str(unit) if unit is not None else ""
        row["金額"] = str(int(unit * qty)) if (unit is not None and pd.notna(qty)) else ""
    return rows

# ─── 注文データの保存（アプリを閉じても消えないようにする）─────────
DATA_FILE = os.path.join(os.path.dirname(__file__), "orders_data.json")

def load_orders():
    """保存済みの注文一覧を読み込む。壊れていても落ちない。"""
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [{c: str(r.get(c, "")) for c in COLUMNS}
                    for r in data if isinstance(r, dict)]
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return []

def save_orders(orders):
    """一時ファイルに書いてから置き換える（書き込み中の停電等で壊さないため）"""
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=1)
        os.replace(tmp, DATA_FILE)
        return True
    except Exception as e:
        st.session_state.save_error = str(e)
        return False

def set_orders(rows):
    """一覧を差し替えて即保存する。注文を変更するときは必ずこれを通す。"""
    st.session_state.orders = rows
    save_orders(rows)

def add_orders(rows):
    """一覧に追記して即保存する。"""
    set_orders(st.session_state.orders + list(rows))

if "orders" not in st.session_state:
    st.session_state.orders = load_orders()
if "editing" not in st.session_state:
    st.session_state.editing = None
if "last_failures" not in st.session_state:
    st.session_state.last_failures = []
if "quota_hit" not in st.session_state:
    st.session_state.quota_hit = None
if "print_bytes" not in st.session_state:
    st.session_state.print_bytes = None
if "master_varieties" not in st.session_state or "master_prices" not in st.session_state:
    (st.session_state.master_varieties, st.session_state.master_rootstocks,
     st.session_state.master_prices, st.session_state.master_kinds) = load_master_from_excel()


# ─── ヘルパー関数 ────────────────────────────────────────────────
def _normalize(s):
    return unicodedata.normalize("NFKC", s).lower().strip()

def find_closest(name, candidates, threshold=0.4):
    """早見表の中から一番近い名前を返す。(採用した名前, 一致度) を返す。"""
    if not candidates or not name or not str(name).strip():
        return name, 1.0
    name_n = _normalize(str(name))
    scores = [(difflib.SequenceMatcher(None, name_n, _normalize(c)).ratio(), c) for c in candidates]
    best_score, best_candidate = max(scores)
    if best_score >= threshold:
        return best_candidate, best_score
    return name, best_score

def apply_master(items, varieties=None, rootstocks=None):
    # スレッドから呼ぶ場合は session_state を触れないので引数で渡す
    if varieties is None:  varieties  = st.session_state.master_varieties
    if rootstocks is None: rootstocks = st.session_state.master_rootstocks
    result = []
    for item in items:
        corrected = item.copy()
        notes = []
        if varieties:
            raw = str(item.get("品種名", "") or "").strip()
            fixed, score = find_closest(raw, varieties)
            corrected["品種名"] = fixed
            # 全角/半角の違いだけなら黙って直す。中身が変わる置き換えは必ず知らせる。
            if raw and _normalize(raw) != _normalize(fixed):
                notes.append(f"品種名「{raw}」→「{fixed}」に置換（一致度{score:.0%}）")
        if rootstocks:
            raw_r = str(item.get("台木", "") or "").strip()
            fixed_r, _ = find_closest(raw_r, rootstocks)
            corrected["台木"] = fixed_r
        corrected["要確認"] = " / ".join(notes)
        result.append(corrected)
    return result

class QuotaExhausted(Exception):
    """APIの利用枠切れ。待っても回復しないので一括処理を打ち切る"""

class ModelUnavailable(Exception):
    """モデルが廃止・未提供。次のモデルへ切り替える"""

def is_model_gone(msg):
    m = msg.replace(" ", "")
    return ("404" in m and any(k in m for k in ("NOT_FOUND", "notfound", "models/"))) \
        or "is not found" in msg or "利用できなくなりました" in msg

def is_daily_quota(msg):
    """1日あたりの上限（待っても回復しない）かどうかを判定する"""
    m = msg.replace(" ", "")
    return any(k in m for k in ("PerDay", "perday", "PerProjectPerDay", "FreeTier"))

def retry_delay_of(msg, default=20):
    """APIが返す retryDelay（例 '38s'）を秒数として取り出す"""
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s", msg)
    if m:
        return min(int(m.group(1)) + 2, 70)
    return default

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            key = ""
    return key

def extract_order_from_image(image_bytes, media_type, model, varieties=None, rootstocks=None):
    # varieties/rootstocks は並列処理から渡す（session_state はスレッド非対応）
    if varieties is None:  varieties  = st.session_state.master_varieties
    if rootstocks is None: rootstocks = st.session_state.master_rootstocks
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY が設定されていません。\n"
            "ターミナルで次のコマンドを実行してください:\n"
            "export GEMINI_API_KEY=\"あなたのAPIキー\""
        )
    client = genai.Client(api_key=api_key)
    variety_hint   = "、".join(varieties)
    rootstock_hint = "、".join(rootstocks)
    hint_text = ""
    if variety_hint:   hint_text += f"\n品種名の候補: {variety_hint}"
    if rootstock_hint: hint_text += f"\n台木の候補: {rootstock_hint}"

    prompt = f"""この画像は苗木の注文書です。
以下のJSON形式で情報を読み取ってください。
読み取れない項目は空文字にしてください。
品種名・台木・本数は複数行ある場合もあるので、すべて配列に入れてください。

【電話番号の読み取り注意】
・電話番号欄には「－」（ハイフン）があらかじめ印刷されています。
　この印刷されたハイフンは区切り記号であり、数字ではありません。
　絶対に 1 や 7 などの数字として読み取らないでください。
・電話番号欄には電話番号が最大2件書かれていることがあります。
　左側（上段）を電話番号1、右側（下段）を電話番号2としてください。
・出力は必ず半角数字とハイフンのみにし、
　「0553-22-1487」のような形式に整えてください。
・空欄のハイフンだけが残っている場合、その電話番号は空文字にしてください。
　（例：「－　　－」しか無い＝未記入なので空文字）
{hint_text}

{{
  "顧客ID": "右上の「No.」または「配送No.」欄に記載されている番号（数字のみ、なければ空文字）",
  "注文日": "元号または西暦の日付文字列",
  "受付方法": "注文日の右にある「電話・FAX・メール／郵便・来社」のうち丸で囲まれた、または選択されているもの1つ（電話/FAX/メール/郵便/来社のいずれか。判別できなければ空文字）",
  "支払方法": "最下部「お支払い方法」でチェックが入っているもの1つ（郵便振替/銀行振込/代金引換/現金のいずれか。なければ空文字）",
  "ふりがな": "名前のふりがな",
  "お名前": "漢字の名前",
  "電話番号1": "電話番号欄の1つめの電話番号",
  "電話番号2": "電話番号欄の2つめの電話番号（1つしか無ければ空文字）",
  "郵便番号": "ご住所欄の「〒」の後に書かれた郵便番号（例 405-0018。なければ空文字）",
  "住所": "ご住所欄の住所（郵便番号は含めない。なければ空文字）",
  "items": [
    {{"品種名": "品種名", "台木": "台木", "本数": "本数（数字）"}},
    {{"品種名": "...",    "台木": "...", "本数": "..."}}
  ],
  "備考": "備考欄（なければ空文字）"
}}

JSONのみ返してください。"""

    image = PIL.Image.open(io.BytesIO(image_bytes))
    if max(image.size) > 1600:                 # 大きすぎる写真は縮小（速度・コスト対策）
        image.thumbnail((1600, 1600), PIL.Image.LANCZOS)
    if image.mode != "RGB":
        image = image.convert("RGB")

    last_err = None
    for attempt in range(6):
        try:
            response = client.models.generate_content(model=model, contents=[image, prompt])
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as e:
            last_err = e
            msg = str(e)
            if is_model_gone(msg):
                raise ModelUnavailable(f"モデル {model} は利用できません") from e
            if any(x in msg for x in ("429", "RESOURCE_EXHAUSTED", "quota")):
                if is_daily_quota(msg):
                    # 1日の上限。待っても回復しないので即座に打ち切る
                    raise QuotaExhausted("本日の利用上限に達しました") from e
                if attempt < 5:
                    time.sleep(retry_delay_of(msg, default=15 * (attempt + 1))
                               + random.uniform(0, 3))
                    continue
                raise QuotaExhausted("短時間に送りすぎて制限中です") from e
            if any(x in msg for x in ("503", "500", "timed out", "timeout", "Errno 60")) and attempt < 5:
                time.sleep(5 * (attempt + 1) + random.uniform(0, 2))
                continue
            raise last_err
    raise last_err

def parse_one_image(name, image_bytes, model, varieties, rootstocks, prices=None):
    """写真1枚を解析して行データに変換する。並列実行される（session_state 不可）"""
    result = extract_order_from_image(image_bytes, "image/jpeg", model, varieties, rootstocks)
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict):
        raise ValueError(f"想定外の応答形式: {type(result).__name__}")
    items = result.get("items")
    if isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list) or len(items) == 0:
        items = [{"品種名": "", "台木": "", "本数": ""}]
    items = [i if isinstance(i, dict) else {"品種名": str(i), "台木": "", "本数": ""} for i in items]
    # 空行（3項目すべて空）は捨てる
    items = [i for i in items if any(str(i.get(k, "")).strip() for k in ("品種名", "台木", "本数"))] \
            or [{"品種名": "", "台木": "", "本数": ""}]
    result["items"] = apply_master(items, varieties, rootstocks)
    rows = flatten_to_rows(result)
    for r in rows:
        r["元ファイル"] = name
    if prices:
        price_rows(rows, prices)
    return rows

def clean_phone(v):
    """電話番号を半角数字とハイフンだけに整える。未記入はハイフンだけ残るので空にする"""
    s = unicodedata.normalize("NFKC", str(v or "")).strip()
    s = re.sub(r"[^0-9\-]", "", s)          # 数字とハイフン以外を除去
    s = re.sub(r"-{2,}", "-", s).strip("-")  # 連続ハイフン・前後のハイフンを整理
    return "" if not re.search(r"\d", s) else s

def flatten_to_rows(form):
    base = {k: form.get(k, "") for k in ["顧客ID","注文日","受付方法","支払方法","ふりがな","お名前",
                                         "電話番号1","電話番号2","郵便番号","住所","備考"]}
    base["電話番号1"] = clean_phone(base["電話番号1"])
    base["電話番号2"] = clean_phone(base["電話番号2"])
    if not base["電話番号1"] and base["電話番号2"]:   # 1が空で2だけある場合は詰める
        base["電話番号1"], base["電話番号2"] = base["電話番号2"], ""
    rows = []
    for item in form.get("items", [{"品種名":"","台木":"","本数":""}]):
        row = base.copy()
        row["品種名"] = item.get("品種名", "")
        row["台木"]   = item.get("台木", "")
        row["本数"]   = item.get("本数", "")
        row["要確認"] = item.get("要確認", "")
        rows.append(row)
    return rows


# ─── 印刷用 PDF / TIFF の生成 ───────────────────────────────────
FONT_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Regular.otf"),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
]

@st.cache_resource
def _font_path():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                PIL.ImageFont.truetype(p, 20)
                return p
            except Exception:
                continue
    return None

def _fnt(size):
    p = _font_path()
    return PIL.ImageFont.truetype(p, size) if p else PIL.ImageFont.load_default()

def render_table_pages(df, title, dpi=150):
    """一覧表を A4横のページ画像（複数枚）に描画する"""
    W, H = int(11.69 * dpi), int(8.27 * dpi)      # A4横
    M = int(0.4 * dpi)                            # 余白
    f_title, f_head, f_cell = _fnt(26), _fnt(15), _fnt(14)

    cols = [c for c in df.columns if c != "元ファイル"]
    probe = PIL.Image.new("RGB", (10, 10)); pd_ = PIL.ImageDraw.Draw(probe)
    # 列幅は「見出しと中身の実際の描画幅」から決め、全体を紙幅に収める
    raw = []
    for c in cols:
        w = pd_.textlength(str(c), font=f_head)
        for v in df[c].astype(str).head(400):
            w = max(w, pd_.textlength(v[:22], font=f_cell))
        raw.append(w + 16)
    scale = (W - 2 * M) / sum(raw)
    widths = [max(w * scale, 26) for w in raw]

    RH, HH = int(0.19 * dpi), int(0.24 * dpi)
    rows_per_page = max(1, (H - 2 * M - int(0.42 * dpi) - HH) // RH)
    chunks = [df.iloc[i:i + rows_per_page] for i in range(0, len(df), rows_per_page)] or [df]

    pages = []
    for pno, chunk in enumerate(chunks, 1):
        img = PIL.Image.new("RGB", (W, H), "white")
        d = PIL.ImageDraw.Draw(img)
        d.text((M, M - 6), title, font=f_title, fill="black")
        d.text((W - M - 190, M + 4), f"{pno} / {len(chunks)} ページ", font=f_cell, fill="black")

        y = M + int(0.42 * dpi)
        d.rectangle([M, y, M + sum(widths), y + HH], fill=(226, 240, 228))
        x = M
        for c, w in zip(cols, widths):
            d.text((x + 6, y + HH / 2 - 9), str(c), font=f_head, fill="black")
            x += w
        y += HH

        for _, row in chunk.iterrows():
            x = M
            for c, w in zip(cols, widths):
                txt = str(row[c])
                while txt and d.textlength(txt, font=f_cell) > w - 10:
                    txt = txt[:-1]                     # 列からはみ出さないよう末尾を切る
                d.text((x + 6, y + RH / 2 - 9), txt, font=f_cell, fill="black")
                d.line([(x, y), (x, y + RH)], fill=(190, 190, 190), width=1)
                x += w
            d.line([(M, y + RH), (M + sum(widths), y + RH)], fill=(190, 190, 190), width=1)
            y += RH

        d.rectangle([M, M + int(0.42 * dpi), M + sum(widths), y], outline="black", width=2)
        pages.append(img)
    return pages

def pages_to_bytes(pages, fmt):
    buf = io.BytesIO()
    if fmt == "PDF":
        pages[0].save(buf, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    else:  # TIFF（複数ページ・可逆圧縮）
        pages[0].save(buf, "TIFF", save_all=True, append_images=pages[1:],
                      compression="tiff_deflate", dpi=(150, 150))
    return buf.getvalue()


# ─── スキャンPDF・複数ページTIFFを1枚ずつの画像に展開する ─────────
PAGE_TYPES = ["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf", "tif", "tiff"]
MAX_PAGES = 150          # メモリ実測に基づく上限（超えるとStreamlit Cloudが落ちる）

def pdf_to_images(data, dpi=200):
    """複合機でまとめてスキャンしたPDFを1ページ=1枚のJPEGに分解する"""
    import pypdfium2 as pdfium
    out = []
    pdf = pdfium.PdfDocument(data)
    total = len(pdf)
    try:
        for i in range(min(total, MAX_PAGES)):
            img = pdf[i].render(scale=dpi / 72).to_pil().convert("RGB")
            if max(img.size) > 1600:          # 送信サイズを抑える
                img.thumbnail((1600, 1600), PIL.Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=88)
            out.append(buf.getvalue())
    finally:
        pdf.close()
    return out, total

def tiff_to_images(data):
    """複数ページTIFFを1ページずつに分解する"""
    out = []
    img = PIL.Image.open(io.BytesIO(data))
    total = getattr(img, "n_frames", 1)
    for i in range(min(total, MAX_PAGES)):
        img.seek(i)
        page = img.convert("RGB")
        if max(page.size) > 1600:
            page.thumbnail((1600, 1600), PIL.Image.LANCZOS)
        buf = io.BytesIO()
        page.save(buf, "JPEG", quality=88)
        out.append(buf.getvalue())
    return out, total

def expand_uploads(files):
    """アップロードされたファイル群を (表示名, 画像バイト列) の一覧に展開する。
    PDF・TIFF は1ページずつ分解するので、複合機の一括スキャンをそのまま渡せる。"""
    pages, errors = [], []
    for f in files:
        name = f.name
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        data = f.getvalue()
        try:
            if ext == "pdf":
                imgs, total = pdf_to_images(data)
                if not imgs:
                    raise ValueError("ページが読み取れませんでした")
                for i, b in enumerate(imgs, 1):
                    pages.append((f"{name}#{i}ページ目", b))
                if total > len(imgs):
                    errors.append((name, f"{total}ページありますが、一度に処理できるのは"
                                         f"{MAX_PAGES}ページまでです。{len(imgs)+1}ページ目以降は"
                                         f"読み込んでいません。分割してお試しください。"))
            elif ext in ("tif", "tiff"):
                imgs, total = tiff_to_images(data)
                for i, b in enumerate(imgs, 1):
                    pages.append((f"{name}#{i}ページ目", b))
                if total > len(imgs):
                    errors.append((name, f"{total}ページありますが、一度に処理できるのは"
                                         f"{MAX_PAGES}ページまでです。{len(imgs)+1}ページ目以降は"
                                         f"読み込んでいません。分割してお試しください。"))
            else:
                pages.append((name, data))
        except Exception as e:
            errors.append((name, f"ファイルを開けませんでした: {e}"))
    return pages, errors


# ─── 設定バー（モデル選択 ＋ マスタ状態） ────────────────────────
cfg1, cfg2, cfg3 = st.columns([2, 2, 1])

with cfg1:
    selected_model = st.selectbox(
        "⚙️ 使用モデル",
        FALLBACK_MODELS,
        format_func=lambda m: MODEL_LABELS.get(m, m),
        index=0,
        help="429エラーが出たら別のモデルに切り替えてください",
    )

with cfg2:
    nv = len(st.session_state.master_varieties)
    nr = len(st.session_state.master_rootstocks)
    if nv or nr:
        st.success(f"📋 マスタ読み込み済み：品種名 {nv}件 ／ 台木 {nr}件", icon="✅")
    else:
        st.warning("📋 苗木早見表が見つかりません")

with cfg3:
    if st.button("🔄 マスタ再読み込み", use_container_width=True):
        (st.session_state.master_varieties, st.session_state.master_rootstocks,
         st.session_state.master_prices, st.session_state.master_kinds) = load_master_from_excel()
        st.rerun()

st.divider()

# ─── メインレイアウト ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("🍑🍇 注文書をアップロード")
    uploaded = st.file_uploader(
        "写真を選択",
        type=PAGE_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:
        with st.spinner("ファイルを確認中…"):
            pages, open_errors = expand_uploads(uploaded)
        n_up = len(pages)
        n_files = len(uploaded)
        if n_up != n_files:
            st.info(f"📄 {n_files}ファイル → 注文書 {n_up}枚に展開しました")
        else:
            st.info(f"📸 {n_up}枚を選択中")
        for nm, err in open_errors:
            st.error(f"{nm}: {err}")
        # 実測: 1枚あたり約2.3MBのメモリを使うため、枚数に応じて段階的に注意を出す
        if n_up > 100:
            st.error(
                f"### 🚨 {n_up}枚は多すぎます\n\n"
                "**このまま実行すると、途中でアプリが止まって"
                "読み取った分が消えてしまう可能性があります。**\n\n"
                "**おすすめの進め方**\n\n"
                "1. いったん「写真を選択」からやり直す\n"
                f"2. **50枚ずつ**に分けて選ぶ（{n_up}枚なら {-(-n_up // 50)}回に分ける）\n"
                "3. 1回終わるごとに、下の一覧に追加されていくので安心です\n\n"
                "※ 一覧は自動で保存されるので、何回かに分けても消えません。"
            )
        elif n_up > 50:
            st.warning(
                f"### ⚠️ {n_up}枚はやや多めです\n\n"
                "動く可能性は高いですが、確実にやるなら**50枚ずつ**に"
                "分けたほうが安全です。\n\n"
                "このまま進めても構いません。途中で止まった場合は、"
                "読み取れた分は一覧に残るので、残りを選び直してください。"
            )
        elif n_up >= 20:
            st.info(f"📋 {n_up}枚を読み取ります。おおよそ {max(1, round(n_up * 3 / 60))}分ほどかかります。"
                    "終わるまで画面を閉じないでください。")

        if n_up == 1:
            st.image(pages[0][1], use_container_width=True)
        elif n_up > 1:
            with st.expander(f"読み取る注文書を確認（{n_up}枚）"):
                for nm, _ in pages[:12]:
                    st.caption(nm)
                if n_up > 12:
                    st.caption(f"…ほか {n_up - 12} 枚")

        # 同時送信数。APIの制限に当たらないよう1枚ずつ確実に処理する。
        # 速度を上げたい場合はここを増やす（有料プランなら4〜8が目安）。
        workers = 1

        if n_up and st.button(f"🔍 {n_up}枚を一括解析する", use_container_width=True, type="primary"):
            files = list(pages)
            varieties  = list(st.session_state.master_varieties)
            rootstocks = list(st.session_state.master_rootstocks)
            prices     = dict(st.session_state.master_prices)

            # 選んだモデルから順に、枠切れしたら自動で次のモデルへ降格して続行する
            chain = [selected_model] + [m for m in FALLBACK_MODELS if m != selected_model]
            st.info("⏳ 読み取り中です。終わるまでこの画面を閉じないでください。", icon="⏳")
            bar, live = st.progress(0.0, text="解析を開始します…"), st.empty()

            ok_rows, failures, downgrades = [], [], []
            pending = list(files)          # まだ成功していない写真
            total   = len(files)
            quota_hit = None

            for mi, model_name in enumerate(chain):
                if not pending:
                    break
                if mi > 0:
                    downgrades.append(model_name)
                    live.warning(f"⚠️ 枠切れのため「{MODEL_LABELS.get(model_name, model_name)}」"
                                 f"に切り替えて残り{len(pending)}枚を続行します…")

                retry_next, quota_hit = [], None
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    futs = {ex.submit(parse_one_image, nm, data, model_name,
                                      varieties, rootstocks, prices): (nm, data)
                            for nm, data in pending}
                    for fut in as_completed(futs):
                        nm, data = futs[fut]
                        try:
                            ok_rows.extend(fut.result())
                        except (QuotaExhausted, ModelUnavailable) as e:
                            quota_hit = str(e)
                            retry_next.append((nm, data))   # 次のモデルで再挑戦する
                            for f2 in futs:
                                f2.cancel()
                        except Exception as e:
                            failures.append((nm, str(e)[:200]))
                        n_done = len({r["元ファイル"] for r in ok_rows}) + len(failures)
                        bar.progress(min(n_done / total, 1.0),
                                     text=f"解析中…（{MODEL_LABELS.get(model_name, model_name)}）"
                                          f" {n_done}/{total}枚　成功 {n_done - len(failures)} ／ 失敗 {len(failures)}")

                # キャンセルされて未処理のまま残ったものも次のモデルへ回す
                done_names = {r["元ファイル"] for r in ok_rows} | {n for n, _ in failures}
                pending = [(nm, data) for nm, data in pending if nm not in done_names]
                if not quota_hit:
                    break                      # 枠切れ以外なら降格せず終了

            bar.empty(); live.empty()
            for nm, _ in pending:              # 全モデル試しても駄目だった分
                failures.append((nm, "全モデルで利用枠切れ"))

            add_orders(ok_rows)
            st.session_state.last_failures = failures
            st.session_state.quota_hit = quota_hit if pending else None

            n_ok = len({r["元ファイル"] for r in ok_rows})
            note = ""
            if downgrades:
                note = f"（枠切れのため {'→'.join(MODEL_LABELS.get(m, m) for m in downgrades)} に自動切替）"
            if pending:
                st.error(f"🚫 全モデルで利用枠に達しました。{n_ok}枚成功・{len(pending)}枚未処理{note}")
            elif failures:
                st.warning(f"✅ {n_ok}枚 成功／⚠️ {len(failures)}枚 失敗（{len(ok_rows)}行を追加）{note}")
            else:
                st.success(f"✅ {n_ok}枚すべて読み取り完了（{len(ok_rows)}行を追加）{note}")
            st.rerun()

    if st.session_state.get("quota_hit"):
        st.error(
            f"**🚫 {st.session_state.quota_hit}**\n\n"
            "AIが使えない状態です。次のどれかで解決します：\n\n"
            "1. **別のモデルに切り替える** — 画面上部の「使用モデル」を変えると、"
            "モデルごとに枠が分かれているため続けられる場合があります\n"
            "2. **しばらく待つ** — 1分あたりの制限なら1〜2分で回復します\n"
            "3. **翌日まで待つ** — 1日の上限の場合は日付が変わると回復します\n"
            "4. **有料プランにする** — 毎日たくさん処理するならこれが確実です\n\n"
            "※ すでに読み取れた分は下の一覧に残っています。失敗した写真だけ選び直してください。"
        )
        if st.button("この案内を閉じる"):
            st.session_state.quota_hit = None
            st.rerun()

    if st.session_state.get("last_failures"):
        with st.expander(f"⚠️ 読み取りに失敗した写真（{len(st.session_state.last_failures)}枚）"):
            for nm, err in st.session_state.last_failures:
                st.markdown(f"**{nm}**")
                st.caption(err)
            st.caption("失敗した写真だけを選び直して、もう一度アップロードしてください。")
            if st.button("この一覧を消す"):
                st.session_state.last_failures = []
                st.rerun()

    st.divider()

    if st.button("✏️ 手入力で追加", use_container_width=True):
        st.session_state.editing = {
            "顧客ID":"","注文日":"","受付方法":"","支払方法":"",
            "ふりがな":"","お名前":"",
            "電話番号1":"","電話番号2":"","郵便番号":"","住所":"",
            "items":[{"品種名":"","台木":"","本数":""}],
            "備考":"",
        }

    with st.expander("📂 CSV・Excelから取り込む"):
        st.caption("以前に出力した一覧や、テスト用データを読み込めます")
        imp = st.file_uploader("取り込むファイル", type=["csv", "xlsx"],
                               key="importer", label_visibility="collapsed")
        mode = st.radio("取り込み方法", ["既存の一覧に追加", "既存を置き換える"],
                        horizontal=True, key="import_mode")
        if imp is not None and st.button("📥 このファイルを取り込む", use_container_width=True, type="primary"):
            try:
                if imp.name.lower().endswith(".csv"):
                    df_in = pd.read_csv(imp, dtype=str, encoding="utf-8-sig").fillna("")
                else:
                    df_in = pd.read_excel(imp, dtype=str).fillna("")
                missing = [c for c in COLUMNS if c not in df_in.columns]
                for c in missing:
                    df_in[c] = ""
                df_in = df_in[COLUMNS]
                new_rows = price_rows(df_in.to_dict("records"), st.session_state.master_prices)
                if mode == "既存を置き換える":
                    set_orders(new_rows)
                else:
                    add_orders(new_rows)
                msg = f"✅ {len(new_rows)}件を取り込みました。"
                if missing:
                    msg += f"（ファイルに無かった列は空欄：{'・'.join(missing)}）"
                st.success(msg)
                st.rerun()
            except Exception as e:
                st.error(f"取り込みエラー: {e}")

    with st.expander("🔧 使用できるモデルを確認"):
        if st.button("モデル一覧を取得"):
            import os
            try:
                client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY",""))
                models = [m.name for m in client.models.list()
                          if "generateContent" in (m.supported_actions or [])]
                st.code("\n".join(models))
            except Exception as e:
                st.error(str(e))


with col_right:
    # ── 確認・編集フォーム ──
    if st.session_state.editing is not None:
        st.subheader("📝 内容を確認・修正")
        d = st.session_state.editing

        with st.form("order_form"):
            n_items = len(d.get("items", None) or [{}])
            ri1, ri2, ri3, ri4 = st.columns([1, 2, 1.4, 1.4])
            customer_id = ri1.text_input("🔢 顧客ID", value=d.get("顧客ID",""))
            order_date  = ri2.text_input("注文日",    value=d.get("注文日",""))
            _uke = str(d.get("受付方法","") or "").strip()
            uketsuke = ri3.selectbox("受付方法", UKETSUKE,
                index=UKETSUKE.index(_uke) if _uke in UKETSUKE else 0)
            _shi = str(d.get("支払方法","") or "").strip()
            shiharai = ri4.selectbox("支払方法", SHIHARAI,
                index=SHIHARAI.index(_shi) if _shi in SHIHARAI else 0)

            r1, r2 = st.columns(2)
            furigana = r1.text_input("ふりがな", value=d.get("ふりがな",""))
            name     = r2.text_input("お名前",   value=d.get("お名前",""))

            r3, r4 = st.columns(2)
            phone1 = r3.text_input("電話番号1", value=d.get("電話番号1",""))
            phone2 = r4.text_input("電話番号2", value=d.get("電話番号2",""))

            r5, r6 = st.columns([1, 3])
            postal  = r5.text_input("〒 郵便番号", value=d.get("郵便番号",""))
            address = r6.text_input("ご住所",     value=d.get("住所",""))

            st.markdown("**ご注文内容**")
            h1, h2, h3 = st.columns([3, 2, 1])
            h1.markdown("品種名"); h2.markdown("台木"); h3.markdown("本数")
            existing  = d.get("items", [])
            new_items = []
            for i in range(n_items):
                item = existing[i] if i < len(existing) else {}
                c1, c2, c3 = st.columns([3, 2, 1])
                variety   = c1.text_input("品種名", value=item.get("品種名",""), label_visibility="collapsed", key=f"variety_{i}")
                rootstock = c2.text_input("台木",   value=item.get("台木",""),   label_visibility="collapsed", key=f"rootstock_{i}")
                quantity  = c3.text_input("本数",   value=str(item.get("本数","")), label_visibility="collapsed", key=f"quantity_{i}")
                new_items.append({"品種名":variety,"台木":rootstock,"本数":quantity})

            notes = st.text_area("備考", value=d.get("備考",""), height=68)

            if st.form_submit_button("➕ 一覧に追加", type="primary", use_container_width=True):
                form_data = {
                    "顧客ID":customer_id,"注文日":order_date,
                    "受付方法":uketsuke,"支払方法":shiharai,
                    "ふりがな":furigana,"お名前":name,
                    "電話番号1":phone1,"電話番号2":phone2,
                    "郵便番号":postal,"住所":address,
                    "items":new_items,"備考":notes,
                }
                add_orders(price_rows(flatten_to_rows(form_data), st.session_state.master_prices))
                st.session_state.editing = None
                st.rerun()

    # ── 注文一覧 ──
    _orders = st.session_state.orders
    if _orders:
        _df_h = pd.DataFrame(_orders, columns=COLUMNS)
        _nc = _df_h["電話番号1"].replace("", pd.NA).dropna().nunique()
        _ni = len(_df_h)
        st.subheader(f"📋 注文一覧（{_nc}名・{_ni}品目）")
    else:
        st.subheader("📋 注文一覧（0件）")

    if st.session_state.orders:
        df = pd.DataFrame(st.session_state.orders, columns=COLUMNS)

        # ── 絞り込み ＆ ソート ──
        fs1, fs2 = st.columns([2, 3])
        search_id = fs1.text_input("🔍 顧客IDで絞り込み", placeholder="例: 123", label_visibility="visible")
        sort_key  = fs2.radio(
            "並び替え",
            ["受付順", "顧客ID順", "名前順（あいうえお）", "電話番号順"],
            horizontal=True,
            label_visibility="collapsed",
        )

        df_view = df.copy()
        if search_id.strip():
            df_view = df_view[df_view["顧客ID"].astype(str).str.contains(search_id.strip(), na=False)]

        if sort_key == "顧客ID順":
            df_view = df_view.sort_values("顧客ID", key=lambda s: pd.to_numeric(s, errors="coerce")).reset_index(drop=True)
        elif sort_key == "名前順（あいうえお）":
            df_view = df_view.sort_values("ふりがな").reset_index(drop=True)
        elif sort_key == "電話番号順":
            df_view = df_view.sort_values("電話番号1").reset_index(drop=True)

        # ── 金額の集計 ──
        _amt = pd.to_numeric(df["金額"], errors="coerce")
        _total = int(_amt.fillna(0).sum())
        _nop = int(_amt.isna().sum())          # 単価が引けなかった行
        mc1, mc2 = st.columns([1, 1])
        mc1.metric("💰 合計金額（税込）", f"{_total:,} 円")
        mc2.metric("🌱 合計本数", f"{int(pd.to_numeric(df['本数'], errors='coerce').fillna(0).sum()):,} 本")
        if _nop:
            st.warning(f"⚠️ {_nop}件は単価が分からないため金額に入っていません。"
                       "品種名か台木が早見表と一致していない可能性があります。"
                       "下の表で確認してください。")

        # ── 品種名が置き換えられた行の警告 ──
        _rep = df[df.get("要確認", pd.Series([""] * len(df))).astype(str).str.strip() != ""]
        if len(_rep):
            with st.expander(f"🔎 品種名を早見表に合わせた行が {len(_rep)}件あります（要確認）", expanded=True):
                st.caption("手書きが読み取れなかった場合、似た名前に置き換わることがあります。"
                           "今年度の取り扱いが無い品種は特にご注意ください。")
                st.dataframe(_rep[["顧客ID", "お名前", "品種名", "台木", "本数", "要確認"]],
                             use_container_width=True, hide_index=True)

        # ── 顧客IDの取り違えチェック ──
        _chk = df[df["顧客ID"].astype(str).str.strip() != ""]
        _conf = (_chk.groupby("顧客ID")["お名前"]
                     .agg(lambda s: sorted({x for x in s if str(x).strip()}))
                     .loc[lambda s: s.map(len) > 1])
        _noid = (df["顧客ID"].astype(str).str.strip() == "").sum()
        if len(_conf):
            st.error(
                "**⚠️ 顧客IDが重複しています（別の方に同じ番号が付いています）**\n\n"
                + "\n".join(f"- ID **{i}** → {' ／ '.join(n)}" for i, n in _conf.items())
                + "\n\n読み取り間違いの可能性が高いので、下の表で確認・修正してください。"
            )
        if _noid:
            st.warning(f"⚠️ 顧客IDが空欄の行が {_noid} 件あります。"
                       "注文書のNo.欄が読み取れなかった可能性があります。")

        edit_mode = st.toggle("✏️ 表を直接編集する", value=False,
                              help="読み取り間違いをこの表の上で直せます。並び替えは「受付順」のときだけ編集できます。")

        if edit_mode and sort_key == "受付順" and not search_id.strip():
            edited = st.data_editor(
                df_view, use_container_width=True, num_rows="dynamic",
                key="order_editor", height=460,
            )
            if st.button("💾 編集内容を保存", type="primary", use_container_width=True):
                set_orders(price_rows(edited.fillna("").astype(str).to_dict("records"),
                                      st.session_state.master_prices))
                st.success("保存しました。")
                st.rerun()
        else:
            if edit_mode:
                st.caption("⚠️ 編集するには並び替えを「受付順」にして、IDの絞り込みを空にしてください。")
            st.dataframe(df_view, use_container_width=True, hide_index=False, height=460)

        with st.expander("📊 集計（品種ごと・お客様ごと・全体）", expanded=True):
            df_c = df_view.copy()
            df_c["本数"] = pd.to_numeric(df_c["本数"], errors="coerce")
            df_c["金額"] = pd.to_numeric(df_c["金額"], errors="coerce")

            st.markdown("### ① 品種ごとの合計金額")
            summary = (df_c.groupby("品種名")
                           .agg(合計本数=("本数", "sum"), 合計金額=("金額", "sum"))
                           .reset_index().sort_values("合計本数", ascending=False))
            summary["合計本数"] = summary["合計本数"].fillna(0).astype(int)
            summary["合計金額"] = summary["合計金額"].fillna(0).astype(int)
            st.dataframe(summary, use_container_width=True, hide_index=True)

            st.markdown("### ② お客様ごとの合計金額")
            per = (df_c.groupby(["顧客ID", "お名前"], dropna=False)
                       .agg(品目数=("品種名", "count"), 合計本数=("本数", "sum"),
                            合計金額=("金額", "sum"))
                       .reset_index()
                       .sort_values("顧客ID", key=lambda s: pd.to_numeric(s, errors="coerce")))
            per["合計金額"] = per["合計金額"].fillna(0).astype(int)
            per["合計本数"] = per["合計本数"].fillna(0).astype(int)
            st.dataframe(per, use_container_width=True, hide_index=True)

            st.markdown("### ③ 全体の合計")
            s1, s2 = st.columns(2)
            s1.metric("総合計本数", f"{int(df_c['本数'].fillna(0).sum()):,} 本")
            s2.metric("総合計金額（税込）", f"{int(df_c['金額'].fillna(0).sum()):,} 円")

        st.divider()
        date_str = datetime.now().strftime("%y%m%d")

        df_out = df_view.copy()

        c1, c2, c3 = st.columns([2, 2, 1])

        csv_buf = io.StringIO()
        df_out.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        c1.download_button(
            "📥 CSVダウンロード",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"前島園芸苗注文書一覧_{date_str}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        def cell_width(value):
            if value is None: return 0
            return sum(2 if ord(c) > 127 else 1 for c in str(value))

        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            # 1枚目: 注文一覧（最終行に合計を入れる）
            _x = df_out.copy()
            _x["本数"] = pd.to_numeric(_x["本数"], errors="coerce")
            _x["金額"] = pd.to_numeric(_x["金額"], errors="coerce")
            _sum = {c: "" for c in _x.columns}
            _sum["お名前"] = "■ 合計"
            _sum["本数"] = int(_x["本数"].fillna(0).sum())
            _sum["金額"] = int(_x["金額"].fillna(0).sum())
            _x = pd.concat([_x, pd.DataFrame([_sum])], ignore_index=True)
            _x.to_excel(writer, index=False, sheet_name="注文一覧")

            # 2枚目: お客様ごとの請求額
            _p = df_out.copy()
            _p["本数"] = pd.to_numeric(_p["本数"], errors="coerce")
            _p["金額"] = pd.to_numeric(_p["金額"], errors="coerce")
            per = (_p.groupby(["顧客ID", "お名前", "電話番号1"], dropna=False)
                     .agg(品目数=("品種名", "count"), 合計本数=("本数", "sum"),
                          合計金額=("金額", "sum")).reset_index()
                     .sort_values("顧客ID", key=lambda s: pd.to_numeric(s, errors="coerce")))
            per["合計本数"] = per["合計本数"].fillna(0).astype(int)
            per["合計金額"] = per["合計金額"].fillna(0).astype(int)
            per = pd.concat([per, pd.DataFrame([{
                "顧客ID": "", "お名前": "■ 合計", "電話番号1": "",
                "品目数": int(per["品目数"].sum()),
                "合計本数": int(per["合計本数"].sum()),
                "合計金額": int(per["合計金額"].sum())}])], ignore_index=True)
            per.to_excel(writer, index=False, sheet_name="お客様ごと請求")

            from openpyxl.styles import Font
            for sheet_name, frame in (("注文一覧", _x), ("お客様ごと請求", per)):
                ws = writer.sheets[sheet_name]
                for col_cells in ws.columns:
                    max_w = max(cell_width(cell.value) for cell in col_cells)
                    ws.column_dimensions[col_cells[0].column_letter].width = min(max(max_w+2,10),60)
                for cell in ws[1]:                       # 見出しを太字に
                    cell.font = Font(bold=True)
                for cell in ws[ws.max_row]:              # 合計行を太字に
                    cell.font = Font(bold=True)
                # 金額・単価列に円マークの書式を付ける
                for idx, name in enumerate(frame.columns, start=1):
                    if name in ("金額", "単価", "合計金額"):
                        for row in range(2, ws.max_row + 1):
                            ws.cell(row=row, column=idx).number_format = '#,##0"円"' 
        c2.download_button(
            "📥 Excelダウンロード",
            data=excel_buf.getvalue(),
            file_name=f"前島園芸苗注文書一覧_{date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # ── 印刷用（PDF / TIFF）──
        st.markdown("**🖨️ 印刷用ファイル**")
        p1, p2 = st.columns([1, 3])
        out_fmt = p1.radio("形式", ["PDF", "TIFF"], horizontal=True,
                           key="print_fmt", label_visibility="collapsed")
        with p2:
            if _font_path() is None:
                st.error("日本語フォントが見つからないため、印刷用ファイルを作れません。")
            elif st.button(f"🖨️ {out_fmt} を作成する", use_container_width=True):
                with st.spinner(f"{out_fmt} を作成中…"):
                    try:
                        pages = render_table_pages(
                            df_out, f"前島園芸 苗木注文書一覧（{len(df_out)}件）")
                        st.session_state.print_bytes = pages_to_bytes(pages, out_fmt)
                        st.session_state.print_ext   = "pdf" if out_fmt == "PDF" else "tif"
                        st.session_state.print_pages = len(pages)
                    except Exception as e:
                        st.error(f"作成に失敗しました: {e}")

        if st.session_state.get("print_bytes"):
            ext = st.session_state.print_ext
            st.download_button(
                f"📥 {ext.upper()}をダウンロード（{st.session_state.print_pages}ページ）",
                data=st.session_state.print_bytes,
                file_name=f"前島園芸苗注文書一覧_{date_str}.{ext}",
                mime="application/pdf" if ext == "pdf" else "image/tiff",
                use_container_width=True,
                type="primary",
            )

        if c3.button("🗑️ 全削除", use_container_width=True):
            set_orders([])
            st.rerun()
    else:
        st.info("まだ注文がありません。写真をアップロードするか、手入力で追加してください。")
