
import streamlit as st
from datetime import datetime
from functools import wraps
import json
from pathlib import Path

st.set_page_config(page_title="Kasir Kedai", page_icon="🧾", layout="wide")
DATA = Path(__file__).with_name("produk.json")
LOG = Path(__file__).with_name("aktivitas.log")

# VALIDATION: memeriksa data sebelum digunakan
def validate_product(nama, kategori, harga, stok):
    if not nama or not nama.strip():
        raise ValueError("Nama produk wajib diisi.")
    if kategori not in ["Makanan", "Minuman", "Snack"]:
        raise ValueError("Kategori tidak valid.")
    if harga <= 0:
        raise ValueError("Harga harus lebih dari 0.")
    if stok < 0:
        raise ValueError("Stok tidak boleh negatif.")

# DECORATOR: mencatat aktivitas method
def catat_aktivitas(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        hasil = func(*args, **kwargs)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {func.__name__} berhasil\\n")
        return hasil
    return wrapper

def validasi_pembayaran(func):
    @wraps(func)
    def wrapper(self, uang):
        if not self.items:
            raise ValueError("Keranjang masih kosong.")
        if uang < self.total:
            raise ValueError("Uang pembayaran kurang.")
        return func(self, uang)
    return wrapper

# CONSTRUCTOR: __init__ menginisialisasi objek
class Produk:
    def __init__(self, nama, kategori, harga, stok):
        validate_product(nama, kategori, harga, stok)
        self.nama, self.kategori = nama.strip(), kategori
        self.harga, self.stok = int(harga), int(stok)

class Transaksi:
    def __init__(self, kasir):
        if not kasir.strip():
            raise ValueError("Nama kasir wajib diisi.")
        self.kasir, self.items, self.total = kasir.strip(), [], 0

    @catat_aktivitas
    def tambah_produk(self, produk, jumlah):
       if not all(hasattr(produk, a) for a in ("nama", "harga", "stok")):
            raise TypeError("Data produk tidak valid.")
        if not isinstance(jumlah, int) or jumlah <= 0:
            raise ValueError("Jumlah harus lebih dari 0.")
        if jumlah > produk.stok:
            raise ValueError(f"Stok {produk.nama} tidak mencukupi.")
        produk.stok -= jumlah
        subtotal = produk.harga * jumlah
        self.items.append({"nama": produk.nama, "harga": produk.harga,
                           "jumlah": jumlah, "subtotal": subtotal})
        self.total += subtotal

    @validasi_pembayaran
    @catat_aktivitas
    def bayar(self, uang):
        return int(uang - self.total)

def save_products(products):
    DATA.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

def load_products():
    if not DATA.exists():
        save_products([
            {"nama":"Kopi Susu","kategori":"Minuman","harga":18000,"stok":30},
            {"nama":"Es Teh Manis","kategori":"Minuman","harga":8000,"stok":40},
            {"nama":"Kentang Goreng","kategori":"Snack","harga":15000,"stok":20},
            {"nama":"Roti Bakar","kategori":"Makanan","harga":17000,"stok":15}
        ])
    return [Produk(**p) for p in json.loads(DATA.read_text(encoding="utf-8"))]

def simpan_produk_session():
    save_products([{"nama":p.nama,"kategori":p.kategori,"harga":p.harga,"stok":p.stok}
                   for p in st.session_state.products])

def rp(n):
    return "Rp" + f"{int(n):,}".replace(",", ".")

if "products" not in st.session_state:
    st.session_state.products = load_products()
if "cart" not in st.session_state:
    st.session_state.cart = []
if "receipt" not in st.session_state:
    st.session_state.receipt = None

st.title("🧾 Aplikasi Kasir Kedai")
st.caption("Proyek Python: Constructor • Validation • Decorator")
with st.sidebar:
    page = st.radio("Menu", ["Kasir", "Kelola Produk", "Penjelasan Konsep"])
    kasir = st.text_input("Nama kasir", "Kasir 1")

products = st.session_state.products

if page == "Kasir":
    st.header("Daftar Menu")
    kiri, kanan = st.columns(2)
    with kiri:
        for i, p in enumerate(products):
            with st.container(border=True):
                st.write(f"**{p.nama}** · {p.kategori} · {rp(p.harga)} · Stok {p.stok}")
                qty = st.number_input("Jumlah", 1, max(1, p.stok), 1, key=f"qty{i}", disabled=p.stok == 0)
                if st.button("Tambah ke keranjang", key=f"add{i}", disabled=p.stok == 0):
                    st.session_state.cart.append({"index": i, "qty": int(qty)})
                    st.rerun()
    with kanan:
        st.header("Keranjang")
        total = 0
        for j, item in enumerate(st.session_state.cart):
            p = products[item["index"]]
            subtotal = p.harga * item["qty"]
            total += subtotal
            st.write(f"{p.nama} × {item['qty']} = **{rp(subtotal)}**")
            if st.button("Hapus", key=f"hapus{j}"):
                st.session_state.cart.pop(j)
                st.rerun()
        st.subheader(f"Total: {rp(total)}")
        uang = st.number_input("Uang pembayaran (Rp)", min_value=0, value=int(total), step=1000)
        if st.button("Proses pembayaran", type="primary", use_container_width=True):
            try:
                trx = Transaksi(kasir)
                kebutuhan = {}
                for item in st.session_state.cart:
                    kebutuhan[item["index"]] = kebutuhan.get(item["index"], 0) + item["qty"]
                for idx, jumlah in kebutuhan.items():
                    if jumlah > products[idx].stok:
                        raise ValueError(f"Stok {products[idx].nama} tidak mencukupi.")
                for item in st.session_state.cart:
                    trx.tambah_produk(products[item["index"]], item["qty"])
                kembali = trx.bayar(int(uang))
                st.session_state.receipt = {
                    "kasir": kasir, "waktu": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    "items": trx.items, "total": trx.total, "uang": int(uang), "kembali": kembali
                }
                simpan_produk_session()
                st.session_state.cart = []
                st.success("Pembayaran berhasil.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    if st.session_state.receipt:
        r = st.session_state.receipt
        st.divider()
        st.subheader("Struk transaksi")
        st.write(f"Kasir: {r['kasir']} | {r['waktu']}")
        st.table(r["items"])
        st.write(f"Total: {rp(r['total'])} · Bayar: {rp(r['uang'])} · Kembalian: {rp(r['kembali'])}")
        teks = f"KEDAI\\nKasir: {r['kasir']}\\nWaktu: {r['waktu']}\\n"
        teks += "\\n".join(f"{x['nama']} x{x['jumlah']} = {rp(x['subtotal'])}" for x in r["items"])
        teks += f"\\nTOTAL {rp(r['total'])}\\nBAYAR {rp(r['uang'])}\\nKEMBALIAN {rp(r['kembali'])}"
        st.download_button("Unduh struk TXT", teks, "struk_kasir.txt")

elif page == "Kelola Produk":
    st.header("Tambah Produk")
    with st.form("form_produk", clear_on_submit=True):
        nama = st.text_input("Nama produk")
        kategori = st.selectbox("Kategori", ["Makanan", "Minuman", "Snack"])
        harga = st.number_input("Harga", min_value=0, step=1000)
        stok = st.number_input("Stok", min_value=0, step=1)
        submit = st.form_submit_button("Simpan")
    if submit:
        try:
            baru = Produk(nama, kategori, int(harga), int(stok))
            if any(p.nama.lower() == baru.nama.lower() for p in products):
                raise ValueError("Nama produk sudah ada.")
            products.append(baru)
            simpan_produk_session()
            st.success("Produk ditambahkan.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    st.subheader("Daftar Produk")
    st.dataframe([{"Nama":p.nama, "Kategori":p.kategori, "Harga":rp(p.harga), "Stok":p.stok}
                  for p in products], use_container_width=True, hide_index=True)

else:
    st.header("Penjelasan Tiga Konsep")
    st.subheader("1. Constructor")
    st.code("class Produk:\\n    def __init__(self, nama, kategori, harga, stok):\\n        validate_product(nama, kategori, harga, stok)\\n        self.nama = nama.strip()\\n        self.kategori = kategori\\n        self.harga = int(harga)\\n        self.stok = int(stok)", language="python")
    st.write("Method __init__() adalah constructor yang otomatis dijalankan saat objek Produk dibuat. Constructor mengisi atribut awal objek.")
    st.subheader("2. Validation")
    st.code("def validate_product(nama, kategori, harga, stok):\\n    if not nama or not nama.strip():\\n        raise ValueError('Nama produk wajib diisi.')\\n    if harga <= 0:\\n        raise ValueError('Harga harus lebih dari 0.')\\n    if stok < 0:\\n        raise ValueError('Stok tidak boleh negatif.')", language="python")
    st.write("Validation memeriksa input agar data yang diproses sesuai aturan.")
    st.subheader("3. Decorator")
    st.code("def catat_aktivitas(func):\\n    @wraps(func)\\n    def wrapper(*args, **kwargs):\\n        hasil = func(*args, **kwargs)\\n        # mencatat aktivitas\\n        return hasil\\n    return wrapper\\n\\n@catat_aktivitas\\ndef tambah_produk(self, produk, jumlah):\\n    ...", language="python")
    st.write("Decorator membungkus method untuk menambahkan fungsi pencatatan aktivitas tanpa mengubah isi utama method.")
    st.info("Decorator catat_aktivitas digunakan pada tambah_produk() dan bayar(). Decorator validasi_pembayaran memeriksa keranjang dan uang pembayaran.")

st.caption("Proyek tugas kuliah Python")
