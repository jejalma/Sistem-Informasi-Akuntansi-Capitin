from datetime import date
from typing import Callable

from nicegui import ui

from services.reports import month_range
from views.components import INPUT_PROPS
from views.fmt import tgl


class Period:
    """Filter periode (dari–sampai) dengan tombol cepat."""

    def __init__(self, on_change: Callable[[], None], testid: str = 'period'):
        self.start, self.end = month_range(date.today())
        self.on_change, self.testid = on_change, testid

    @property
    def label(self) -> str:
        if not self.start and not self.end:
            return 'Semua periode'
        return f'Periode {tgl(self.start) if self.start else "awal"} s.d. {tgl(self.end) if self.end else "sekarang"}'

    @property
    def end_label(self) -> str:
        return f'Per {tgl(self.end)}' if self.end else 'Per hari ini'

    def _set(self, start: str | None, end: str | None) -> None:
        self.start, self.end = start or None, end or None
        self.start_input.value, self.end_input.value = start or '', end or ''

    def _changed(self) -> None:
        self.start = self.start_input.value or None
        self.end = self.end_input.value or None
        self.on_change()

    def render(self) -> None:
        today = date.today()
        with ui.row().classes('items-center gap-2 no-wrap'):
            self.start_input = ui.date_input('Dari', value=self.start or '').props(
                f'{INPUT_PROPS} data-testid={self.testid}-start').classes('w-40 bg-white')
            self.end_input = ui.date_input('Sampai', value=self.end or '').props(
                f'{INPUT_PROPS} data-testid={self.testid}-end').classes('w-40 bg-white')
            self.start_input.on_value_change(lambda _: self._changed())
            self.end_input.on_value_change(lambda _: self._changed())
            with ui.button_group().props('flat'):
                ui.button('Bulan ini', on_click=lambda: self._set(*month_range(today))).props(
                    f'flat dense color=primary no-caps data-testid={self.testid}-month')
                ui.button('Tahun ini', on_click=lambda: self._set(f'{today.year}-01-01', f'{today.year}-12-31')).props(
                    f'flat dense color=primary no-caps data-testid={self.testid}-year')
                ui.button('Semua', on_click=lambda: self._set(None, None)).props(
                    f'flat dense color=primary no-caps data-testid={self.testid}-all')
