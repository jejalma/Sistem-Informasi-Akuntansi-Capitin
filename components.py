from typing import Callable

from nicegui import ui

from services import ServiceError
from services.pdf import table_pdf

TONES = {
    'teal': 'bg-teal-soft text-primary',
    'ember': 'bg-ember-soft text-secondary',
    'moss': 'bg-moss-soft text-accent',
    'rose': 'bg-rose-soft text-negative',
    'sand': 'bg-sand text-ink',
}
INPUT_PROPS = 'outlined dense'


def run_safely(action: Callable, success: str | None = None, after: Callable | None = None) -> bool:
    try:
        action()
    except ServiceError as exc:
        ui.notify(str(exc), type='negative', position='top')
        return False
    if success:
        ui.notify(success, type='positive', position='top')
    if after:
        after()
    return True


def page_header(title: str, subtitle: str | None = None) -> ui.row:
    with ui.row().classes('w-full items-end justify-between gap-4'):
        with ui.column().classes('gap-1'):
            ui.label(title).classes('text-3xl font-light text-ink tracking-tight').props('data-testid=page-title')
            if subtitle:
                ui.label(subtitle).classes('text-sm text-muted')
        actions = ui.row().classes('gap-2 items-center')
    return actions


def card(extra: str = '') -> ui.card:
    return ui.card().props('flat bordered').classes(f'w-full p-5 rounded-xl bg-white border-[#E6E1D6] gap-3 {extra}')


def section_title(title: str, hint: str | None = None) -> None:
    with ui.column().classes('gap-0'):
        ui.label(title).classes('text-base font-medium text-ink')
        if hint:
            ui.label(hint).classes('text-xs text-muted')


def badge(text: str, tone: str = 'teal') -> ui.label:
    return ui.label(text).classes(f'px-2 py-0.5 rounded text-[11px] font-medium inline-block {TONES[tone]}')


def report_block(*, title: str, subtitle: str, headers: list[tuple[str, str]], rows: list[tuple[list, str]],
            widths: list[float], filename: str, testid: str, orientation: str = 'P') -> None:
    def download():
        pdf = table_pdf(title, subtitle, [h for h, _ in headers], rows, widths,
                        ''.join({'left': 'L', 'right': 'R', 'center': 'C'}[a] for _, a in headers), orientation)
        ui.download.content(pdf, filename, 'application/pdf')

    with ui.row().classes('w-full items-center justify-between'):
        section_title(title, subtitle)
        ui.button('Unduh PDF', icon='print', on_click=download).props(
            f'outline color=primary dense data-testid={testid}-pdf-button').classes('px-3')


def confirm(message: str, on_confirm: Callable, label: str = 'Ya, hapus') -> None:
    with ui.dialog() as dialog, ui.card().classes('p-6 w-96 gap-3'):
        ui.label('Konfirmasi').classes('text-lg font-medium text-ink')
        ui.label(message).classes('text-sm text-muted')
        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button('Batal', on_click=dialog.close).props('flat color=grey-8 data-testid=confirm-cancel-button')
            ui.button(label, on_click=lambda: (dialog.close(), on_confirm())).props(
                'unelevated color=negative data-testid=confirm-yes-button')
    dialog.open()


def field(spec: dict, values: dict, on_change: Callable | None = None):
    key, label, kind = spec['key'], spec['label'], spec.get('kind', 'text')

    def changed(e):
        values[key] = e.value
        if on_change:
            on_change()

    current = values.get(key)
    if kind == 'number':
        el = ui.number(label, value=current, min=spec.get('min', 0), format=spec.get('format'), on_change=changed)
    elif kind == 'select':
        el = ui.select(spec['options'], label=label, value=current, on_change=changed)
    elif kind == 'switch':
        el = ui.switch(label, value=bool(current), on_change=changed)
    elif kind == 'date':
        el = ui.date_input(label, value=current or '', on_change=changed)
    elif kind == 'password':
        el = ui.input(label, password=True, password_toggle_button=True, on_change=changed)
    else:
        el = ui.input(label, value=current or '', on_change=changed)
    if kind != 'switch':
        el.props(INPUT_PROPS)
    el.props(f'data-testid=field-{key}').classes('w-full')
    if spec.get('hint'):
        el.props(f'hint="{spec["hint"]}"')
    if spec.get('disabled'):
        el.disable()
    return el


def form_dialog(title: str, fields: list[dict], initial: dict, on_submit: Callable[[dict], None],
                live: Callable[[dict], None] | None = None) -> None:
    values = dict(initial)
    with ui.dialog().props('persistent') as dialog, ui.card().classes('p-6 w-[500px] max-w-full gap-3'):
        ui.label(title).classes('text-lg font-medium text-ink').props('data-testid=form-dialog-title')
        live_area = ui.refreshable(lambda: live(values)) if live else None
        for spec in fields:
            field(spec, values, live_area.refresh if live_area else None)
        if live_area:
            live_area()
        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button('Batal', on_click=dialog.close).props('flat color=grey-8 data-testid=form-cancel-button')
            ui.button('Simpan', icon='check',
                      on_click=lambda: run_safely(lambda: on_submit(values), 'Data berhasil disimpan.',
                                                  dialog.close)).props(
                'unelevated color=primary data-testid=form-submit-button')
    dialog.open()


def icon_button(icon: str, tooltip: str, on_click: Callable, testid: str, color: str = 'grey-8') -> None:
    ui.button(icon=icon, on_click=on_click).props(f'flat round dense color={color} size=sm data-testid={testid}') \
        .tooltip(tooltip)



def kpi(title: str, value: str | int | float, hint: str | None = None,
        icon: str | None = None, tone: str = 'teal', test_id: str | None = None) -> None:
    """
    Komponen KPI Card / Kotak Statistik untuk Dashboard.

    :param title: Judul indikator (misal: "Pendapatan")
    :param value: Nilai utama KPI (misal: "Rp 5.000.000")
    :param hint: Keterangan tambahan di bawah nilai
    :param icon: Nama ikon Material (misal: "trending_up")
    :param tone: Tema warna (teal, ember, moss, rose, sand)
    :param test_id: ID untuk atribut data-testid (opsional, untuk pengujian)
    """
    with card().classes('flex-1 min-w-[200px]'):
        if test_id:
            ui.element('span').props(f'data-testid={test_id}').classes('hidden')
        with ui.row().classes('w-full items-center justify-between'):
            ui.label(title).classes('text-xs font-medium text-muted uppercase tracking-wider')
            if icon:
                ui.icon(icon).classes('text-lg')
            else:
                badge(tone.capitalize(), tone=tone)
        with ui.column().classes('gap-1 mt-1'):
            ui.label(str(value)).classes('text-2xl font-semibold text-ink tracking-tight')
            if hint:
                ui.label(hint).classes('text-xs text-muted')

def data_table(headers: list[tuple[str, str]], rows: list[list],
               empty_text: str = 'Tidak ada data tersedia.', testid: str = 'table') -> None:
    num_cols = len(headers)
    text_align = {'left': 'text-left', 'right': 'text-right', 'center': 'text-center'}
    justify = {'left': 'justify-start', 'right': 'justify-end', 'center': 'justify-center'}

    with ui.card().classes('w-full p-0 rounded-xl border border-[#E6E1D6] overflow-hidden bg-white') \
            .props(f'flat bordered data-testid={testid}'):

        # Header tabel
        with ui.grid(columns=num_cols).classes(
                'w-full gap-0 bg-[#F9F8F6] border-b border-[#E6E1D6] px-4 py-3 items-center'):
            for header_name, align in headers:
                ui.label(header_name).classes(
                    f'text-xs font-semibold text-muted uppercase tracking-wider {text_align.get(align, "text-left")}')

        # Body tabel
        with ui.column().classes('w-full gap-0'):
            if not rows:
                with ui.row().classes('w-full px-4 py-6 justify-center'):
                    ui.label(empty_text).classes('text-sm text-muted italic')
            else:
                for i, row in enumerate(rows):
                    if i:
                        ui.separator()
                    with ui.grid(columns=num_cols).classes(
                            'w-full gap-0 px-4 py-3 items-center hover:bg-[#FAFAF9] transition-colors'):
                        for idx, cell in enumerate(row):
                            align = headers[idx][1] if idx < num_cols else 'left'
                            if callable(cell):
                                # sel berupa fungsi (badge, tombol aksi): jalankan
                                with ui.row().classes(f'w-full items-center gap-1 no-wrap {justify.get(align, "justify-start")}'):
                                    cell()
                            else:
                                ui.label(str(cell)).classes(f'text-sm text-ink {text_align.get(align, "text-left")}')