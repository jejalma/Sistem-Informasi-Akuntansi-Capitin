from database import get_conn, now_iso
from services import ServiceError


def validate_lines(lines: list[tuple[int, float, float]]) -> tuple[float, float]:
    if len(lines) < 2:
        raise ServiceError('Jurnal minimal memiliki 2 baris (debit dan kredit).')
    for account_id, debit, credit in lines:
        if not account_id:
            raise ServiceError('Setiap baris jurnal wajib memilih akun.')
        if debit < 0 or credit < 0 or (debit > 0) == (credit > 0):
            raise ServiceError('Setiap baris harus berisi debit ATAU kredit (lebih dari 0).')
    total_debit = round(sum(line[1] for line in lines), 2)
    total_credit = round(sum(line[2] for line in lines), 2)
    if total_debit != total_credit:
        raise ServiceError(f'Jurnal tidak seimbang: debit {total_debit:,.0f} vs kredit {total_credit:,.0f}.')
    return total_debit, total_credit


def post_entry(conn, *, date: str, description: str, lines: list[tuple[int, float, float]], ref_no: str,
               source: str = 'OTOMATIS', transaction_id: int | None = None, user_id: int | None = None) -> int:
    validate_lines(lines)
    cur = conn.execute(
        'INSERT INTO journal_entries (ref_no, date, description, source, transaction_id, created_by, created_at) '
        'VALUES (?,?,?,?,?,?,?)', (ref_no, date, description, source, transaction_id, user_id, now_iso()))
    entry_id = cur.lastrowid
    conn.executemany('INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)',
                     [(entry_id, a, round(d, 2), round(c, 2)) for a, d, c in lines])
    return entry_id


def create_manual_entry(date: str, description: str, lines: list[tuple[int, float, float]], user_id: int) -> int:
    if not date:
        raise ServiceError('Tanggal wajib diisi.')
    if not (description or '').strip():
        raise ServiceError('Keterangan jurnal wajib diisi.')
    with get_conn() as conn:
        entry_id = post_entry(conn, date=date, description=description.strip(), lines=lines, ref_no='JU-TMP',
                              source='MANUAL', user_id=user_id)
        conn.execute('UPDATE journal_entries SET ref_no = ? WHERE id = ?', (f'JU-{entry_id:05d}', entry_id))
        return entry_id


def delete_manual_entry(entry_id: int) -> None:
    with get_conn() as conn:
        row = conn.execute('SELECT source FROM journal_entries WHERE id = ?', (entry_id,)).fetchone()
        if not row:
            raise ServiceError('Jurnal tidak ditemukan.')
        if row['source'] != 'MANUAL':
            raise ServiceError('Jurnal otomatis hanya bisa dihapus dengan menghapus transaksinya.')
        conn.execute('DELETE FROM journal_entries WHERE id = ?', (entry_id,))
