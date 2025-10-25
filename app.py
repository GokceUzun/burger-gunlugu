import os, io, uuid, datetime as dt
from pathlib import Path

import pandas as pd
from PIL import Image
import streamlit as st
from typing import Optional

# ---------- Basit Ayarlar ----------
APP_TITLE = "🍔 Burger Günlüğü — Gökçe & Baba"
DATA_FILE = Path("burger_log.csv")
PHOTO_DIR = Path("photos")
PHOTO_DIR.mkdir(exist_ok=True)

CATEGORIES = ["Ekmek", "Köfte", "Sos", "Yan Ürün", "Ortam/Servis/Sunum", "Fiyat/Performans"]

# ---------- Yardımcılar ----------
def safe_float(x, default=0.0):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return default

def calc_total(scores: dict) -> float:
    vals = [safe_float(scores.get(k, 0)) for k in CATEGORIES]
    vals = [v for v in vals if v is not None]
    if not vals: 
        return 0.0
    return round(sum(vals) / len(vals), 2)

def load_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=[
            "id", "tarih", "mekan", 
            #"semt", "burger", "fiyat", "bekleme_dk",
            "foto", "yeniden_gider_miyiz",
            # Gökçe
            *[f"gokce_{c}" for c in CATEGORIES], "gokce_yorum", "gokce_toplam",
            # Baba
            *[f"baba_{c}" for c in CATEGORIES], "baba_yorum", "baba_toplam",
            # Genel
            "ortalama"
        ])
    return df

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)

def save_photo(uploaded_file) -> Optional[str]:
    if not uploaded_file:
        return None
    try:
        img = Image.open(uploaded_file)
        suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
        fname = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}{suffix}"
        fpath = PHOTO_DIR / fname
        img.save(fpath)
        return str(fpath)
    except Exception:
        return None

# ---------- UI ----------
st.set_page_config(APP_TITLE, page_icon="🍔", layout="wide")
st.title(APP_TITLE)
#st.caption("Fotoğraf yükle, ayrı puanlar ver, ortalama otomatik hesaplansın. Veriler aynı klasörde **CSV** olarak saklanır.")

df = load_data()

with st.sidebar:
    st.subheader("Veri & Dışa/İçe Aktarma")
    # CSV indir
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 CSV indir", data=csv_bytes, file_name="burger_log.csv", mime="text/csv")
    # CSV yükle (tamamen değiştirir)
    up_csv = st.file_uploader("CSV içe aktar (varsa üzerine yazar)", type=["csv"])
    if up_csv:
        new_df = pd.read_csv(up_csv)
        save_data(new_df)
        st.success("CSV içe aktarıldı. Sayfayı yenileyin (R) ya da tekrar çalıştırın.")
    st.markdown("---")
    if st.button("🗑️ Tüm kayıtları temizle"):
        save_data(pd.DataFrame(columns=df.columns))
        st.success("Tüm kayıtlar silindi. Sayfayı yenileyin.")

# ---- Yeni Kayıt Formu ----
st.header("➕ Yeni Kayıt")
with st.form("new_entry", clear_on_submit=True):
    col_meta1, col_meta2, col_meta3, col_meta4 = st.columns([1.2,1,1,1])
    with col_meta1:
        mekan = st.text_input("Mekan Adı *")
        #semt = st.text_input("Semt")
        #burger = st.text_input("Burger")
    with col_meta2:
        tarih = st.date_input("Tarih", dt.date.today())
        #fiyat = st.text_input("Fiyat (₺)")
    with col_meta3:
        #bekleme = st.text_input("Bekleme (dk)")
        yeniden = st.checkbox("Yeniden gider miyiz?")
    with col_meta4:
        foto_file = st.file_uploader("Fotoğraf (opsiyonel)", type=["jpg","jpeg","png","webp"])

    st.markdown("#### ⭐ Baba Puanları")
    cols_g = st.columns(3)
    gokce_scores = {}
    for i, cat in enumerate(CATEGORIES):
        with cols_g[i % 3]:
            gokce_scores[cat] = st.slider(f"Baba – {cat}", 0, 10, 0, step=1)
    gokce_yorum = st.text_area("Baba Yorumu", placeholder="Kısa not…")
    gokce_toplam = calc_total(gokce_scores)

    st.markdown("#### ⭐ Gökçe Puanları")
    cols_b = st.columns(3)
    baba_scores = {}
    for i, cat in enumerate(CATEGORIES):
        with cols_b[i % 3]:
            baba_scores[cat] = st.slider(f"Gökçe – {cat}", 0, 10, 0, step=1)
    baba_yorum = st.text_area("Gökçe Yorumu", placeholder="Kısa not…")
    baba_toplam = calc_total(baba_scores)

    genel_ortalama = round((gokce_toplam + baba_toplam)/2, 2)

    st.info(f"**Genel Ortalama: {genel_ortalama}**  |  Baba: {gokce_toplam}  •  Gökçe: {baba_toplam}")

    submitted = st.form_submit_button("Kaydı Ekle")
    if submitted:
        if not mekan.strip():
            st.error("Mekan adı zorunlu.")
        else:
            photo_path = save_photo(foto_file)
            row = {
                "id": uuid.uuid4().hex,
                "tarih": str(tarih),
                "mekan": mekan.strip(),
                #"semt": semt.strip(),
                #"burger": burger.strip(),
                #"fiyat": fiyat.strip(),
                #"bekleme_dk": bekleme.strip(),
                "foto": photo_path or "",
                "yeniden_gider_miyiz": bool(yeniden),
                **{f"gokce_{k}": gokce_scores[k] for k in CATEGORIES},
                "gokce_yorum": gokce_yorum.strip(),
                "gokce_toplam": gokce_toplam,
                **{f"baba_{k}": baba_scores[k] for k in CATEGORIES},
                "baba_yorum": baba_yorum.strip(),
                "baba_toplam": baba_toplam,
                "ortalama": genel_ortalama
            }
            df = pd.concat([pd.DataFrame([row]), df], ignore_index=True)
            save_data(df)
            st.success("Kayıt eklendi ✅")

view_df = df.copy()

# ---- Kart Görünümü ----
st.markdown("### Kart Görünümü")
if view_df.empty:
    st.warning("Kayıt yok.")
else:
    # grid halinde kartlar
    for _, r in view_df.iterrows():
        with st.container(border=True):
            cols = st.columns([1,2,1.2])
            with cols[0]:
                if str(r["foto"]).strip() and Path(str(r["foto"])).exists():
                    st.image(str(r["foto"]), use_column_width=True)
                else:
                    st.caption("Fotoğraf yok")
            with cols[1]:
                st.subheader(r["mekan"])
                st.caption(f"{r['semt']} • {r['burger']}")
                st.write(f"**Tarih:** {r['tarih']}  \n**Fiyat:** {r['fiyat']} ₺  •  **Bekleme:** {r['bekleme_dk']} dk")
                st.write(f"**Yeniden gider miyiz?** {'✅ Evet' if r['yeniden_gider_miyiz'] else '❌ Hayır'}")
                with st.expander("Gökçe Detay"):
                    st.write({c: int(r[f'gokce_{c}']) for c in CATEGORIES})
                    st.write("Yorum:", r["gokce_yorum"])
                with st.expander("Baba Detay"):
                    st.write({c: int(r[f'baba_{c}']) for c in CATEGORIES})
                    st.write("Yorum:", r["baba_yorum"])
            with cols[2]:
                st.metric("Ortalama", r["ortalama"])
                st.metric("Gökçe Toplam", r["gokce_toplam"])
                st.metric("Baba Toplam", r["baba_toplam"])
            # Silme butonu
            del_col = st.columns([1,0.2])[1]
            with del_col:
                if st.button("Sil", key=f"del-{r['id']}"):
                    df = df[df["id"] != r["id"]]
                    save_data(df)
                    st.rerun()

# ---- Tablo Görünümü ----
with st.expander("📊 Tablo Görünümü (tüm sütunlar)"):
    st.dataframe(df, use_container_width=True)
