from typing import Optional
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from PIL import Image
import streamlit as st

# ---------- Ayarlar ----------
APP_TITLE = "🍔 Burger Günlüğü"
DATA_FILE = Path("burger_log.csv")
PHOTO_DIR = Path("photos")
PHOTO_DIR.mkdir(exist_ok=True)

# Kategoriler
CATS = ["Ekmek", "Köfte" "Sos", "Yan Ürün", "Ortam/Servis/Sunum", "Fiyat/Performans"]

# ---------- Yardımcılar ----------
def save_photo(uploaded_file) -> Optional[str]:
    if not uploaded_file:
        return None
    try:
        img = Image.open(uploaded_file)
        suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
        fname = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}{suffix}"
        fpath = PHOTO_DIR / fname
        img.save(fpath)
        return str(fpath)
    except Exception:
        return None

def avg(vals):
    nums = [float(v) for v in vals if v is not None]
    return round(sum(nums)/len(nums), 2) if nums else 0.0

def base_columns():
    cols = ["id","Tarih","Mekan","Foto"]
    cols += [f"Baba {c}"   for c in CATS] + ["Baba Yorum","Baba Toplam"]
    cols += [f"Gökçe {c}" for c in CATS] + ["Gökçe Yorum","Gökçe Toplam"]
    cols += ["Ortalama"]
    return cols

def load_data() -> pd.DataFrame:
    cols = base_columns()
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
        # Eksik kolon varsa ekle
        for c in cols:
            if c not in df.columns:
                df[c] = "" if ("Yorum" in c or c in ["Mekan","Foto"]) else 0
        # Tarihi düzgün göster
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce").dt.date
        return df[cols]
    else:
        return pd.DataFrame(columns=cols)

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)

# ---------- UI ----------
st.set_page_config(APP_TITLE, page_icon="🍔", layout="centered")
st.title(APP_TITLE)
#st.caption("Mekan & tarih gir; Gökçe ve Baba için kategorili puan + yorum ekle. Kayıtlar CSV'ye, fotoğraflar photos/ klasörüne kaydedilir.")

df = load_data()

with st.sidebar:
    st.subheader("Veri")
    st.download_button("📥 CSV indir", data=df.to_csv(index=False).encode("utf-8"),
                       file_name="burger_log.csv", mime="text/csv")
    up_csv = st.file_uploader("CSV içe aktar (üzerine yazar)", type=["csv"])
    if up_csv:
        new_df = pd.read_csv(up_csv)
        save_data(new_df)
        st.success("CSV içe aktarıldı. Sayfayı yenileyin.")
    st.markdown("---")
    if st.button("🗑️ Tüm kayıtları sil"):
        save_data(pd.DataFrame(columns=base_columns()))
        st.success("Tüm kayıtlar silindi. Sayfayı yenileyin.")

# ---- Form ----
st.header("Yeni Kayıt")
mekan = st.text_input("Mekan Adı *")
tarih = st.date_input("Tarih", value=date.today())
foto_file = st.file_uploader("Fotoğraf (isteğe bağlı)", type=["jpg","jpeg","png","webp"])

# Baba
st.subheader("Baba")
baba_scores = {}
cols_b = st.columns(3)
for i, cat in enumerate(CATS):
    with cols_b[i % 3]:
        baba_scores[cat] = st.slider(f"{cat}", 0, 10, 7, key=f"baba_{cat}")
baba_yorum = st.text_area("Baba Yorumu", key="baba_yorum")
baba_toplam = avg(baba_scores.values())

# Gökçe
st.subheader("Gökçe")
gokce_scores = {}
cols_g = st.columns(3)
for i, cat in enumerate(CATS):
    with cols_g[i % 3]:
        # Benzersiz key şart! (aksi halde çakışma hatası)
        gokce_scores[cat] = st.slider(f"{cat}", 0, 10, 7, key=f"gokce_{cat}")
gokce_yorum = st.text_area("Gökçe Yorumu", key="gokce_yorum")
gokce_toplam = avg(gokce_scores.values())

ortalama = avg([gokce_toplam, baba_toplam])
st.info(f"Genel Ortalama: **{ortalama}**  |  Baba: {baba_toplam} • Gökçe: {gokce_toplam}")

if st.button("Kaydı Ekle"):
    if not mekan.strip():
        st.warning("Mekan adı zorunlu.")
    else:
        photo_path = save_photo(foto_file)
        row = {
            "id": uuid.uuid4().hex,
            "Tarih": tarih,
            "Mekan": mekan.strip(),
            "Foto": photo_path or "",
            **{f"Gökçe {c}": int(gokce_scores[c]) for c in CATS},
            "Gökçe Yorum": gokce_yorum.strip(),
            "Gökçe Toplam": gokce_toplam,
            **{f"Baba {c}": int(baba_scores[c]) for c in CATS},
            "Baba Yorum": baba_yorum.strip(),
            "Baba Toplam": baba_toplam,
            "Ortalama": ortalama
        }
        new_df = pd.DataFrame([row], columns=base_columns())
        df = pd.concat([new_df, df], ignore_index=True)
        save_data(df)
        st.success("Kayıt eklendi ✅")

# ---- Kayıtlar ----
st.header("Kayıtlar")
if df.empty:
    st.info("Henüz kayıt yok.")
else:
    # Kart gibi liste
    for _, r in df.sort_values("Tarih", ascending=False).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([1,3])
            with c1:
                if str(r["Foto"]).strip() and Path(str(r["Foto"])).exists():
                    st.image(str(r["Foto"]), use_column_width=True)
                else:
                    st.caption("Fotoğraf yok")
            with c2:
                st.subheader(f"{r['Mekan']}")
                st.caption(f"Tarih: {r['Tarih']}")
                st.write(f"**Gökçe Toplam:** {r['Gökçe Toplam']}  |  **Baba Toplam:** {r['Baba Toplam']}  |  **Ortalama:** {r['Ortalama']}")
                with st.expander("Gökçe Detay"):
                    st.write({c: int(r[f"Gökçe {c}"]) for c in CATS})
                    st.write("Yorum:", r["Gökçe Yorum"])
                with st.expander("Baba Detay"):
                    st.write({c: int(r[f"Baba {c}"]) for c in CATS})
                    st.write("Yorum:", r["Baba Yorum"])

    with st.expander("📊 Tablo görünümü"):
        st.dataframe(df, use_container_width=True)
