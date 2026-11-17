import sqlite3
from datetime import date

from database import get_conn
from services import ServiceError

COLLECTOR_LEVELS = ['Desa', 'Kecamatan', 'Pedagang Pengumpul', 'Lainnya']

_RECEIVABLE_SQL = """
SELECT COALESCE(SUM(CASE WHEN type='PENJUALAN' AND payment='piutang' THEN amount
                         WHEN type='PENERIMAAN_PIUTANG' THEN -amount ELSE 0 END), 0)
FROM transactions WHERE collector_id = ?
"""


def _text(data: dict, key: str, label: str, required: bool = True) -> str:
    value = (data.get(key) or '').strip()
    if required and not value:
        raise ServiceError(f'{label} wajib diisi.')
    return value


def _money(data: dict, key: str, label: str) -> float:
    value = data.get(key)
    if value is None or float(value) < 0:
        raise ServiceError(f'{label} wajib diisi dan tidak boleh negatif.')
    return round(float(value), 2)


def _save(table: str, values: dict, record_id: int | None) -> int:
    cols = list(values)
    try:
        with get_conn() as conn:
            if record_id:
                conn.execute(f'UPDATE {table} SET {", ".join(f"{c}=?" for c in cols)} WHERE id=?',
                             [*values.values(), record_id])
                return record_id
            cur = conn.execute(f'INSERT INTO {table} ({", ".join(cols)}) VALUES ({", ".join("?" * len(cols))})',
                               list(values.values()))
            return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ServiceError('Data dengan nama yang sama sudah ada.') from exc


def _delete(table: str, record_id: int, usage_sql: list[str], message: str) -> None:
    with get_conn() as conn:
        if any(conn.execute(sql, (record_id,)).fetchone() for sql in usage_sql):
            raise ServiceError(message)
        conn.execute(f'DELETE FROM {table} WHERE id = ?', (record_id,))


# Produk
def product_stock(conn, product_id: int) -> float:
    row = conn.execute('SELECT COALESCE(SUM(qty_kg), 0) FROM stock_movements WHERE product_id = ?',
                       (product_id,)).fetchone()
    return round(row[0], 3)


def list_products() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT p.*, COALESCE((SELECT SUM(qty_kg) FROM stock_movements s WHERE s.product_id = p.id), 0) '
            'AS stock_kg FROM products p ORDER BY p.price_per_kg').fetchall()
    return [{**dict(r), 'stock_kg': round(r['stock_kg'], 3), 'stock_value': r['stock_kg'] * r['price_per_kg']}
            for r in rows]

def save_product(data: dict, product_id: int | None = None) -> int:
    values = {'name': _text(data, 'name', 'Nama produk'), 'size_desc': _text(data, 'size_desc', 'Ukuran', False),
              'price_per_kg': _money(data, 'price_per_kg', 'Harga per kg')}
    return _save('products', values, product_id)

def save_product_with_stock(data: dict, product_id: int | None = None) -> int:
    pid = save_product(data, product_id)
    target = data.get('stock_kg')
    if target in (None, ''):
        return pid
    if float(target) < 0:
        raise ServiceError('Stok tidak boleh negatif.')
    with get_conn() as conn:
        delta = round(float(target) - product_stock(conn, pid), 3)
        if delta:
            conn.execute(
                'INSERT INTO stock_movements (product_id, date, kind, qty_kg, note, created_at) '
                "VALUES (?,?,?,?,?,datetime('now'))",
                (pid, date.today().isoformat(), 'KOREKSI', delta, 'Koreksi stok dari halaman Produk'))
    return pid


def delete_product(product_id: int) -> None:
    _delete('products', product_id,
            ['SELECT 1 FROM stock_movements WHERE product_id=?', 'SELECT 1 FROM transactions WHERE product_id=?'],
            'Produk sudah memiliki riwayat stok/transaksi sehingga tidak dapat dihapus.')


# Pengepul
def collector_receivable(conn, collector_id: int) -> float:
    return round(conn.execute(_RECEIVABLE_SQL, (collector_id,)).fetchone()[0], 2)


def list_collectors() -> list[dict]:
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM collectors ORDER BY name')]
        for row in rows:
            row['receivable'] = collector_receivable(conn, row['id'])
    return rows


def save_collector(data: dict, collector_id: int | None = None) -> int:
    level = data.get('level') or 'Desa'
    if level not in COLLECTOR_LEVELS:
        raise ServiceError('Tingkat pengepul tidak valid.')
    values = {'name': _text(data, 'name', 'Nama pengepul'), 'level': level,
              'phone': _text(data, 'phone', 'Telepon', False), 'address': _text(data, 'address', 'Alamat', False)}
    return _save('collectors', values, collector_id)


def delete_collector(collector_id: int) -> None:
    _delete('collectors', collector_id, ['SELECT 1 FROM transactions WHERE collector_id=?'],
            'Pengepul sudah memiliki transaksi sehingga tidak dapat dihapus.')


# Karyawan
def list_employees(active_only: bool = False) -> list[dict]:
    sql = 'SELECT * FROM employees' + (' WHERE active = 1' if active_only else '') + ' ORDER BY name'
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql)]


def save_employee(data: dict, employee_id: int | None = None) -> int:
    values = {'name': _text(data, 'name', 'Nama karyawan'), 'position': _text(data, 'position', 'Jabatan', False),
              'daily_wage': _money(data, 'daily_wage', 'Upah harian'),
              'phone': _text(data, 'phone', 'Telepon', False), 'active': 1 if data.get('active', True) else 0}
    return _save('employees', values, employee_id)


def delete_employee(employee_id: int) -> None:
    _delete('employees', employee_id, ['SELECT 1 FROM transactions WHERE employee_id=?'],
            'Karyawan sudah memiliki riwayat gaji. Nonaktifkan saja statusnya.')


def entity_counts() -> dict:
    with get_conn() as conn:
        q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
        return {'collectors': q('SELECT COUNT(*) FROM collectors'),
                'employees': q('SELECT COUNT(*) FROM employees WHERE active = 1'),
                'products': q('SELECT COUNT(*) FROM products'),
                'transactions': q('SELECT COUNT(*) FROM transactions')}
