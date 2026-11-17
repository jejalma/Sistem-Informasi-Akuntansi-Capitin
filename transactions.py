from database import get_conn, now_iso
from services import ServiceError
from services.accounts import get_by_key, get_account
from services.journal import post_entry
from services.master import product_stock, collector_receivable

TYPES = {
    'PENJUALAN': ('Penjualan Kepiting', 'PJ'),
    'PENERIMAAN_PIUTANG': ('Penerimaan Piutang', 'PP'),
    'PAKAN': ('Pembelian Pakan', 'PK'),
    'GAJI': ('Pembayaran Gaji', 'GJ'),
    'OPERASIONAL': ('Beban Operasional', 'OP'),
    'MODAL': ('Setoran Modal', 'MD'),
    'PRIVE': ('Pengambilan Prive', 'PV'),
}
PAYMENTS = {'kas': 'Tunai (Kas)', 'bank': 'Transfer (Bank)', 'piutang': 'Kredit (Piutang)'}


def _positive(value, label: str) -> float:
    if value is None or float(value) <= 0:
        raise ServiceError(f'{label} harus lebih dari 0.')
    return float(value)


def _required(value, label: str):
    if not value:
        raise ServiceError(f'{label} wajib dipilih.')
    return value


def _cash_account(conn, payment: str, allow_credit: bool = False) -> dict:
    allowed = ('kas', 'bank', 'piutang') if allow_credit else ('kas', 'bank')
    if payment not in allowed:
        raise ServiceError('Metode pembayaran tidak valid.')
    return get_by_key(conn, payment)


def _row(conn, table: str, record_id: int, label: str) -> dict:
    row = conn.execute(f'SELECT * FROM {table} WHERE id = ?', (record_id,)).fetchone()
    if not row:
        raise ServiceError(f'{label} tidak ditemukan.')
    return dict(row)


def _with_note(text: str, note: str | None) -> str:
    return f'{text} - {note.strip()}' if note and note.strip() else text


def build(conn, tx_type: str, data: dict) -> dict:
    """Validasi input dan susun draf transaksi + baris jurnal (tanpa menyimpan)."""
    if tx_type not in TYPES:
        raise ServiceError('Jenis transaksi tidak valid.')
    if not data.get('date'):
        raise ServiceError('Tanggal wajib diisi.')
    payment = data.get('payment') or 'kas'
    note = data.get('note')
    draft = {'type': tx_type, 'date': data['date'], 'payment': payment, 'qty': None, 'unit_price': None,
             'collector_id': None, 'product_id': None, 'employee_id': None, 'account_id': None, 'stock_delta': None}

    if tx_type == 'PENJUALAN':
        collector = _row(conn, 'collectors', _required(data.get('collector_id'), 'Pengepul'), 'Pengepul')
        product = _row(conn, 'products', _required(data.get('product_id'), 'Produk'), 'Produk')
        qty = _positive(data.get('qty'), 'Jumlah (kg)')
        price = _positive(data.get('unit_price'), 'Harga per kg')
        stock = product_stock(conn, product['id'])
        if qty > stock:
            raise ServiceError(f'Stok {product["name"]} tidak mencukupi (tersedia {stock:g} kg).')
        amount = qty * price
        debit_acc = _cash_account(conn, payment, allow_credit=True)
        credit_acc = get_by_key(conn, 'pendapatan')
        desc = f'Penjualan {product["name"]} {qty:g} kg ke {collector["name"]}'
        draft.update(qty=qty, unit_price=price, collector_id=collector['id'], product_id=product['id'],
                     stock_delta=-qty)
    elif tx_type == 'PENERIMAAN_PIUTANG':
        collector = _row(conn, 'collectors', _required(data.get('collector_id'), 'Pengepul'), 'Pengepul')
        amount = _positive(data.get('amount'), 'Nominal')
        outstanding = collector_receivable(conn, collector['id'])
        if amount > outstanding + 0.005:
            raise ServiceError(f'Nominal melebihi sisa piutang {collector["name"]} (Rp {outstanding:,.0f}).')
        debit_acc = _cash_account(conn, payment)
        credit_acc = get_by_key(conn, 'piutang')
        desc = f'Pelunasan piutang dari {collector["name"]}'
        draft['collector_id'] = collector['id']
    elif tx_type == 'PAKAN':
        qty = _positive(data.get('qty'), 'Jumlah pakan (kg)')
        price = _positive(data.get('unit_price'), 'Harga per kg')
        amount = qty * price
        debit_acc = get_by_key(conn, 'persediaan_pakan')
        credit_acc = _cash_account(conn, payment)
        desc = f'Pembelian ikan rucah {qty:g} kg'
        draft.update(qty=qty, unit_price=price)
    elif tx_type == 'GAJI':
        employee = _row(conn, 'employees', _required(data.get('employee_id'), 'Karyawan'), 'Karyawan')
        days = _positive(data.get('qty'), 'Jumlah hari kerja')
        amount = days * employee['daily_wage']
        debit_acc = get_by_key(conn, 'beban_gaji')
        credit_acc = _cash_account(conn, payment)
        desc = f'Gaji {employee["name"]} {days:g} hari'
        draft.update(qty=days, unit_price=employee['daily_wage'], employee_id=employee['id'])
    elif tx_type == 'OPERASIONAL':
        debit_acc = get_account(conn, _required(data.get('account_id'), 'Akun beban'))
        if debit_acc['category'] != 'BEBAN':
            raise ServiceError('Akun yang dipilih harus berkategori BEBAN.')
        amount = _positive(data.get('amount'), 'Nominal')
        credit_acc = _cash_account(conn, payment)
        desc = debit_acc['name']
        draft['account_id'] = debit_acc['id']
    elif tx_type == 'MODAL':
        amount = _positive(data.get('amount'), 'Nominal')
        debit_acc = _cash_account(conn, payment)
        credit_acc = get_by_key(conn, 'modal')
        desc = 'Setoran modal pemilik'
    else:
        amount = _positive(data.get('amount'), 'Nominal')
        debit_acc = get_by_key(conn, 'prive')
        credit_acc = _cash_account(conn, payment)
        desc = 'Pengambilan prive pemilik'

    amount = round(amount, 2)
    draft.update(amount=amount, description=_with_note(desc, note), lines=[
        {'account_id': debit_acc['id'], 'code': debit_acc['code'], 'name': debit_acc['name'], 'debit': amount,
         'credit': 0.0},
        {'account_id': credit_acc['id'], 'code': credit_acc['code'], 'name': credit_acc['name'], 'debit': 0.0,
         'credit': amount},
    ])
    return draft


def preview(tx_type: str, data: dict) -> dict:
    with get_conn() as conn:
        return build(conn, tx_type, data)


def record(tx_type: str, data: dict, user_id: int | None) -> dict:
    with get_conn() as conn:
        draft = build(conn, tx_type, data)
        cur = conn.execute(
            'INSERT INTO transactions (date, type, description, amount, payment, qty, unit_price, collector_id, '
            'product_id, employee_id, account_id, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (draft['date'], tx_type, draft['description'], draft['amount'], draft['payment'], draft['qty'],
             draft['unit_price'], draft['collector_id'], draft['product_id'], draft['employee_id'],
             draft['account_id'], user_id, now_iso()))
        tx_id = cur.lastrowid
        ref_no = f'{TYPES[tx_type][1]}-{tx_id:05d}'
        conn.execute('UPDATE transactions SET ref_no = ? WHERE id = ?', (ref_no, tx_id))
        post_entry(conn, date=draft['date'], description=draft['description'], ref_no=ref_no,
                   lines=[(ln['account_id'], ln['debit'], ln['credit']) for ln in draft['lines']],
                   transaction_id=tx_id, user_id=user_id)
        if draft['stock_delta']:
            conn.execute(
                'INSERT INTO stock_movements (product_id, date, kind, qty_kg, note, transaction_id, created_by, '
                'created_at) VALUES (?,?,?,?,?,?,?,?)',
                (draft['product_id'], draft['date'], 'PENJUALAN', draft['stock_delta'], ref_no, tx_id, user_id,
                 now_iso()))
        return {**draft, 'id': tx_id, 'ref_no': ref_no}


def delete_transaction(tx_id: int) -> None:
    with get_conn() as conn:
        tx = conn.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,)).fetchone()
        if not tx:
            raise ServiceError('Transaksi tidak ditemukan.')
        if tx['type'] == 'PENJUALAN' and tx['payment'] == 'piutang':
            if collector_receivable(conn, tx['collector_id']) - tx['amount'] < -0.005:
                raise ServiceError('Piutang ini sudah dilunasi. Hapus dulu transaksi penerimaan piutangnya.')
        conn.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))


def list_transactions(tx_type: str | None = None, start: str | None = None, end: str | None = None,
                      search: str | None = None, limit: int | None = None) -> list[dict]:
    sql = ('SELECT t.*, c.name AS collector_name, u.name AS created_by_name FROM transactions t '
           'LEFT JOIN collectors c ON c.id = t.collector_id LEFT JOIN users u ON u.id = t.created_by '
           'WHERE (? IS NULL OR t.type = ?) AND (? IS NULL OR t.date >= ?) AND (? IS NULL OR t.date <= ?) '
           'AND (? IS NULL OR t.description LIKE ? OR t.ref_no LIKE ?) ORDER BY t.date DESC, t.id DESC')
    like = f'%{search.strip()}%' if search and search.strip() else None
    params = [tx_type, tx_type, start, start, end, end, like, like, like]
    if limit:
        sql += ' LIMIT ?'
        params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params)]
