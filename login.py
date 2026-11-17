from fastapi.responses import RedirectResponse
from nicegui import app, ui

import config
from services import ServiceError, auth
from views import theme
from views.layout import brand, current_user

DEMO_ACCOUNTS = [(label, email, password) for (label, email, password, _) in [
    ('Admin (Bapak Salim)', *config.SEED_USERS[0][1:]),
    ('Akuntan', *config.SEED_USERS[1][1:]),
    ('Kasir', *config.SEED_USERS[2][1:]),
]]


def _hero() -> None:
    with ui.column().classes('gt-sm w-1/2 flex min-h-screen bg-primary text-white p-10 justify-between'):
        brand(dark=True)
        with ui.column().classes('gap-3'):
            ui.label('Catat setiap').classes('text-5xl font-semibold leading-tight')
            with ui.row().classes('gap-0 items-baseline'):
                ui.label('panen').classes('text-5xl font-semibold text-secondary leading-tight')
                ui.label(', kelola').classes('text-5xl font-semibold leading-tight')
            ui.label('setiap rupiah.').classes('text-5xl font-semibold leading-tight')
            with ui.row().classes('items-center gap-2 text-white/70 mt-3'):
                ui.icon('waves', size='16px')
                ui.label('Morodemak, Bonang, Demak').classes('text-sm')
        ui.label('v1.0 · SIA-TKS · Tambak Kepiting Bapak Salim').classes('text-xs font-mono text-white/50')


@ui.page('/login', title='Masuk · Capit-in')
def login_page():
    if current_user():
        return RedirectResponse('/')
    theme.apply()
    ui.query('.nicegui-content').classes('p-0')
    ui.query('body').classes('bg-cream')

    def submit() -> None:
        try:
            user = auth.authenticate(email.value, password.value)
        except ServiceError as exc:
            error.set_text(str(exc))
            error.set_visibility(True)
            return
        app.storage.user['uid'] = user['id']
        ui.navigate.to('/')

    def fill(mail: str, pwd: str) -> None:
        email.set_value(mail)
        password.set_value(pwd)

    with ui.row().classes('w-full min-h-screen no-wrap gap-0'):
        _hero()
        with ui.column().classes('w-full lg:w-1/2 min-h-screen items-center justify-center p-6'):
            with ui.column().classes('w-full max-w-[380px] gap-4'):
                with ui.column().classes('gap-1 lt-md mb-4'):
                    brand()
                ui.label('Masuk ke akun Anda').classes('text-3xl font-semibold text-ink tracking-tight')
                ui.label('Gunakan email dan kata sandi dari admin tambak.').classes('text-sm text-muted -mt-3')
                email = ui.input('Email').props('outlined dense data-testid=login-email-input').classes(
                    'w-full bg-white')
                password = ui.input('Kata Sandi', password=True, password_toggle_button=True).props(
                    'outlined dense data-testid=login-password-input').classes('w-full bg-white')
                password.on('keydown.enter', submit)
                error = ui.label('').classes('text-sm text-negative').props('data-testid=login-error')
                error.set_visibility(False)
                ui.button('Masuk', on_click=submit).props(
                    'unelevated color=primary size=md data-testid=login-submit-button').classes('w-full py-2')
                ui.separator().classes('my-2')
                ui.label('AKUN DEMO — KLIK UNTUK ISI OTOMATIS').classes('text-[10px] tracking-[0.15em] text-muted')
                for label, mail, pwd in DEMO_ACCOUNTS:
                    slug = label.split()[0].lower()
                    with ui.row().classes(
                            'w-full items-center justify-between bg-white border border-[#E6E1D6] rounded-lg px-3 py-2 '
                            'cursor-pointer hover:border-[#0F4C5C] no-wrap').on(
                            'click', lambda m=mail, p=pwd: fill(m, p)).props(f'data-testid=demo-account-{slug}'):
                        ui.label(label).classes('text-sm text-ink')
                        ui.label(mail).classes('text-xs font-mono text-muted')
