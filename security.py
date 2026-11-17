import bcrypt

ROLE_LABELS = {'admin': 'Admin', 'akuntan': 'Akuntan', 'kasir': 'Kasir'}

_BASE = {'tx.create', 'stock.create'}
PERMISSIONS = {
    'kasir': _BASE,
    'akuntan': _BASE | {'master.create', 'master.edit', 'journal.manual'},
    'admin': _BASE | {'master.create', 'master.edit', 'journal.manual', 'delete', 'users.manage'},
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def can(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())
