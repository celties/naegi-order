#!/usr/bin/env python3
"""26-27年度の苗木価格表（果樹別の複数Excel）を1つのマスタにまとめる。

各ファイルは
  ・列の位置がファイルごとに違う
  ・1ファイルに複数の表が入っていることがある（その他＝リンゴ/クリ/イチジク/キウイ）
  ・区分行（白肉桃・甘柿など）や注記行が混ざる
  ・品種名は同じ品種が続く行では空欄
  ・品種名に注記が付く（例「甲斐オウ果６　（甲斐ルビー®）【山梨県内限定販売】」）
ため、見出し行（品種名／台木／税込価格）を探して列位置を毎回決め直す。
"""
import glob
import os
import re
import unicodedata

import pandas as pd

SRC_DIR = "/Users/celties/Downloads/前島園芸/苗木価格表26~27"
OUT = "/Users/celties/Downloads/Claude/naegi_order/苗木早見表　一覧.xlsx"

# 表題から果樹の種類を拾う（「〇〇苗木価格表」）
TITLE_RE = re.compile(r"^(.+?)苗木価格表")
# 品種名に付く注記を落とす
ANNOT_RE = re.compile(r"[（(【〔].*?[）)】〕]|※.*$|\s+")


def clean_variety(s):
    """品種名から注記と余分な空白を取り除く"""
    s = unicodedata.normalize("NFKC", str(s)).strip()
    s = ANNOT_RE.sub("", s)
    return s.strip()


def clean_root(s):
    s = unicodedata.normalize("NFKC", str(s)).strip()
    return re.sub(r"\s+", "", s)


def is_note(text):
    """注記行かどうか（台木も価格も無い長い文）"""
    t = str(text)
    return len(t) > 14 or any(k in t for k in ("となります", "ください", "情報です", "本体価格", "変わる場合"))


def parse_sheet(df, fname):
    """1シートから (品種名, 台木, 税込価格, 種類) の行を取り出す"""
    rows = []
    kind = None          # 現在の果樹の種類（表題から）
    cols = None          # (品種名列, 台木列, 税込価格列)
    last_variety = None

    for _, raw in df.iterrows():
        vals = raw.tolist()
        texts = [unicodedata.normalize("NFKC", str(v)).strip() if pd.notna(v) else "" for v in vals]
        joined = " ".join(t for t in texts if t)
        if not joined:
            continue

        # 表題行 → 種類を更新し、表が変わるので品種の引き継ぎを切る
        m = TITLE_RE.match(joined.replace(" ", ""))
        if m and "品種名" not in joined:
            kind = m.group(1)
            last_variety = None
            continue

        # 見出し行 → 列位置を決め直す
        if "品種名" in texts and "台木" in texts:
            c_var = texts.index("品種名")
            c_root = texts.index("台木")
            c_price = texts.index("税込価格") if "税込価格" in texts else None
            if c_price is None:
                continue
            cols = (c_var, c_root, c_price)
            last_variety = None
            continue

        if cols is None:
            continue
        c_var, c_root, c_price = cols
        variety = texts[c_var] if c_var < len(texts) else ""
        root = texts[c_root] if c_root < len(texts) else ""
        price = vals[c_price] if c_price < len(vals) else None

        # 区分行（白肉桃・甘柿など）と注記行は、価格も台木も無い
        if not root and (price is None or pd.isna(price)):
            if variety and not is_note(variety):
                last_variety = None      # 区分が変わるので引き継ぎを切る
            continue

        if variety:
            last_variety = clean_variety(variety)
        v = last_variety
        r = clean_root(root)
        p = pd.to_numeric(price, errors="coerce")
        if not v or not r or pd.isna(p):
            continue
        rows.append({"品種名": v, "台木": r, "税込み価格": int(p),
                     "種類": kind or "", "出典": os.path.basename(fname)})
    return rows


def main():
    all_rows = []
    for f in sorted(glob.glob(os.path.join(SRC_DIR, "*.xls*"))):
        if os.path.basename(f).startswith("~$"):
            continue
        xl = pd.ExcelFile(f)
        for sh in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sh, header=None)
            got = parse_sheet(df, f)
            all_rows.extend(got)
            print(f"{os.path.basename(f):50s} {sh:10s} → {len(got):4d}件")

    d = pd.DataFrame(all_rows)
    dup = d[d.duplicated(subset=["品種名", "台木"], keep=False)]
    if len(dup):
        print(f"\n⚠️ 品種×台木の重複 {len(dup)}件:")
        print(dup.sort_values(["品種名", "台木"]).to_string(index=False))
    d = d.drop_duplicates(subset=["品種名", "台木"], keep="first")

    d = d.sort_values(["種類", "品種名", "台木"]).reset_index(drop=True)
    print(f"\n合計 {len(d)}件 / 品種 {d['品種名'].nunique()}種 / 台木 {d['台木'].nunique()}種")
    print(f"価格帯 {d['税込み価格'].min():,}〜{d['税込み価格'].max():,}円")
    print("\n種類別:")
    print(d.groupby("種類").agg(件数=("品種名", "count"), 品種数=("品種名", "nunique")).to_string())
    print("\n台木一覧:", sorted(d["台木"].unique()))
    d.to_csv("/tmp/master_new.csv", index=False, encoding="utf-8-sig")
    print("\n→ /tmp/master_new.csv に書き出しました（確認用）")
    return d


if __name__ == "__main__":
    main()
