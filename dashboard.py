from datetime import date

from nicegui import ui

from services import master, reports
from services.transactions import TYPES, list_transactions
from views.components import badge, card, data_table, kpi, page_header, section_title
from views.fmt import kg, rp, tgl
from views.layout import protected

TYPE_TONES = {'PENJUALAN': 'moss', 'PENERIMAAN_PIUTANG': 'moss', 'MODAL': 'teal', 'PAKAN': 'ember', 'GAJI': 'ember',
              'OPERASIONAL': 'ember', 'PRIVE': 'rose'}


def type_badge(tx_type: str) -> None:
    badge(TYPES[tx_type][0], TYPE_TONES[tx_type])


def _opening_warning(status: dict) -> None:
    if status['balanced']:
        return
    with ui.row().classes('w-full items-center gap-3 rounded-xl border border-[#C98A2B] bg-ember-soft px-4 py-3 no-wrap') \
            .props('data-testid=dashboard-opening-warning'):
        ui.icon('warning_amber', size='20px').classes('text-warning')
        ui.label(f'Saldo awal Bagan Akun belum seimbang (selisih {rp(status["diff"])}). '
                 'Neraca tidak akan seimbang sampai saldo awal debit = kredit.').classes('text-sm text-ink')
        ui.space()
        ui.link('Periksa Bagan Akun', '/akun').classes('text-sm text-primary font-medium whitespace-nowrap')


def _chart(series: list[dict]) -> None:
    ui.echart({
        'tooltip': {'trigger': 'axis'},
        'legend': {'bottom': 0, 'data': ['Pendapatan', 'Beban']},
        'grid': {'left': 60, 'right': 16, 'top': 30, 'bottom': 48},
        'xAxis': {'type': 'category', 'data': [s['label'] for s in series],
                  'axisLine': {'lineStyle': {'color': '#9aa3a5'}}},
        'yAxis': {'type': 'value', 'name': 'ribu Rp', 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#E6E1D6'}}},
        'series': [
            {'name': 'Pendapatan', 'type': 'bar', 'barMaxWidth': 26, 'itemStyle': {'color': '#0F4C5C',
                                                                                  'borderRadius': [4, 4, 0, 0]},
             'data': [round(s['revenue'] / 1000) for s in series]},
            {'name': 'Beban', 'type': 'line', 'smooth': True, 'symbolSize': 7, 'itemStyle': {'color': '#E07A3F'},
             'data': [round(s['expense'] / 1000) for s in series]},
        ],
    }).classes('w-full h-72').props('data-testid=dashboard-chart')


def _entities() -> None:
    counts = master.entity_counts()
    items = [('groups', 'Pengepul Terdaftar', counts['collectors'], 'collectors'),
             ('badge', 'Karyawan Aktif', counts['employees'], 'employees'),
             ('set_meal', 'Produk Kepiting', counts['products'], 'products'),
             ('receipt_long', 'Total Transaksi', counts['transactions'], 'transactions')]
    for icon, label, value, key in items:
        with ui.row().classes('w-full items-center gap-3 rounded-lg bg-cream px-4 py-3 no-wrap'):
            ui.icon(icon, size='18px').classes('text-primary')
            ui.label(label).classes('text-sm text-ink')
            ui.space()
            ui.label(str(value)).classes('font-mono text-ink').props(f'data-testid=entity-count-{key}')


@protected('/', 'Dashboard')
def dashboard_page(user: dict) -> None:
    data = reports.dashboard(date.today())
    page_header('Ringkasan Keuangan', f'Periode: {tgl(data["start"])} — {tgl(data["end"])}')
    _opening_warning(data['opening'])
    with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4'):
        kpi('Pendapatan', rp(data['revenue']), 'Penjualan kepiting bulan ini', 'trending_up', 'moss', 'kpi-revenue')
        kpi('Beban', rp(data['expense']), 'Pakan, gaji, operasional', 'trending_down', 'ember', 'kpi-expense')
        kpi('Laba Bersih', rp(data['net_income']), f'Margin {data["margin"]:.1f}%', 'account_balance_wallet',
            'teal' if data['net_income'] >= 0 else 'rose', 'kpi-net-income')
        kpi('Saldo Kas & Bank', rp(data['cash']), f'Piutang {rp(data["receivable"])}', 'savings', 'teal', 'kpi-cash')
        kpi('Nilai Stok', rp(data['stock_value']), f'{kg(data["stock_kg"])} total', 'inventory_2', 'sand',
            'kpi-stock')
    with ui.grid().classes('w-full grid-cols-1 xl:grid-cols-3 gap-4'):
        with card('xl:col-span-2'):
            section_title('Pendapatan vs Beban (6 Bulan)', 'Pergerakan arus bulanan, dalam ribuan rupiah')
            _chart(data['series'])
        with card():
            section_title('Ringkasan Entitas')
            _entities()
    with card():
        section_title('Transaksi Terbaru')
        rows = [[tgl(t['date']), t['ref_no'], lambda t=t: type_badge(t['type']), t['description'], rp(t['amount'])]
                for t in list_transactions(limit=8)]
        data_table([('Tanggal', 'left'), ('No. Ref', 'left'), ('Jenis', 'left'), ('Keterangan', 'left'),
                    ('Nilai', 'right')], rows, 'Belum ada transaksi. Mulai dari menu Transaksi.', 'recent-transactions')
