from services import master
from services.auth import delete_user, list_users, save_user
from security import ROLE_LABELS
from views.components import badge
from views.crud import crud_page
from views.fmt import kg, rp
from views.layout import protected


@protected('/produk', 'Produk Kepiting')
def products_page(user: dict) -> None:
    crud_page(
        user, title='Produk Kepiting', subtitle='Kategori kepiting bakau dan harga jual ke pengepul per kg',
        entity='Produk', slug='product', defaults={'price_per_kg': None, 'stock_kg': 0},
        fields=lambda r: [{'key': 'name', 'label': 'Nama produk'},
                          {'key': 'size_desc', 'label': 'Ukuran / keterangan', 'hint': 'Contoh: 2-3 ekor per kg'},
                          {'key': 'price_per_kg', 'label': 'Harga jual per kg (Rp)', 'kind': 'number',
                           'format': '%.0f'},
                          {'key': 'stock_kg', 'label': 'Stok (kg)', 'kind': 'number',
                           'format': '%.1f'}],
        load=master.list_products, save=master.save_product, remove=master.delete_product,
        headers=[('Produk', 'left'), ('Ukuran', 'left'), ('Harga / kg', 'right'), ('Stok', 'right'),
                 ('Nilai Stok', 'right')],
        to_cells=lambda p: [p['name'], p['size_desc'] or '-', rp(p['price_per_kg']), kg(p['stock_kg']),
                            rp((p['stock_kg'] or 0) * (p['price_per_kg'] or 0))])


@protected('/pengepul', 'Pengepul')
def collectors_page(user: dict) -> None:
    crud_page(
        user, title='Pengepul', subtitle='Pembeli hasil panen tingkat desa / kecamatan',
        entity='Pengepul', slug='collector', defaults={'level': 'Desa'},
        fields=lambda r: [{'key': 'name', 'label': 'Nama pengepul'},
                          {'key': 'level', 'label': 'Tingkat', 'kind': 'select',
                           'options': master.COLLECTOR_LEVELS},
                          {'key': 'phone', 'label': 'No. telepon'}, {'key': 'address', 'label': 'Alamat'}
                          ],
        load=master.list_collectors, save=master.save_collector, remove=master.delete_collector,
        headers=[('Nama', 'left'), ('Tingkat', 'left'), ('Telepon', 'left'), ('Alamat', 'left'),
                 ('Sisa Piutang', 'right')],
        to_cells=lambda c: [c['name'], lambda c=c: badge(c['level'], 'teal'), c['phone'] or '-', c['address'] or '-',
                            rp(c['receivable'])])


@protected('/karyawan', 'Karyawan')
def employees_page(user: dict) -> None:
    crud_page(
        user, title='Karyawan', subtitle='Pekerja tambak dengan sistem upah harian',
        entity='Karyawan', slug='employee', defaults={'daily_wage': 120000, 'active': True,
                                                      'position': 'Pekerja Tambak'},
        fields=lambda r: [{'key': 'name', 'label': 'Nama karyawan'}, {'key': 'position', 'label': 'Tugas / jabatan'},
                          {'key': 'daily_wage', 'label': 'Upah harian (Rp)', 'kind': 'number', 'format': '%.0f'},
                          {'key': 'phone', 'label': 'No. telepon'},
                          {'key': 'active', 'label': 'Aktif bekerja', 'kind': 'switch'}],
        load=master.list_employees, save=master.save_employee, remove=master.delete_employee,
        headers=[('Nama', 'left'), ('Tugas', 'left'), ('Upah Harian', 'right'), ('Status', 'left')],
        to_cells=lambda e: [e['name'], e['position'] or '-', rp(e['daily_wage']),
                            lambda e=e: badge('AKTIF' if e['active'] else 'NONAKTIF',
                                              'moss' if e['active'] else 'sand')])


@protected('/pengguna', 'Pengguna', 'users.manage')
def users_page(user: dict) -> None:
    crud_page(
        user, title='Pengguna', subtitle='Akun login dan hak akses: Admin, Akuntan, Kasir',
        entity='Pengguna', slug='user', defaults={'role': 'kasir'},
        fields=lambda r: [{'key': 'name', 'label': 'Nama'}, {'key': 'email', 'label': 'Email'},
                          {'key': 'role', 'label': 'Peran', 'kind': 'select', 'options': ROLE_LABELS},
                          {'key': 'password', 'label': 'Kata sandi baru (kosongkan jika tetap)' if r
                           else 'Kata sandi', 'kind': 'password'}],
        load=list_users, save=save_user, remove=lambda uid: delete_user(uid, user['id']),
        create_perm='users.manage', edit_perm='users.manage', delete_perm='users.manage',
        headers=[('Nama', 'left'), ('Email', 'left'), ('Peran', 'left')],
        to_cells=lambda u: [u['name'], u['email'], lambda u=u: badge(ROLE_LABELS[u['role']],
                                                                    {'admin': 'teal', 'akuntan': 'moss',
                                                                     'kasir': 'ember'}[u['role']])])
