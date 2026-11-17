import pytest

import database
from services import ServiceError, accounts, master, reports, stock, transactions as tx


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    database.set_db_path(str(tmp_path / 'test.db'))
    database.init_db(seed_users=[('Admin', 'a@test.id', 'secret1', 'admin')])


def _key(key):
    return next(a for a in accounts.list_accounts() if a['system_key'] == key)


def _first_product():
    return master.list_products()[0]


def test_opening_status_detects_imbalance():
    kas, modal = _key('kas'), _key('modal')
    accounts.set_opening_balances({kas['id']: 1_000_000, modal['id']: 900_000})
    status = accounts.opening_status(accounts.list_accounts())
    assert not status['balanced'] and status['diff'] == 100_000
    accounts.set_opening_balances({modal['id']: 1_000_000})
    assert accounts.opening_status(accounts.list_accounts())['balanced']


def test_sale_rejected_when_stock_insufficient():
    product = _first_product()
    collector = master.list_collectors()[0]
    with pytest.raises(ServiceError, match='Stok'):
        tx.record('PENJUALAN', {'date': '2026-06-01', 'collector_id': collector['id'], 'product_id': product['id'],
                                'qty': 2, 'unit_price': 110000, 'payment': 'kas'}, None)


def test_sale_creates_balanced_journal_and_reduces_stock():
    product = _first_product()
    collector = master.list_collectors()[0]
    stock.add_movement(product['id'], '2026-06-01', 'PANEN', 10, '', None)
    result = tx.record('PENJUALAN', {'date': '2026-06-02', 'collector_id': collector['id'],
                                     'product_id': product['id'], 'qty': 4, 'unit_price': 110000,
                                     'payment': 'piutang'}, None)
    assert result['amount'] == 440000
    assert master.list_products()[0]['stock_kg'] == 6
    assert reports.trial_balance(None)['balanced']
    assert master.list_collectors()[0]['receivable'] == 440000
    with pytest.raises(ServiceError):
        tx.record('PENERIMAAN_PIUTANG', {'date': '2026-06-03', 'collector_id': collector['id'], 'amount': 500000,
                                         'payment': 'kas'}, None)


def test_reports_balance_after_mixed_transactions():
    kas, modal = _key('kas'), _key('modal')
    accounts.set_opening_balances({kas['id']: 5_000_000, modal['id']: 5_000_000})
    employee = master.list_employees()[0]
    tx.record('PAKAN', {'date': '2026-06-02', 'qty': 5, 'unit_price': 10000, 'payment': 'kas'}, None)
    tx.record('GAJI', {'date': '2026-06-02', 'employee_id': employee['id'], 'qty': 2, 'payment': 'kas'}, None)
    income = reports.income_statement('2026-06-01', '2026-06-30')
    assert income['total_expense'] == 50000 + 240000
    sheet = reports.balance_sheet(None)
    assert sheet['balanced'] and sheet['total_assets'] == 5_000_000 - 290000
    flow = reports.cash_flow('2026-06-01', '2026-06-30')
    assert flow['opening'] == 5_000_000 and flow['net'] == -290000


def test_core_and_used_accounts_are_protected():
    kas = _key('kas')
    with pytest.raises(ServiceError):
        accounts.delete_account(kas['id'])
    with pytest.raises(ServiceError):
        accounts.update_account(kas['id'], {**kas, 'code': '1-1999'})
    new_id = accounts.create_account({'code': '5-7000', 'name': 'Beban Transport', 'category': 'BEBAN'})
    accounts.delete_account(new_id)
    with pytest.raises(ServiceError):
        accounts.create_account({'code': '1-7000', 'name': 'Salah', 'category': 'BEBAN'})
