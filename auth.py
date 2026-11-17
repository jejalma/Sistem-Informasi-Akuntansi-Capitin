from database import get_conn
from security import verify_password, hash_password, ROLE_LABELS
from services import ServiceError
from database import now_iso
import time

_MAX_ATTEMPTS = 5
_LOCK_SECONDS = 300
_failed: dict[str, list[float]] = {}


def _recent_failures(email: str) -> list[float]:
    cutoff = time.time() - _LOCK_SECONDS
    _failed[email] = [t for t in _failed.get(email, []) if t > cutoff]
    return _failed[email]


def authenticate(email: str, password: str) -> dict:
    email = (email or '').strip().lower()
    if not email or not password:
        raise ServiceError('Email dan kata sandi wajib diisi.')
    if len(_recent_failures(email)) >= _MAX_ATTEMPTS:
        raise ServiceError('Terlalu banyak percobaan gagal. Coba lagi dalam 5 menit.')
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM users WHERE lower(email) = ?', (email,)).fetchone()
    if not row or not verify_password(password, row['password_hash']):
        _failed[email].append(time.time())
        raise ServiceError('Email atau kata sandi salah.')
    _failed.pop(email, None)
    return _public(row)


def _public(row) -> dict:
    return {'id': row['id'], 'name': row['name'], 'email': row['email'], 'role': row['role']}


def get_user(user_id: int | None) -> dict | None:
    if not user_id:
        return None
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return _public(row) if row else None


def list_users() -> list[dict]:
    with get_conn() as conn:
        return [_public(r) for r in conn.execute('SELECT * FROM users ORDER BY id')]


def save_user(data: dict, user_id: int | None = None) -> int:
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    role = data.get('role')
    password = data.get('password') or ''
    if not name or '@' not in email:
        raise ServiceError('Nama dan email yang valid wajib diisi.')
    if role not in ROLE_LABELS:
        raise ServiceError('Peran tidak valid.')
    if not user_id and len(password) < 6:
        raise ServiceError('Kata sandi minimal 6 karakter.')
    if password and len(password) < 6:
        raise ServiceError('Kata sandi minimal 6 karakter.')
    with get_conn() as conn:
        if conn.execute('SELECT 1 FROM users WHERE lower(email)=? AND id IS NOT ?', (email, user_id)).fetchone():
            raise ServiceError('Email sudah terdaftar.')
        if user_id:
            current = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
            if current['role'] == 'admin' and role != 'admin' and _admin_count(conn) <= 1:
                raise ServiceError('Minimal harus ada satu Admin.')
            conn.execute('UPDATE users SET name=?, email=?, role=? WHERE id=?', (name, email, role, user_id))
            if password:
                conn.execute('UPDATE users SET password_hash=? WHERE id=?', (hash_password(password), user_id))
            return user_id
        cur = conn.execute('INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?,?,?,?,?)',
                           (name, email, hash_password(password), role, now_iso()))
        return cur.lastrowid


def _admin_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]


def delete_user(user_id: int, acting_user_id: int) -> None:
    if user_id == acting_user_id:
        raise ServiceError('Anda tidak dapat menghapus akun sendiri.')
    with get_conn() as conn:
        row = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row:
            raise ServiceError('Pengguna tidak ditemukan.')
        if row['role'] == 'admin' and _admin_count(conn) <= 1:
            raise ServiceError('Minimal harus ada satu Admin.')
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
