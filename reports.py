from datetime import date, timedelta

from database import get_conn
from services.accounts import opening_status

ACTIVITY_TITLES = {'OPERASI': 'Arus Kas dari Aktivitas Operasi', 'INVESTASI': 'Arus Kas dari Aktivitas Investasi',
                   'PENDANAAN': 'Arus Kas dari Aktivitas Pendanaan'}
MONTHS_ID = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']


# ---------- periode ----------
def month_range(day: date) -> tuple[str, str]:
    first = day.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return first.isoformat(), (nxt - timedelta(days=1)).isoformat()


def _day_before(iso: str) -> str:
    return (date.fromisoformat(iso) - timedelta(days=1)).isoformat()


# ---------- dasar ----------
def _accounts(conn) -> list[dict]:
    return [dict(r) for r in conn.execute('SELECT * FROM accounts ORDER BY code')]


def _movements(conn, start: str | None = None, end: str | None = None) -> dict[int, tuple[float, float]]:
    rows = conn.execute(
        'SELECT l.account_id, SUM(l.debit), SUM(l.credit) FROM journal_lines l '
        'JOIN journal_entries e ON e.id = l.entry_id '
        'WHERE (? IS NULL OR e.date >= ?) AND (? IS NULL OR e.date <= ?) GROUP BY l.account_id',
        (start, start, end, end)).fetchall()
    return {r[0]: (r[1] or 0.0, r[2] or 0.0) for r in rows}


def signed(account: dict, debit: float, credit: float) -> float:
    return debit - credit if account['normal_balance'] == 'DEBIT' else credit - debit


def _balances(conn, accounts: list[dict], end: str | None) -> dict[int, float]:
    moves = _movements(conn, None, end)
    return {a['id']: round(a['opening_balance'] + signed(a, *moves.get(a['id'], (0.0, 0.0))), 2) for a in accounts}


def _side_amount(account: dict, balance: float, positive_side: str) -> float:
    return balance if account['normal_balance'] == positive_side else -balance


# ---------- jurnal & buku besar ----------
def general_journal(start: str | None, end: str | None) -> dict:
    with get_conn() as conn:
        entries = [dict(r) for r in conn.execute(
            'SELECT * FROM journal_entries WHERE (? IS NULL OR date >= ?) AND (? IS NULL OR date <= ?) '
            'ORDER BY date, id', (start, start, end, end))]
        for entry in entries:
            entry['lines'] = [dict(r) for r in conn.execute(
                'SELECT l.*, a.code, a.name FROM journal_lines l JOIN accounts a ON a.id = l.account_id '
                'WHERE l.entry_id = ? ORDER BY l.credit > 0, l.id', (entry['id'],))]
    total_d = round(sum(ln['debit'] for e in entries for ln in e['lines']), 2)
    total_c = round(sum(ln['credit'] for e in entries for ln in e['lines']), 2)
    return {'entries': entries, 'total_debit': total_d, 'total_credit': total_c, 'balanced': total_d == total_c}


def ledger(account_id: int, start: str | None, end: str | None) -> dict:
    with get_conn() as conn:
        account = dict(conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone())
        before = _movements(conn, None, _day_before(start)).get(account_id, (0.0, 0.0)) if start else (0.0, 0.0)
        opening = round(account['opening_balance'] + signed(account, *before), 2)
        lines = conn.execute(
            'SELECT e.date, e.ref_no, e.description, l.debit, l.credit FROM journal_lines l '
            'JOIN journal_entries e ON e.id = l.entry_id WHERE l.account_id = ? '
            'AND (? IS NULL OR e.date >= ?) AND (? IS NULL OR e.date <= ?) ORDER BY e.date, e.id, l.id',
            (account_id, start, start, end, end)).fetchall()
    balance, rows = opening, []
    for ln in lines:
        balance = round(balance + signed(account, ln['debit'], ln['credit']), 2)
        rows.append({**dict(ln), 'balance': balance})
    return {'account': account, 'opening': opening, 'rows': rows, 'closing': balance,
            'total_debit': round(sum(r['debit'] for r in rows), 2),
            'total_credit': round(sum(r['credit'] for r in rows), 2)}


def trial_balance(end: str | None) -> dict:
    with get_conn() as conn:
        accounts = _accounts(conn)
        balances = _balances(conn, accounts, end)
    rows = []
    for acc in accounts:
        debit_side = _side_amount(acc, balances[acc['id']], 'DEBIT')
        rows.append({**acc, 'debit': max(debit_side, 0.0), 'credit': max(-debit_side, 0.0)})
    total_d = round(sum(r['debit'] for r in rows), 2)
    total_c = round(sum(r['credit'] for r in rows), 2)
    return {'rows': rows, 'total_debit': total_d, 'total_credit': total_c, 'balanced': total_d == total_c}


# ---------- laporan keuangan ----------
def income_statement(start: str | None, end: str | None) -> dict:
    with get_conn() as conn:
        accounts = _accounts(conn)
        moves = _movements(conn, start, end)

    def section(category: str) -> list[dict]:
        return [{'code': a['code'], 'name': a['name'], 'amount': round(signed(a, *moves.get(a['id'], (0, 0))), 2)}
                for a in accounts if a['category'] == category]

    revenues, expenses = section('PENDAPATAN'), section('BEBAN')
    total_rev = round(sum(r['amount'] for r in revenues), 2)
    total_exp = round(sum(r['amount'] for r in expenses), 2)
    return {'revenues': revenues, 'expenses': expenses, 'total_revenue': total_rev, 'total_expense': total_exp,
            'net_income': round(total_rev - total_exp, 2)}


def balance_sheet(end: str | None) -> dict:
    with get_conn() as conn:
        accounts = _accounts(conn)
        balances = _balances(conn, accounts, end)

    def section(category: str, positive_side: str) -> list[dict]:
        return [{'code': a['code'], 'name': a['name'], 'amount': _side_amount(a, balances[a['id']], positive_side)}
                for a in accounts if a['category'] == category]

    earnings = sum(_side_amount(a, balances[a['id']], 'KREDIT') for a in accounts
                   if a['category'] in ('PENDAPATAN', 'BEBAN'))
    assets, liabilities = section('ASET', 'DEBIT'), section('KEWAJIBAN', 'KREDIT')
    equity = section('MODAL', 'KREDIT') + [{'code': '', 'name': 'Laba (Rugi) Berjalan', 'amount': round(earnings, 2)}]
    total_assets = round(sum(r['amount'] for r in assets), 2)
    total_liab = round(sum(r['amount'] for r in liabilities), 2)
    total_equity = round(sum(r['amount'] for r in equity), 2)
    return {'assets': assets, 'liabilities': liabilities, 'equity': equity, 'total_assets': total_assets,
            'total_liabilities': total_liab, 'total_equity': total_equity,
            'balanced': abs(total_assets - (total_liab + total_equity)) < 0.005}


def _classify(counter_accounts: list[dict]) -> str:
    if any(a['category'] == 'MODAL' or a['code'].startswith('2-2') for a in counter_accounts):
        return 'PENDANAAN'
    if any(a['category'] == 'ASET' and a['code'].startswith('1-2') for a in counter_accounts):
        return 'INVESTASI'
    return 'OPERASI'


def cash_flow(start: str | None, end: str | None) -> dict:
    with get_conn() as conn:
        accounts = _accounts(conn)
        by_id = {a['id']: a for a in accounts}
        cash_ids = {a['id'] for a in accounts if a['system_key'] in ('kas', 'bank')}
        opening_bal = _balances(conn, accounts, _day_before(start)) if start else {
            a['id']: a['opening_balance'] for a in accounts}
        opening = round(sum(_side_amount(by_id[i], opening_bal[i], 'DEBIT') for i in cash_ids), 2)
        lines = conn.execute(
            'SELECT l.entry_id, l.account_id, l.debit, l.credit FROM journal_lines l '
            'JOIN journal_entries e ON e.id = l.entry_id '
            'WHERE (? IS NULL OR e.date >= ?) AND (? IS NULL OR e.date <= ?)', (start, start, end, end)).fetchall()
    entries: dict[int, list] = {}
    for ln in lines:
        entries.setdefault(ln['entry_id'], []).append(ln)
    groups: dict[str, dict[str, float]] = {k: {} for k in ACTIVITY_TITLES}
    for entry_lines in entries.values():
        cash_net = sum(ln['debit'] - ln['credit'] for ln in entry_lines if ln['account_id'] in cash_ids)
        if abs(cash_net) < 0.005:
            continue
        counters = [ln for ln in entry_lines if ln['account_id'] not in cash_ids]
        counter_accs = [by_id[ln['account_id']] for ln in counters]
        main = max(counters, key=lambda ln: ln['debit'] + ln['credit'])
        label = by_id[main['account_id']]['name']
        bucket = groups[_classify(counter_accs)]
        bucket[label] = bucket.get(label, 0.0) + cash_net
    sections = []
    for key, title in ACTIVITY_TITLES.items():
        rows = [{'label': k, 'amount': round(v, 2)} for k, v in groups[key].items()]
        sections.append({'key': key, 'title': title, 'rows': rows, 'total': round(sum(r['amount'] for r in rows), 2)})
    net = round(sum(s['total'] for s in sections), 2)
    return {'sections': sections, 'opening': opening, 'net': net, 'closing': round(opening + net, 2)}


def stock_report(start: str | None, end: str | None) -> dict:
    with get_conn() as conn:
        products = [dict(r) for r in conn.execute('SELECT * FROM products ORDER BY price_per_kg')]
        rows = []
        for p in products:
            q = lambda sql, *a: conn.execute(sql, (p['id'], *a)).fetchone()[0] or 0.0  # noqa: E731
            opening = q('SELECT SUM(qty_kg) FROM stock_movements WHERE product_id=? AND date < ?', start) if start else 0.0
            period = ('AND (? IS NULL OR date >= ?) AND (? IS NULL OR date <= ?)', start, start, end, end)
            masuk = q(f'SELECT SUM(qty_kg) FROM stock_movements WHERE product_id=? AND qty_kg > 0 {period[0]}',
                      *period[1:])
            keluar = -q(f'SELECT SUM(qty_kg) FROM stock_movements WHERE product_id=? AND qty_kg < 0 {period[0]}',
                        *period[1:])
            closing = round(opening + masuk - keluar, 3)
            rows.append({'name': p['name'], 'opening': round(opening, 3), 'in': round(masuk, 3),
                         'out': round(keluar, 3), 'closing': closing, 'price': p['price_per_kg'],
                         'value': round(closing * p['price_per_kg'], 2)})
    return {'rows': rows, 'total_kg': round(sum(r['closing'] for r in rows), 3),
            'total_value': round(sum(r['value'] for r in rows), 2)}


# ---------- dashboard ----------
def monthly_series(today: date, months: int = 6) -> list[dict]:
    series, cursor = [], today.replace(day=1)
    for _ in range(months):
        start, end = month_range(cursor)
        stmt = income_statement(start, end)
        series.append({'label': f'{MONTHS_ID[cursor.month - 1]} {cursor.year}', 'revenue': stmt['total_revenue'],
                       'expense': stmt['total_expense']})
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return list(reversed(series))


def dashboard(today: date) -> dict:
    start, end = month_range(today)
    stmt = income_statement(start, end)
    tb = trial_balance(None)
    cash = sum(r['debit'] - r['credit'] for r in tb['rows'] if r.get('_key') in ('kas', 'bank'))
    receivable = sum(r['debit'] - r['credit'] for r in tb['rows'] if r['system_key'] == 'piutang')
    stock = stock_report(None, None)
    with get_conn() as conn:
        accounts = _accounts(conn)
    margin = (stmt['net_income'] / stmt['total_revenue'] * 100) if stmt['total_revenue'] else 0.0
    return {'start': start, 'end': end, 'revenue': stmt['total_revenue'], 'expense': stmt['total_expense'],
            'net_income': stmt['net_income'], 'margin': margin, 'cash': round(cash, 2),
            'receivable': round(receivable, 2), 'stock_kg': stock['total_kg'], 'stock_value': stock['total_value'],
            'opening': opening_status(accounts), 'series': monthly_series(today)}
