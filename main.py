from pathlib import Path

from nicegui import app,ui
import config
import database

app.add_static_files('/static', str(Path(__file__).parent / 'static'))
from views.pages import login, dashboard, transactions, journal, reports, master_data, accounts, stock
database.init_db()
ui.button.default_props('no-caps')

if __name__ in {'__main__', '__mp_main__'}:
    import config
from nicegui import ui

# Kode untuk mencetak link otomatis ke terminal sebelum server menyala
print(f"🚀 Aplikasi CAPIT-IN sedang berjalan! Buka di browser: http://localhost:{config.PORT}")

ui.run(
    host='0.0.0.0',
    port=config.PORT,
    title=f'{config.APP_NAME} · SIA Tambak Kepiting',
    storage_secret=config.STORAGE_SECRET,
    language='id',
    show=False,
    reload=False,
    show_welcome_message=False,
    favicon='🦀'
)
