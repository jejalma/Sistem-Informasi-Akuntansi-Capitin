from datetime import date

_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']


def _id_sep(text: str) -> str:
    return text.replace(',', '_').replace('.', ',').replace('_', '.')


def rp(value: float | None) -> str:
    value = value or 0.0
    body = _id_sep(f'{abs(value):,.0f}')
    return f'-Rp {body}' if value < -0.005 else f'Rp {body}'


def rp_or_dash(value: float | None) -> str:
    return rp(value) if value and abs(value) >= 0.005 else '-'


def kg(value: float | None) -> str:
    text = f'{value or 0:,.2f}'.rstrip('0').rstrip('.')
    return f'{_id_sep(text)} kg'


def tgl(iso: str | None) -> str:
    if not iso:
        return '-'
    d = date.fromisoformat(iso[:10])
    return f'{d.day:02d} {_MONTHS[d.month - 1]} {d.year}'
