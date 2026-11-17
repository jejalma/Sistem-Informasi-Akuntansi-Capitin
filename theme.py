from nicegui import app

PALETTE = {
    'primary': '#0F4C5C',
    'secondary': '#E07A3F',
    'accent': '#2A7F62',
    'positive': '#2A7F62',
    'negative': '#B3412E',
    'warning': '#C98A2B',
    'info': '#0F4C5C',
    'ink': '#1F2A2E',
    'muted': '#6B7578',
    'cream': '#F6F3EC',
    'sand': '#EFE9DC',
    'line': '#E6E1D6',
    'teal_soft': '#E3EEEE',
    'ember_soft': '#FBEADF',
    'moss_soft': '#E4F1EA',
    'rose_soft': '#F7E2DE',
}

HEX = {k: v for k, v in PALETTE.items()}


def apply() -> None:
    app.colors(**PALETTE)
