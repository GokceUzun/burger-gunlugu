from typing import Optional
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from PIL import Image
import streamlit as st

from supabase import create_client, Client

# --- Supabase client ---
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase = get_client()
TABLE = "burger-logs"

# ---------- Ayarlar ----------
APP_TITLE = "🍔 Burger Günlüğü"
DATA_FILE = Path("burger_log.csv")
PHOTO_DIR = Path("photos")
PHOTO_DIR.mkdir(exist_ok=True)

# Kategoriler
CATS = ["Ekmek", "Köfte", "Sos", "Yan Ürünler", "Ortam/Servis/Sunum", "Fiyat/Performans"]

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
#foto_file = st.file_uploader("Fotoğraf (isteğe bağlı)", type=["jpg","jpeg","png","webp"])

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
st.info(f"Genel Ortalama: **{ortalama}**⭐  |  Baba: {baba_toplam}⭐ • Gökçe: {gokce_toplam}⭐")

if st.button("Kaydı Ekle"):
    if not mekan.strip():
        st.warning("Mekan adı zorunlu.")
    else:
        #photo_path = save_photo(foto_file)
        row = {
            "id": uuid.uuid4().hex,
            "tarih": str(tarih),
            "mekan": mekan.strip(),
            "baba_puan": int(baba_toplam),
            "baba_yorum": baba_yorum.strip(),
            "gokce_puan": int(gokce_toplam),
            "gokce_yorum": gokce_yorum.strip(),
            "ortalama": float(ortalama),
        }
        res = supabase.table(TABLE).insert(row).execute()
        if res.data:
            st.success("Kayıt eklendi ✅")
            st.experimental_rerun()
        else:
            st.error("Kayıt eklenemedi. Policy/şema ayarlarını kontrol et.")

# ---- Kayıtlar ----
st.header("Kayıtlar")
res = supabase.table(TABLE).select("*").order("tarih", desc=True).execute()
rows = res.data or []
if not rows:
    st.info("Henüz kayıt yok.")
else:
    # Liste
    for r in rows:
        with st.container(border=True):
            st.subheader(r.get("mekan", "—"))
            st.caption(f"Tarih: {r.get('tarih', '—')}")
            st.write(f"**Baba:** {r.get('baba_scores', 0)} — {r.get('baba_yorum', '')}")
            st.write(f"**Gökçe:** {r.get('gokce_scores', 0)} — {r.get('gokce_yorum', '')}")
            st.write(f"**Ortalama:** {r.get('ortalama', 0)}")

    # Tablo görünümü
    with st.expander("📊 Tablo görünümü"):
        st.dataframe(pd.DataFrame(rows), use_container_width=True)