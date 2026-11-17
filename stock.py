from database import get_conn, now_iso
from services import ServiceError
from services.master import product_stock

KINDS = {
    'PANEN': ('Panen (masuk)', 1),
    'SUSUT': ('Mati / Susut (keluar)', -1),
    'KOREKSI_TAMBAH': ('Koreksi Tambah', 1),
    'KOREKSI_KURANG': ('Koreksi Kurang', -1),
}
KIND_LABELS = {**{k: v[0] for k, v in KINDS.items()}, 'PENJUALAN': 'Penjualan (keluar)'}


def add_movement(product_id: int, date: str, kind: str, qty: float, note: str, user_id: int | None) -> int:
    if kind not in KINDS:
        raise ServiceError('Jenis pergerakan stok tidak valid.')
    if not product_id:
        raise ServiceError('Produk wajib dipilih.')
    if not date:
        raise ServiceError('Tanggal wajib diisi.')
    if not qty or qty <= 0:
        raise ServiceError('Jumlah (kg) harus lebih dari 0.')
    signed = round(qty * KINDS[kind][1], 3)
    with get_conn() as conn:
        if product_stock(conn, product_id) + signed < 0:
            raise ServiceError('Stok tidak mencukupi untuk pengurangan ini.')
        cur = conn.execute(
            'INSERT INTO stock_movements (product_id, date, kind, qty_kg, note, created_by, created_at) '
            'VALUES (?,?,?,?,?,?,?)', (product_id, date, kind, signed, (note or '').strip(), user_id, now_iso()))
        return cur.lastrowid


def delete_movement(movement_id: int) -> None:
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM stock_movements WHERE id = ?', (movement_id,)).fetchone()
        if not row:
            raise ServiceError('Data stok tidak ditemukan.')
        if row['transaction_id']:
            raise ServiceError('Pergerakan dari penjualan hanya bisa dihapus lewat menu Transaksi.')
        if product_stock(conn, row['product_id']) - row['qty_kg'] < 0:
            raise ServiceError('Menghapus data ini membuat stok menjadi minus.')
        conn.execute('DELETE FROM stock_movements WHERE id = ?', (movement_id,))


def list_movements(product_id: int | None = None, start: str | None = None, end: str | None = None) -> list[dict]:
    sql = ('SELECT s.*, p.name AS product_name FROM stock_movements s JOIN products p ON p.id = s.product_id '
           'WHERE (? IS NULL OR s.product_id = ?) AND (? IS NULL OR s.date >= ?) AND (? IS NULL OR s.date <= ?) '
           'ORDER BY s.date DESC, s.id DESC')
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, (product_id, product_id, start, start, end, end))]
