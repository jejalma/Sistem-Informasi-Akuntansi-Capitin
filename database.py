import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import config
from security import hash_password

_db_path = config.DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','akuntan','kasir')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('ASET','KEWAJIBAN','MODAL','PENDAPATAN','BEBAN')),
    normal_balance TEXT NOT NULL CHECK (normal_balance IN ('DEBIT','KREDIT')),
    opening_balance REAL NOT NULL DEFAULT 0,
    system_key TEXT UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    size_desc TEXT NOT NULL DEFAULT '',
    price_per_kg REAL NOT NULL CHECK (price_per_kg >= 0)
);
CREATE TABLE IF NOT EXISTS collectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'Desa',
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    position TEXT NOT NULL DEFAULT 'Pekerja Tambak',
    daily_wage REAL NOT NULL CHECK (daily_wage >= 0),
    phone TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_no TEXT UNIQUE,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    payment TEXT,
    qty REAL,
    unit_price REAL,
    collector_id INTEGER REFERENCES collectors(id),
    product_id INTEGER REFERENCES products(id),
    employee_id INTEGER REFERENCES employees(id),
    account_id INTEGER REFERENCES accounts(id),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_no TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'OTOMATIS',
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    debit REAL NOT NULL DEFAULT 0,
    credit REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    date TEXT NOT NULL,
    kind TEXT NOT NULL,
    qty_kg REAL NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lines_entry ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_lines_account ON journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_entries_date ON journal_entries(date);
CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_movements(product_id);
"""

SEED_ACCOUNTS = [
    ('1-1000', 'Kas', 'ASET', 'DEBIT', 'kas'),
    ('1-1100', 'Bank', 'ASET', 'DEBIT', 'bank'),
    ('1-1200', 'Piutang Usaha', 'ASET', 'DEBIT', 'piutang'),
    ('1-1300', 'Persediaan Kepiting', 'ASET', 'DEBIT', None),
    ('1-1400', 'Persediaan Pakan', 'ASET', 'DEBIT', 'persediaan_pakan'),
    ('1-2000', 'Peralatan Tambak', 'ASET', 'DEBIT', None),
    ('1-2100', 'Akumulasi Penyusutan Peralatan', 'ASET', 'KREDIT', None),
    ('2-1000', 'Hutang Usaha', 'KEWAJIBAN', 'KREDIT', None),
    ('2-1100', 'Hutang Gaji', 'KEWAJIBAN', 'KREDIT', None),
    ('3-1000', 'Modal Bapak Salim', 'MODAL', 'KREDIT', 'modal'),
    ('3-2000', 'Prive', 'MODAL', 'DEBIT', 'prive'),
    ('4-1000', 'Pendapatan Penjualan Kepiting', 'PENDAPATAN', 'KREDIT', 'pendapatan'),
    ('4-2000', 'Pendapatan Lain-lain', 'PENDAPATAN', 'KREDIT', None),
    ('5-1000', 'Harga Pokok Penjualan', 'BEBAN', 'DEBIT', None),
    ('5-2000', 'Beban Pakan Ikan Rucah', 'BEBAN', 'DEBIT', 'beban_pakan'),
    ('5-3000', 'Beban Gaji Karyawan', 'BEBAN', 'DEBIT', 'beban_gaji'),
    ('5-4000', 'Beban Listrik & Air', 'BEBAN', 'DEBIT', None),
    ('5-5000', 'Beban Pemeliharaan Tambak', 'BEBAN', 'DEBIT', None),
    ('5-6000', 'Beban Operasional Lain', 'BEBAN', 'DEBIT', 'beban_operasional'),
]

SEED_PRODUCTS = [
    ('Kepiting Jantan / Campur', '3-4 ekor per kg', 110000),
    ('Kepiting Super', '2-3 ekor per kg', 160000),
    ('Kepiting Betina Telur', 'Cangkang keras, penuh telur', 220000),
]

SEED_EMPLOYEES = [
    ('Pekerja Tambak 1', 'Pemberi pakan & kebersihan petak', 120000),
    ('Pekerja Tambak 2', 'Pemantau pematang & pintu air', 120000),
]

SEED_COLLECTORS = [
    ('Pengepul Desa Morodemak (contoh)', 'Desa', '', 'Desa Morodemak, Bonang'),
    ('Pedagang Pengumpul Bonang (contoh)', 'Kecamatan', '', 'Kecamatan Bonang, Demak'),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def set_db_path(path: str) -> None:
    global _db_path
    _db_path = path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def init_db(seed_users=None) -> None:
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _seed(conn, seed_users if seed_users is not None else config.SEED_USERS)
        conn.execute("UPDATE accounts SET system_key = 'persediaan_pakan' WHERE code = '1-1400' AND system_key IS NULL")
        conn.execute("UPDATE accounts SET system_key = 'beban_pakan' WHERE code = '5-2000' AND system_key IS NULL")


def _seed(conn: sqlite3.Connection, seed_users) -> None:
    for name, email, password, role in seed_users:
        if not conn.execute('SELECT 1 FROM users WHERE email = ?', (email,)).fetchone():
            conn.execute(
                'INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?,?,?,?,?)',
                (name, email, hash_password(password), role, now_iso()),
            )
    if not conn.execute('SELECT 1 FROM accounts LIMIT 1').fetchone():
        conn.executemany(
            'INSERT INTO accounts (code, name, category, normal_balance, system_key) VALUES (?,?,?,?,?)',
            SEED_ACCOUNTS,
        )
    if not conn.execute('SELECT 1 FROM products LIMIT 1').fetchone():
        conn.executemany('INSERT INTO products (name, size_desc, price_per_kg) VALUES (?,?,?)', SEED_PRODUCTS)
    if not conn.execute('SELECT 1 FROM employees LIMIT 1').fetchone():
        conn.executemany('INSERT INTO employees (name, position, daily_wage) VALUES (?,?,?)', SEED_EMPLOYEES)
    if not conn.execute('SELECT 1 FROM collectors LIMIT 1').fetchone():
        conn.executemany('INSERT INTO collectors (name, level, phone, address) VALUES (?,?,?,?)', SEED_COLLECTORS)
