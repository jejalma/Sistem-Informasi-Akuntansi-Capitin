from nicegui import app, ui
from fastapi.responses import RedirectResponse

from security import can, ROLE_LABELS
from services import auth
from views import theme

NAV = [
    (None, [
        ('/', 'Dashboard', 'dashboard', None),
        ('/transaksi', 'Transaksi', 'receipt_long', None),
        ('/jurnal', 'Jurnal & Buku Besar', 'menu_book', None),
        ('/laporan', 'Laporan Keuangan', 'bar_chart', None),
    ]),
    ('MASTER DATA', [
        ('/produk', 'Produk Kepiting', 'set_meal', None),
        ('/pengepul', 'Pengepul', 'groups', None),
        ('/karyawan', 'Karyawan', 'badge', None),
        ('/akun', 'Bagan Akun', 'account_tree', None),
        ('/stok', 'Stok Kepiting', 'inventory_2', None),
    ]),
    ('SISTEM', [
        ('/pengguna', 'Pengguna', 'admin_panel_settings', 'users.manage'),
    ]),
]


def current_user() -> dict | None:
    return auth.get_user(app.storage.user.get('uid'))


def logout() -> None:
    app.storage.user.clear()
    ui.navigate.to('/login')


def brand(dark: bool = False) -> None:
    with ui.row().classes('items-center gap-3 no-wrap'):
        with ui.element('div').classes(
                'rounded-lg overflow-hidden flex items-center justify-center '
                + ('bg-white/10' if dark else 'bg-teal-soft')).style('width:40px;height:40px'):
            ui.image('/static/logo.png').classes('w-full h-full object-cover')
        with ui.column().classes('gap-0'):
            ui.label('SIA TAMBAK KEPITING').classes(
                'text-[10px] tracking-[0.18em] ' + ('text-white/70' if dark else 'text-muted'))
            ui.label('Capit-in').classes('text-base font-semibold ' + ('text-white' if dark else 'text-ink'))


def _nav_item(path: str, label: str, icon: str, active: bool) -> None:
    tone = 'bg-teal-soft text-primary font-medium' if active else 'text-ink hover:bg-cream'
    slug = path.strip('/') or 'dashboard'
    with ui.link(target=path).classes('no-underline w-full').props(f'data-testid=nav-{slug}'):
        with ui.row().classes(f'w-full items-center gap-3 px-3 py-2 rounded-lg no-wrap {tone}'):
            ui.icon(icon, size='18px')
            ui.label(label).classes('text-sm')


def _shell(user: dict, path: str, title: str) -> None:
    ui.query('body').classes('bg-cream')
    with ui.left_drawer(value=True, bordered=True).props('width=240').classes('bg-white p-0') as drawer:
        with ui.element('div').classes('px-4 py-3 border-b border-[#E6E1D6]'):
            brand()
        with ui.column().classes('w-full px-2 py-3 gap-1'):
            for section, items in NAV:
                visible = [i for i in items if not i[3] or can(user['role'], i[3])]
                if not visible:
                    continue
                if section:
                    ui.label(section).classes('text-[10px] tracking-[0.18em] text-muted px-3 pt-4 pb-1')
                for item_path, label, icon, _ in visible:
                    _nav_item(item_path, label, icon, item_path == path)
    with ui.header().classes('bg-white text-ink border-b border-[#E6E1D6] px-5 py-2 items-center justify-between'):
        with ui.row().classes('items-center gap-3 no-wrap'):
            ui.button(icon='menu', on_click=drawer.toggle).props('flat round dense color=grey-8 data-testid=menu-toggle')
            with ui.column().classes('gap-0'):
                ui.label(title.upper()).classes('text-[10px] tracking-[0.18em] text-muted')
                ui.label('Capit-in · Sistem Informasi Akuntansi Tambak Kepiting').classes('text-sm')
        with ui.row().classes('items-center gap-3 no-wrap'):
            ui.avatar(user['name'][:1].upper(), color='primary', text_color='white', size='36px')
            with ui.column().classes('gap-0 gt-xs'):
                ui.label(user['name']).classes('text-sm font-medium').props('data-testid=current-user-name')
                ui.label(ROLE_LABELS[user['role']]).classes('text-xs text-muted').props('data-testid=current-user-role')
            ui.button(icon='logout', on_click=logout).props(
                'flat round dense color=grey-8 data-testid=logout-button').tooltip('Keluar')


def protected(path: str, title: str, permission: str | None = None):
    def decorator(builder):
        @ui.page(path, title=f'{title} · Capit-in')
        def page():
            user = current_user()
            if not user:
                return RedirectResponse('/login')
            if permission and not can(user['role'], permission):
                return RedirectResponse('/')
            theme.apply()
            _shell(user, path, title)
            with ui.column().classes('w-full max-w-[1400px] mx-auto px-2 md:px-6 py-6 gap-6'):
                builder(user)
        return page
    return decorator
