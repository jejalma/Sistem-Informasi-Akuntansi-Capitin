from typing import Callable

from nicegui import ui

from security import can
from views.components import card, confirm, data_table, form_dialog, icon_button, page_header, run_safely


def crud_page(user: dict, *, title: str, subtitle: str, entity: str, slug: str, fields: Callable[[dict | None], list],
              defaults: dict, load: Callable[[], list], save: Callable[[dict, int | None], int],
              remove: Callable[[int], None], headers: list[tuple[str, str]], to_cells: Callable[[dict], list],
              create_perm: str = 'master.create', edit_perm: str = 'master.edit', delete_perm: str = 'delete') -> None:
    role = user['role']
    allow_create, allow_edit, allow_delete = can(role, create_perm), can(role, edit_perm), can(role, delete_perm)
    actions = page_header(title, subtitle)

    def open_form(record: dict | None = None) -> None:
        form_dialog(f'{"Ubah" if record else "Tambah"} {entity}', fields(record), record or defaults,
                    lambda values: (save(values, record['id'] if record else None), table.refresh()))

    def ask_delete(record: dict) -> None:
        confirm(f'Hapus {entity.lower()} "{record["name"]}"? Tindakan ini tidak dapat dibatalkan.',
                lambda: run_safely(lambda: remove(record['id']), f'{entity} dihapus.', table.refresh))

    def row_actions(record: dict) -> None:
        with ui.row().classes('gap-1 justify-end no-wrap'):
            if allow_edit:
                icon_button('edit', 'Ubah', lambda r=record: open_form(r), f'{slug}-edit-{record["id"]}')
            if allow_delete:
                icon_button('delete_outline', 'Hapus', lambda r=record: ask_delete(r), f'{slug}-delete-{record["id"]}',
                            'negative')

    with actions:
        if allow_create:
            ui.button('Tambah', icon='add', on_click=lambda: open_form()).props(
                f'unelevated color=primary data-testid={slug}-add-button')

    @ui.refreshable
    def table() -> None:
        has_actions = allow_edit or allow_delete
        cols = headers + ([('Aksi', 'right')] if has_actions else [])
        rows = [to_cells(r) + ([lambda r=r: row_actions(r)] if has_actions else []) for r in load()]
        data_table(cols, rows, testid=f'{slug}-table')

    with card():
        table()
