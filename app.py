import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import pandas as pd
from google import genai
import PIL.Image
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
    content: "対応形式: JPG・PNG・WEBP・HEIC（最大200MB）";
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
COLUMNS = ["顧客ID", "注文日", "受付方法", "支払方法", "ふりがな", "お名前",
           "電話番号1", "電話番号2", "郵便番号", "住所", "品種名", "台木", "本数", "備考", "元ファイル"]
UKETSUKE = ["", "電話", "FAX", "メール", "郵便", "来社"]
SHIHARAI = ["", "郵便振替", "銀行振込", "代金引換", "現金"]
MASTER_EXCEL = os.path.join(os.path.dirname(__file__), "苗木早見表　一覧.xlsx")
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash"]
MODEL_LABELS = {
    "gemini-2.5-flash":    "Gemini 2.5 Flash（高精度・推奨）",
    "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite（軽量）",
    "gemini-2.0-flash":    "Gemini 2.0 Flash",
}

def load_master_from_excel():
    try:
        df = pd.read_excel(MASTER_EXCEL, sheet_name="50音順", header=None)
        varieties  = [v for v in df[1].dropna().astype(str).str.strip() if v not in ("品種名","nan","")]
        rootstocks = [r for r in df[2].dropna().astype(str).str.strip() if r not in ("台木","nan","")]
        return list(dict.fromkeys(varieties)), list(dict.fromkeys(rootstocks))
    except Exception:
        return [], []

if "orders" not in st.session_state:
    st.session_state.orders = []
if "editing" not in st.session_state:
    st.session_state.editing = None
if "last_failures" not in st.session_state:
    st.session_state.last_failures = []
if "master_varieties" not in st.session_state or "master_rootstocks" not in st.session_state:
    st.session_state.master_varieties, st.session_state.master_rootstocks = load_master_from_excel()


# ─── ヘルパー関数 ────────────────────────────────────────────────
def _normalize(s):
    return unicodedata.normalize("NFKC", s).lower().strip()

def find_closest(name, candidates, threshold=0.4):
    if not candidates or not name or not str(name).strip():
        return name
    name_n = _normalize(str(name))
    scores = [(difflib.SequenceMatcher(None, name_n, _normalize(c)).ratio(), c) for c in candidates]
    best_score, best_candidate = max(scores)
    return best_candidate if best_score >= threshold else name

def apply_master(items, varieties=None, rootstocks=None):
    # スレッドから呼ぶ場合は session_state を触れないので引数で渡す
    if varieties is None:  varieties  = st.session_state.master_varieties
    if rootstocks is None: rootstocks = st.session_state.master_rootstocks
    result = []
    for item in items:
        corrected = item.copy()
        if varieties:
            corrected["品種名"] = find_closest(item.get("品種名", ""), varieties)
        if rootstocks:
            corrected["台木"] = find_closest(item.get("台木", ""), rootstocks)
        result.append(corrected)
    return result

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
品種名・台木・本数は複数行ある場合もあるので、すべて配列に入れてください。{hint_text}

{{
  "顧客ID": "右上の「No.」または「配送No.」欄に記載されている番号（数字のみ、なければ空文字）",
  "注文日": "元号または西暦の日付文字列",
  "受付方法": "注文日の右にある「電話・FAX・メール／郵便・来社」のうち丸で囲まれた、または選択されているもの1つ（電話/FAX/メール/郵便/来社のいずれか。判別できなければ空文字）",
  "支払方法": "最下部「お支払い方法」でチェックが入っているもの1つ（郵便振替/銀行振込/代金引換/現金のいずれか。なければ空文字）",
  "ふりがな": "名前のふりがな",
  "お名前": "漢字の名前",
  "電話番号1": "電話番号1",
  "電話番号2": "電話番号2（なければ空文字）",
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
            # 429（レート制限）は長めに、その他の一時エラーは短めに待って再試行
            if any(x in msg for x in ("429", "RESOURCE_EXHAUSTED", "quota")) and attempt < 5:
                time.sleep(min(20 * (attempt + 1), 70) + random.uniform(0, 3))
                continue
            if any(x in msg for x in ("503", "500", "timed out", "timeout", "Errno 60")) and attempt < 5:
                time.sleep(5 * (attempt + 1) + random.uniform(0, 2))
                continue
            raise last_err
    raise last_err

def parse_one_image(name, image_bytes, model, varieties, rootstocks):
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
    return rows

def flatten_to_rows(form):
    base = {k: form.get(k, "") for k in ["顧客ID","注文日","受付方法","支払方法","ふりがな","お名前",
                                         "電話番号1","電話番号2","郵便番号","住所","備考"]}
    rows = []
    for item in form.get("items", [{"品種名":"","台木":"","本数":""}]):
        row = base.copy()
        row["品種名"] = item.get("品種名", "")
        row["台木"]   = item.get("台木", "")
        row["本数"]   = item.get("本数", "")
        rows.append(row)
    return rows


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
        st.session_state.master_varieties, st.session_state.master_rootstocks = load_master_from_excel()
        st.rerun()

st.divider()

# ─── メインレイアウト ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("🍑🍇 注文書をアップロード")
    uploaded = st.file_uploader(
        "写真を選択",
        type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:
        n_up = len(uploaded)
        st.info(f"📸 {n_up}枚を選択中")
        if n_up > 50:
            st.warning(
                f"⚠️ {n_up}枚は一度に処理する量としては多めです。"
                "途中で止まる場合は50枚以下に分けてお試しください。",
                icon="⚠️",
            )

        if n_up == 1:
            st.image(uploaded[0], use_container_width=True)
        else:
            with st.expander(f"選んだ写真を確認（{n_up}枚）"):
                for f in uploaded[:12]:
                    st.caption(f.name)
                if n_up > 12:
                    st.caption(f"…ほか {n_up - 12} 枚")

        workers = st.slider(
            "同時に処理する枚数", 1, 8, 4,
            help="多いほど速くなりますが、APIのレート制限（429エラー）が出やすくなります。"
                 "429が多発する場合は数を減らしてください。",
        )

        if st.button(f"🔍 {n_up}枚を一括解析する", use_container_width=True, type="primary"):
            files = [(f.name, f.getvalue()) for f in uploaded]
            varieties  = list(st.session_state.master_varieties)
            rootstocks = list(st.session_state.master_rootstocks)

            bar    = st.progress(0.0, text="解析を開始します…")
            live   = st.empty()
            ok_rows, failures, done = [], [], 0

            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {
                    ex.submit(parse_one_image, nm, data, selected_model, varieties, rootstocks): nm
                    for nm, data in files
                }
                for fut in as_completed(futs):
                    nm = futs[fut]
                    done += 1
                    try:
                        ok_rows.extend(fut.result())
                    except Exception as e:
                        failures.append((nm, str(e)[:200]))
                    bar.progress(done / len(files),
                                 text=f"解析中… {done}/{len(files)}枚（成功 {done-len(failures)} ／ 失敗 {len(failures)}）")
                    live.caption(f"直近: {nm}")

            bar.empty(); live.empty()
            st.session_state.orders.extend(ok_rows)
            st.session_state.last_failures = failures

            n_ok = len(files) - len(failures)
            if failures:
                st.warning(f"✅ {n_ok}枚 成功／⚠️ {len(failures)}枚 失敗（{len(ok_rows)}行を追加）")
            else:
                st.success(f"✅ {n_ok}枚すべて読み取り完了（{len(ok_rows)}行を追加）")
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
                new_rows = df_in.to_dict("records")
                if mode == "既存を置き換える":
                    st.session_state.orders = new_rows
                else:
                    st.session_state.orders.extend(new_rows)
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
                st.session_state.orders.extend(flatten_to_rows(form_data))
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

        edit_mode = st.toggle("✏️ 表を直接編集する", value=False,
                              help="読み取り間違いをこの表の上で直せます。並び替えは「受付順」のときだけ編集できます。")

        if edit_mode and sort_key == "受付順" and not search_id.strip():
            edited = st.data_editor(
                df_view, use_container_width=True, num_rows="dynamic",
                key="order_editor", height=460,
            )
            if st.button("💾 編集内容を保存", type="primary", use_container_width=True):
                st.session_state.orders = edited.fillna("").astype(str).to_dict("records")
                st.success("保存しました。")
                st.rerun()
        else:
            if edit_mode:
                st.caption("⚠️ 編集するには並び替えを「受付順」にして、IDの絞り込みを空にしてください。")
            st.dataframe(df_view, use_container_width=True, hide_index=False, height=460)

        with st.expander("📊 品種別 集計"):
            df_c = df_view.copy()
            df_c["本数"] = pd.to_numeric(df_c["本数"], errors="coerce")
            summary = df_c.groupby("品種名")["本数"].sum().reset_index()
            summary.columns = ["品種名", "合計本数"]
            st.dataframe(summary, use_container_width=True, hide_index=True)
            st.metric("総合計", f"{int(df_c['本数'].sum()):,} 本")

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
            df_out.to_excel(writer, index=False, sheet_name="注文一覧")
            ws = writer.sheets["注文一覧"]
            for col_cells in ws.columns:
                max_w = max(cell_width(cell.value) for cell in col_cells)
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(max_w+2,10),60)
        c2.download_button(
            "📥 Excelダウンロード",
            data=excel_buf.getvalue(),
            file_name=f"前島園芸苗注文書一覧_{date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        if c3.button("🗑️ 全削除", use_container_width=True):
            st.session_state.orders = []
            st.rerun()
    else:
        st.info("まだ注文がありません。写真をアップロードするか、手入力で追加してください。")
