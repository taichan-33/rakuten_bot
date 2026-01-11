"""
DBManagerのテスト
"""

import pytest
import tempfile
import os
from app.core.db_manager import DBManager
from app.models.order_status import OrderStatus


@pytest.fixture
def db():
    """テスト用DBを作成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield DBManager(db_path)


def test_creates_table():
    """テーブルを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DBManager(db_path)
        assert os.path.exists(db_path)


def test_updates_order_status(db):
    """注文ステータスを更新する"""
    db.update_order("test_123", OrderStatus.DONE.value, "receipt.pdf")
    assert db.get_order_status("test_123") == OrderStatus.DONE.value


def test_returns_none_for_unknown_order(db):
    """不明な注文でNoneを返す"""
    assert db.get_order_status("nonexistent") is None


def test_should_process_new_order(db):
    """新規注文は処理対象"""
    assert db.should_process("new_order") is True


def test_should_not_process_done_order(db):
    """DONE注文は処理対象外"""
    db.update_order("done_order", OrderStatus.DONE.value)
    assert db.should_process("done_order") is False


def test_should_process_retry_order(db):
    """RETRY注文は処理対象"""
    db.update_order("retry_order", OrderStatus.RETRY.value)
    assert db.should_process("retry_order") is True


def test_increments_retry_count(db):
    """リトライカウントを増加する"""
    db.update_order("order_1", OrderStatus.RETRY.value, increment_retry=True)
    assert db.get_retry_count("order_1") == 1

    db.update_order("order_1", OrderStatus.RETRY.value, increment_retry=True)
    assert db.get_retry_count("order_1") == 2


def test_get_summary(db):
    """サマリーを取得する"""
    db.update_order("o1", OrderStatus.DONE.value)
    db.update_order("o2", OrderStatus.DONE.value)
    db.update_order("o3", OrderStatus.NO_RECEIPT.value)

    summary = db.get_summary()
    assert summary.get(OrderStatus.DONE.value) == 2
    assert summary.get(OrderStatus.NO_RECEIPT.value) == 1


def test_export_report(db):
    """レポートをエクスポートする"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db.update_order("o1", OrderStatus.DONE.value)

        csv_path = os.path.join(tmpdir, "report.csv")
        db.export_report(csv_path)

        assert os.path.exists(csv_path)
