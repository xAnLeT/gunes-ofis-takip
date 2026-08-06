import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# Sayfa Genişlik Ayarı ve Sekme İkonu
st.set_page_config(page_title="Güneş Mühendislik - Ofis Otomasyonu", layout="wide", page_icon="logo 2.png")

# Veritabanı Kurulumu ve Güncellemesi
def veritabanı_hazırla():
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            musteri_adi TEXT,
            gelis_yolu TEXT,
            usta TEXT,
            armadas_durumu TEXT,
            eksik_nedeni TEXT,
            toplam_bedel REAL,
            alinan_odeme REAL,
            kalan_alacak REAL,
            odeme_yontemi TEXT,
            sayac_seri_no TEXT,
            regulator_durumu TEXT,
            kombi_marka_model TEXT,
            notlar TEXT
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE projeler ADD COLUMN proje_icerigi TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass 

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ustalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usta_adi TEXT UNIQUE,
            telefon_no TEXT
        )
    ''')
    conn.commit()
    conn.close()

veritabanı_hazırla()

# --- Veritabanı Fonksiyonları ---
def usta_hafizaya_ekle(usta_adi, telefon_no_girdi):
    if usta_adi and str(usta_adi).strip() != "":
        conn = sqlite3.connect("ofis_takip_v2.db")
        cursor = conn.cursor()
        tel = str(telefon_no_girdi).strip() if telefon_no_girdi else "Girilmemiş"
        cursor.execute("INSERT OR IGNORE INTO ustalar (usta_adi, telefon_no) VALUES (?, ?)", (str(usta_adi).strip(), tel))
        conn.commit()
        conn.close()

def usta_telefon_guncelle(usta_adi, yeni_tel):
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE ustalar SET telefon_no = ? WHERE usta_adi = ?", (yeni_tel.strip(), usta_adi))
    conn.commit()
    conn.close()

def hafizadaki_ustalari_getir():
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    cursor.execute("SELECT usta_adi FROM ustalar ORDER BY usta_adi ASC")
    ustalar = [satir[0] for satir in cursor.fetchall()]
    conn.close()
    return ustalar

def veri_ekle(tarih_str, musteri, kaynak, usta, a_durum, eksik, toplam, alinan, yontem, sayac, regulator, icerik_str, notlar):
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    kalan = float(toplam) - float(alinan)
    
    cursor.execute('''
        INSERT INTO projeler (tarih, musteri_adi, gelis_yolu, usta, armadas_durumu, eksik_nedeni, toplam_bedel, alinan_odeme, kalan_alacak, odeme_yontemi, sayac_seri_no, regulator_durumu, proje_icerigi, notlar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tarih_str, musteri, kaynak, usta, a_durum, eksik, toplam, alinan, kalan, yontem, sayac, regulator, icerik_str, notlar))
    conn.commit()
    conn.close()

def excelden_toplu_veri_ekle(df):
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    eklenen_sayi = 0
    df = df.fillna("")
    
    for _, row in df.iterrows():
        musteri = str(row.get('Müşteri Adı', row.get('Müşteri', row.get('Proje Adı', '')))).strip()
        usta = str(row.get('Usta', row.get('Sorumlu Usta', row.get('Usta Adı', '')))).strip()
        
        if musteri and musteri != "":
            tarih = str(row.get('Tarih', row.get('Kayıt Tarihi', datetime.now().strftime("%Y-%m-%d"))))
            if not tarih: tarih = datetime.now().strftime("%Y-%m-%d")
            
            gelis_yolu = str(row.get('Geliş Yolu', 'Excel Aktarımı'))
            armadas = str(row.get('Armadaş Durumu', 'Armadaş Onayladı / Tesisat Aşamasında'))
            eksik = str(row.get('Eksik Nedeni', ''))
            
            try: toplam = float(row.get('Toplam Bedel', row.get('Tutar', 0.0)))
            except: toplam = 0.0
            
            try: alinan = float(row.get('Alınan Ödeme', row.get('Alınan', 0.0)))
            except: alinan = 0.0
            
            kalan = toplam - alinan
            yontem = str(row.get('Ödeme Yöntemi', 'Belirtilmedi'))
            sayac = str(row.get('Sayaç Seri No', row.get('Sayaç', '')))
            regulator = str(row.get('Regülatör Durumu', 'Gerekmiyor'))
            icerik = str(row.get('Proje İçeriği', row.get('İçerik', '')))
            notlar = str(row.get('Notlar', 'Geçmiş Excel Kaydı'))
            
            cursor.execute('''
                INSERT INTO projeler (tarih, musteri_adi, gelis_yolu, usta, armadas_durumu, eksik_nedeni, toplam_bedel, alinan_odeme, kalan_alacak, odeme_yontemi, sayac_seri_no, regulator_durumu, proje_icerigi, notlar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tarih, musteri, gelis_yolu, usta, armadas, eksik, toplam, alinan, kalan, yontem, sayac, regulator, icerik, notlar))
            
            if usta:
                cursor.execute("INSERT OR IGNORE INTO ustalar (usta_adi, telefon_no) VALUES (?, ?)", (usta, "Excel'den Eklendi"))
                
            eklenen_sayi += 1
            
    conn.commit()
    conn.close()
    return eklenen_sayi

def veri_cek():
    conn = sqlite3.connect("ofis_takip_v2.db")
    df = pd.read_sql_query("SELECT * FROM projeler ORDER BY id DESC", conn)
    conn.close()
    return df

def veri_guncelle(df_guncel):
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    for _, row in df_guncel.iterrows():
        usta_adi = str(row['usta']).strip() if pd.notna(row['usta']) else ""
        kalan_hesap = float(row['toplam_bedel']) - float(row['alinan_odeme'])
        p_icerik = str(row['proje_icerigi']) if pd.notna(row['proje_icerigi']) else ""
        eksik_metni = str(row['eksik_nedeni']) if pd.notna(row['eksik_nedeni']) else ""
        
        cursor.execute('''
            UPDATE projeler SET 
                musteri_adi=?, gelis_yolu=?, usta=?, armadas_durumu=?, eksik_nedeni=?, 
                toplam_bedel=?, alinan_odeme=?, kalan_alacak=?, odeme_yontemi=?, 
                sayac_seri_no=?, regulator_durumu=?, proje_icerigi=?, notlar=?
            WHERE id=?
        ''', (str(row['musteri_adi']), str(row['gelis_yolu']), usta_adi, str(row['armadas_durumu']), 
              eksik_metni, float(row['toplam_bedel']), float(row['alinan_odeme']), 
              kalan_hesap, str(row['odeme_yontemi']), str(row['sayac_seri_no']), 
              str(row['regulator_durumu']), p_icerik, str(row['notlar']), int(row['id'])))
    conn.commit()
    conn.close()

def veri_sil(silinecek_idler):
    conn = sqlite3.connect("ofis_takip_v2.db")
    cursor = conn.cursor()
    for i in silinecek_idler:
        cursor.execute("DELETE FROM projeler WHERE id=?", (int(i),))
    conn.commit()
    conn.close()

# --- ARAYÜZ ---
col_logo, col_baslik = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

with col_baslik:
    st.title("Güneş Doğalgaz & Mühendislik")
    st.subheader("Kurumsal Proje Yönetim ve İş Takip Paneli")
    st.caption("Verileriniz güvende, işleriniz kontrol altında.")
st.markdown("---")

sekme1, sekme2, sekme3, sekme4, sekme5 = st.tabs([
    "➕ Yeni Proje & İş Kaydı", 
    "📋 Gelişmiş İş Takip Tablosu", 
    "💰 Gelişmiş Finans & Performans",
    "👨‍🔧 Usta Rehberi & Detaylar",
    "🔄 Excel Senkronizasyonu"
])

ARMADAS_ADIMLARI = [
    "Proje Çizim Aşamasında", 
    "Armadaş Dijital Onay Bekliyor", 
    "Armadaş Onayladı / Tesisat Aşamasında", 
    "Armadaş Randevu Alındı", 
    "Armadaş Eksik / Red Aldı", 
    "Gaz Açıldı / Müşteriye Teslim Edildi"
]

tum_kayitli_ustalar = sorted(hafizadaki_ustalari_getir(), key=lambda x: x.lower())

# SEKME 1: YENİ PROJE EKLEME
with sekme1:
    with st.expander("➕ Sisteme Yeni Bir Usta Tanımla (Rehbere Kaydet)"):
        with st.form("hizli_usta_formu", clear_on_submit=True):
            y_usta_ad = st.text_input("Usta Adı Soyadı")
            y_usta_tel = st.text_input("Usta Telefon Numarası (İsteğe Bağlı)")
            usta_ekle_butonu = st.form_submit_button("Ustayı Kaydet")
            
            if usta_ekle_butonu:
                if y_usta_ad:
                    usta_hafizaya_ekle(y_usta_ad, y_usta_tel)
                    st.success(f"'{y_usta_ad}' başarıyla rehbere kaydedildi!")
                    st.rerun()
                else:
                    st.error("Usta adı boş bırakılamaz.")
                    
    st.markdown("---")
    
    with st.form("gelismis_proje_formu", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**📌 Genel Bilgiler**")
            secilen_proje_tarihi = st.date_input("📆 Proje Tarihi", value=datetime.now())
            musteri_adi = st.text_input("Müşteri / Proje Adı")
            gelis_yolu = st.selectbox("Proje Geliş Yolu", ["WhatsApp", "Elden Geldi", "Telefon", "Saha Tespiti"])
            secilen_usta = st.selectbox("Atanan Usta", ["Seçiniz..."] + tum_kayitli_ustalar) if tum_kayitli_ustalar else st.selectbox("Atanan Usta", ["Önce usta tanımlayın!"])
            
            st.markdown("---")
            st.markdown("**📐 Proje İçerik Sayıları**")
            kolon_sayisi = st.number_input("🏢 Kolon Sayısı", min_value=0, value=0, step=1)
            ic_tesisat_sayisi = st.number_input("🔥 İç Tesisat Sayısı", min_value=0, value=0, step=1)
            diger_icerikler = st.multiselect("⚙️ Diğer İşlemler", options=["Cihaz Değişimi", "Randevu Reddi"])
            st.markdown("---")
            
            armadas_durumu = st.selectbox("Armadaş Süreç Adımı", ARMADAS_ADIMLARI)
            eksik_nedeni = st.text_input("Eksik / Red Nedeni (Varsa)")

        with c2:
            st.markdown("**💰 Finansal Durum**")
            toplam_bedel = st.number_input("Proje Toplam Bedeli (TL)", min_value=0.0, step=500.0)
            alinan_odeme = st.number_input("Alınan Kapora / Ödeme (TL)", min_value=0.0, step=500.0)
            odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Kredi Kartı", "Havale/EFT", "Ödeme Alınmadı"])

        with c3:
            st.markdown("**📦 Malzeme & Sayaç Detayları**")
            sayac_seri_no = st.text_input("Doğalgaz Sayaç Seri No")
            regulator_durumu = st.selectbox("Regülatör Durumu", ["Gerekmiyor", "Kutuda Var", "Yeni Takıldı", "Eksik"])
            
        notlar = st.text_area("Ofis Notları / Özel Detaylar")
        kaydet_butonu = st.form_submit_button("Projeyi Kaydet")
        
        if kaydet_butonu:
            if musteri_adi:
                final_usta = secilen_usta if secilen_usta != "Seçiniz..." else ""
                
                icerik_parcalari = []
                if kolon_sayisi > 0:
                    icerik_parcalari.append(f"{kolon_sayisi} Kolon")
                if ic_tesisat_sayisi > 0:
                    icerik_parcalari.append(f"{ic_tesisat_sayisi} İç Tesisat")
                if diger_icerikler:
                    icerik_parcalari.extend(diger_icerikler)
                
                icerik_metni = ", ".join(icerik_parcalari) if icerik_parcalari else "Belirtilmedi"
                tarih_metni = secilen_proje_tarihi.strftime("%Y-%m-%d")
                
                veri_ekle(tarih_metni, musteri_adi, gelis_yolu, final_usta, armadas_durumu, eksik_nedeni, toplam_bedel, alinan_odeme, odeme_yontemi, sayac_seri_no, regulator_durumu, icerik_metni, notlar)
                st.success(f"'{musteri_adi}' projesi kaydedildi!")
                st.rerun()
            else:
                st.error("Lütfen Müşteri/Proje Adı alanını doldurun.")

# SEKME 2: İŞ TAKİP TABLOSU
with sekme2:
    st.header("Merkezi İş Takip Ekranı")
    mevcut_veri = veri_cek()
    
    if 'kombi_marka_model' in mevcut_veri.columns:
        mevcut_veri = mevcut_veri.drop(columns=['kombi_marka_model'])
        
    if not mevcut_veri.empty:
        arama = st.text_input("🔍 Arama Yapın:")
        filtered_veri = mevcut_veri.copy()
        
        if arama:
            filtered_veri = filtered_veri[
                filtered_veri['musteri_adi'].str.contains(arama, case=False, na=False) | 
                filtered_veri['usta'].str.contains(arama, case=False, na=False) |
                filtered_veri['proje_icerigi'].str.contains(arama, case=False, na=False) |
                filtered_veri['sayac_seri_no'].str.contains(arama, case=False, na=False)
            ]
        
        filtered_veri.insert(0, "Sil", False)
        
        guncellenmis_veri = st.data_editor(
            filtered_veri,
            column_order=[
                "Sil", "tarih", "musteri_adi", "proje_icerigi", "usta", 
                "armadas_durumu", "toplam_bedel", "alinan_odeme", 
                "kalan_alacak", "odeme_yontemi", "sayac_seri_no", "regulator_durumu", "notlar"
            ],
            column_config={
                "Sil": st.column_config.CheckboxColumn("🗑️ Seç", default=False),
                "id": None, "eksik_nedeni": None, "tarih": "Kayıt Tarihi", "musteri_adi": "Müşteri Adı",
                "gelis_yolu": st.column_config.SelectboxColumn("Geliş Yolu", options=["WhatsApp", "Elden Geldi", "Telefon", "Saha Tespiti", "Excel Aktarımı"]),
                "usta": st.column_config.SelectboxColumn("Sorumlu Usta", options=[""] + tum_kayitli_ustalar),
                "proje_icerigi": "Proje İçeriği", 
                "armadas_durumu": st.column_config.SelectboxColumn("Armadaş Durumu", options=ARMADAS_ADIMLARI),
                "toplam_bedel": st.column_config.NumberColumn("Toplam Bedel (TL)", format="%.2f ₺"),
                "alinan_odeme": st.column_config.NumberColumn("Alınan Ödeme (TL)", format="%.2f ₺"),
                "kalan_alacak": st.column_config.NumberColumn("Kalan Alacak (TL)", format="%.2f ₺", disabled=True),
                "odeme_yontemi": st.column_config.SelectboxColumn("Ödeme Tipi", options=["Nakit", "Kredi Kartı", "Havale/EFT", "Ödeme Alınmadı"]),
                "sayac_seri_no": "Sayaç Seri No",
                "regulator_durumu": st.column_config.SelectboxColumn("Regülatör", options=["Gerekmiyor", "Kutuda Var", "Yeni Takıldı", "Eksik"]),
                "notlar": "Notlar"
            },
            disabled=["id", "tarih", "kalan_alacak"],
            hide_index=True,
            use_container_width=True,
            key="merkezi_editor"
        )
        
        silinecek_df = guncellenmis_veri[guncellenmis_veri["Sil"] == True]
        if not silinecek_df.empty:
            if st.button("🗑️ Seçili Projeleri Kalıcı Olarak Sil", type="primary"):
                veri_sil(silinecek_df["id"].tolist())
                st.success("Seçtiğiniz kayıtlar silindi!")
                st.rerun()
                
        eski_kontrol = filtered_veri.drop(columns=["Sil"])
        yeni_kontrol = guncellenmis_veri.drop(columns=["Sil"])
        
        if not yeni_kontrol.equals(eski_kontrol):
            veri_guncelle(yeni_kontrol)
            st.toast("🔄 Değişiklikler kaydedildi!", icon="✅")
    else:
        st.info("Kayıtlı iş bulunmuyor.")

# SEKME 3: FİNANS VE PERFORMANS
with sekme3:
    st.header("📈 Mali ve Performans Analizi")
    finans_df = veri_cek()
    
    if not finans_df.empty:
        finans_df['tarih_dt'] = pd.to_datetime(finans_df['tarih'], errors='coerce').fillna(datetime.now())
        finans_df['ay'] = finans_df['tarih_dt'].dt.strftime('%Y-%m')
        finans_df['hafta'] = finans_df['tarih_dt'].dt.strftime('%Y - %U. Hafta') 
        
        rapor_kapsami = st.radio("📊 Periyot Seçin:", ["📅 Aylık", "📆 Haftalık"], horizontal=True)
        
        if rapor_kapsami == "📅 Aylık":
            mevcut_aylar = sorted(finans_df['ay'].unique(), reverse=True)
            secilen_periyot = st.selectbox("Aylık Periyot:", mevcut_aylar)
            mali_filtre_df = finans_df[finans_df['ay'] == secilen_periyot].copy()
        else:
            mevcut_haftalar = sorted(finans_df['hafta'].unique(), reverse=True)
            secilen_periyot = st.selectbox("Haftalık Periyot:", mevcut_haftalar)
            mali_filtre_df = finans_df[finans_df['hafta'] == secilen_periyot].copy()
            
        t1, t2, t3 = st.columns(3)
        t1.metric(f"💰 Toplam Ciro ({secilen_periyot})", f"{mali_filtre_df['toplam_bedel'].sum():,.2f} ₺")
        t2.metric("✅ Tahsil Edilen", f"{mali_filtre_df['alinan_odeme'].sum():,.2f} ₺")
        t3.metric("🚨 Kalan Alacak", f"{mali_filtre_df['kalan_alacak'].sum():,.2f} ₺")
        
        st.markdown("---")
        mali_filtre_df['usta'] = mali_filtre_df['usta'].fillna('').str.strip()
        usta_mali_df = mali_filtre_df[mali_filtre_df['usta'] != ""]
        
        if not usta_mali_df.empty:
            usta_icerik_ozet = []
            for u_adi, grup in usta_mali_df.groupby('usta'):
                usta_icerik_ozet.append({
                    "Usta Adı": u_adi,
                    "Toplam İş (Adet)": len(grup),
                    "🏢 Kolon Sayısı": grup['proje_icerigi'].str.contains("Kolon", case=False, na=False).sum(),
                    "🔥 İç Tesisat Sayısı": grup['proje_icerigi'].str.contains("İç Tesisat", case=False, na=False).sum(),
                    "Ürettiği Ciro (TL)": grup['toplam_bedel'].sum()
                })
            st.dataframe(pd.DataFrame(usta_icerik_ozet), hide_index=True, use_container_width=True)

# SEKME 4: USTA REHBERİ
with sekme4:
    st.header("👨‍🔧 Usta Rehberi")
    if tum_kayitli_ustalar:
        secilen_detay_usta = st.selectbox("Usta Seçin:", tum_kayitli_ustalar, key="rehber_secim")
        if secilen_detay_usta:
            conn = sqlite3.connect("ofis_takip_v2.db")
            cursor = conn.cursor()
            cursor.execute("SELECT telefon_no FROM ustalar WHERE usta_adi = ?", (secilen_detay_usta,))
            tel_sonuc = cursor.fetchone()
            conn.close()
            usta_tel = tel_sonuc[0] if tel_sonuc and tel_sonuc[0] else "Girilmemiş"
            
            c_g1, c_g2 = st.columns([2, 1])
            with c_g1:
                yeni_tel_girdi = st.text_input("📞 Telefon No Güncelle:", value="" if usta_tel == "Girilmemiş" else usta_tel)
            with c_g2:
                st.write(" "); st.write(" ") 
                if st.button("Telefonu Kaydet"):
                    usta_telefon_guncelle(secilen_detay_usta, yeni_tel_girdi)
                    st.success("Telefon güncellendi!")
                    st.rerun()

# SEKME 5: EXCEL YÜKLE / İNDİR
with sekme5:
    st.header("🔄 Excel Senkronizasyonu")
    c_import, c_export = st.columns(2)
    
    with c_import:
        st.subheader("📥 Excel Yükle")
        yuklenen_excel = st.file_uploader("Excel Dosyası Seçin", type=["xlsx", "xls"])
        if yuklenen_excel is not None:
            if st.button("🚀 Verileri Aktar"):
                df_excel = pd.read_excel(yuklenen_excel)
                eklenen = excelden_toplu_veri_ekle(df_excel)
                st.success(f"{eklenen} adet proje eklendi.")
                st.rerun()

    with c_export:
        st.subheader("📤 Excel İndir")
        malzeme_df = veri_cek()
        if not malzeme_df.empty:
            st.download_button(
                label="📊 Tüm Veritabanını İndir",
                data=malzeme_df.to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"Gunes_Muhendislik_Yedek_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
