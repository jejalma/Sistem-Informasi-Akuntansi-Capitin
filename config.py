import os
from pathlib import Path

# Konfigurasi aplikasi
APP_NAME = 'Capit-in'
COMPANY_NAME = 'Tambak Kepiting Bapak Salim'
COMPANY_ADDRESS = 'Jl. Tambak Layur, Desa Morodemak, Kec. Bonang, Kab. Demak, Jawa Tengah'

# Nilai langsung yang aman (Tanpa os.environ)
DB_PATH = 'database.db'
PORT = 8081
STORAGE_SECRET = 'rahasia-anda-bebas'

SEED_USERS = [
    ('Bapak Salim', 'admin@capit.in', 'admin123', 'admin'),
    ('Akuntan', 'akuntan@capit.in', 'akuntan123', 'akuntan'),
    ('Kasir', 'kasir@capit.in', 'kasir123', 'kasir'),
]