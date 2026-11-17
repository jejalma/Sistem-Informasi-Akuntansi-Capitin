import re

from database import get_conn
from services import ServiceError

CATEGORIES = ['ASET', 'KEWAJIBAN', 'MODAL', 'PENDAPATAN', 'BEBAN']
CATEGORY_PREFIX = {'ASET': '1', 'KEWAJIBAN': '2', 'MODAL': '3', 'PENDAPATAN': '4', 'BEBAN': '5'}
DEFAULT_NORMAL = {'ASET': 'DEBIT', 'KEWAJIBAN': 'KREDIT', 'MODAL': 'KREDIT', 'PENDAPATAN': 'KREDIT', 'BEBAN': 'DEBIT'}
_CODE_RE = re.compile(r'^[1-5]-\d{4}$')


def list_accounts(category: str | None = None) -> list[dict]:
    sql = ('SELECT a.*, EXISTS(SELECT 1 FROM journal_lines l WHERE l.account_id = a.id) AS used '
           'FROM accounts a')
    params: tuple = ()
    if category:
        sql += ' WHERE a.category = ?'
        params = (category,)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql + ' ORDER BY a.code', params)]


def get_by_key(conn, key: str) -> dict:
    row = conn.execute('SELECT * FROM accounts WHERE system_key = ?', (key,)).fetchone()
    if not row:
        raise ServiceError(f'Akun sistem "{key}" tidak ditemukan di Bagan Akun.')
    return dict(row)


def get_account(conn, account_id: int) -> dict:
    row = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
    if not row:
        raise ServiceError('Akun tidak ditemukan.')
    return dict(row)


def _clean(data: dict) -> dict:
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    category = data.get('category')
    normal = data.get('normal_balance') or DEFAULT_NORMAL.get(category)
    opening = float(data.get('opening_balance') or 0)
    if category not in CATEGORIES:
        raise ServiceError('Kategori akun wajib dipilih.')
    prefix = CATEGORY_PREFIX[category]
    if not _CODE_RE.match(code) or not code.startswith(prefix):
        raise ServiceError(f'Kode harus berformat {prefix}-XXXX (diawali {prefix} untuk kategori {category}).')
    if not name:
        raise ServiceError('Nama akun wajib diisi.')
    if normal not in ('DEBIT', 'KREDIT'):
        raise ServiceError('Saldo normal harus DEBIT atau KREDIT.')
    if opening < 0:
        raise ServiceError('Saldo awal tidak boleh negatif.')
    return {'code': code, 'name': name, 'category': category, 'normal_balance': normal,
            'opening_balance': round(opening, 2), 'description': (data.get('description') or '').strip()}


def _ensure_unique_code(conn, code: str, exclude_id: int | None = None) -> None:
    row = conn.execute('SELECT id FROM accounts WHERE code = ? AND id IS NOT ?', (code, exclude_id)).fetchone()
    if row:
        raise ServiceError(f'Kode akun {code} sudah dipakai.')


def is_locked(conn, account: dict) -> bool:
    used = conn.execute('SELECT 1 FROM journal_lines WHERE account_id = ? LIMIT 1', (account['id'],)).fetchone()
    return bool(account['system_key']) or bool(used)


def create_account(data: dict) -> int:
    clean = _clean(data)
    with get_conn() as conn:
        _ensure_unique_code(conn, clean['code'])
        cur = conn.execute(
            'INSERT INTO accounts (code, name, category, normal_balance, opening_balance, description) '
            'VALUES (:code, :name, :category, :normal_balance, :opening_balance, :description)', clean)
        return cur.lastrowid


def update_account(account_id: int, data: dict) -> None:
    clean = _clean(data)
    with get_conn() as conn:
        current = get_account(conn, account_id)
        structural = any(clean[k] != current[k] for k in ('code', 'category', 'normal_balance'))
        if structural and is_locked(conn, current):
            raise ServiceError('Akun inti / akun yang sudah dipakai di jurnal tidak boleh diubah kode, '
                               'kategori, atau saldo normalnya.')
        _ensure_unique_code(conn, clean['code'], account_id)
        conn.execute(
            'UPDATE accounts SET code=:code, name=:name, category=:category, normal_balance=:normal_balance, '
            'opening_balance=:opening_balance, description=:description WHERE id=:id', {**clean, 'id': account_id})


def delete_account(account_id: int) -> None:
    with get_conn() as conn:
        account = get_account(conn, account_id)
        if account['system_key']:
            raise ServiceError('Akun inti tidak dapat dihapus.')
        if is_locked(conn, account):
            raise ServiceError('Akun sudah dipakai di jurnal sehingga tidak dapat dihapus.')
        if conn.execute('SELECT 1 FROM transactions WHERE account_id = ? LIMIT 1', (account_id,)).fetchone():
            raise ServiceError('Akun dipakai pada transaksi sehingga tidak dapat dihapus.')
        conn.execute('DELETE FROM accounts WHERE id = ?', (account_id,))


def set_opening_balances(values: dict[int, float]) -> None:
    if any((v or 0) < 0 for v in values.values()):
        raise ServiceError('Saldo awal tidak boleh negatif.')
    with get_conn() as conn:
        conn.executemany('UPDATE accounts SET opening_balance = ? WHERE id = ?',
                         [(round(float(v or 0), 2), k) for k, v in values.items()])


def opening_status(accounts: list[dict], overrides: dict[int, float] | None = None) -> dict:
    overrides = overrides or {}
    debit = credit = 0.0
    for acc in accounts:
        amount = float(overrides.get(acc['id'], acc['opening_balance']) or 0)
        if acc['normal_balance'] == 'DEBIT':
            debit += amount
        else:
            credit += amount
    diff = round(debit - credit, 2)
    return {'debit': round(debit, 2), 'credit': round(credit, 2), 'diff': diff, 'balanced': abs(diff) < 0.005}
