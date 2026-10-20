from datetime import datetime
from decimal import Decimal

import pandas as pd
import pytest

from app.calculation import Calculation
from app.exceptions import OperationError, ValidationError
from app.history import CSV_COLUMNS, HistoryStore

TS = datetime(2026, 1, 2, 3, 4, 5)
HEADER = ",".join(CSV_COLUMNS)


def calc(op="add", a="1", b="2", result="3"):
    return Calculation(op, Decimal(a), Decimal(b), Decimal(result), TS)


@pytest.fixture
def store(tmp_path):
    return HistoryStore(tmp_path / "history" / "h.csv")


# ---- saving ----
def test_save_writes_expected_columns_and_rows(store):
    store.save([calc(), calc("multiply", "2", "3", "6")])
    frame = pd.read_csv(store.path, dtype=str)
    assert list(frame.columns) == CSV_COLUMNS
    assert len(frame) == 2
    assert frame.loc[1, "operation"] == "multiply"


def test_save_creates_missing_directory(store):
    assert not store.path.parent.exists()
    store.save([calc()])
    assert store.path.exists()


def test_save_empty_history_writes_header_only(store):
    store.save([])
    assert store.path.read_text(encoding="utf-8").strip() == HEADER


def test_save_overwrites_previous_content(store):
    store.save([calc(), calc()])
    store.save([calc()])
    assert len(store.load()) == 1


def test_save_leaves_no_temp_file(store):
    store.save([calc()])
    assert [p.name for p in store.path.parent.iterdir()] == ["h.csv"]


def test_save_failure_raises_operation_error(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(OperationError, match="Could not save"):
        HistoryStore(blocker / "sub" / "h.csv").save([calc()])


# ---- loading ----
def test_round_trip_preserves_values_exactly(store):
    original = [calc(), calc("divide", "1", "3", "0.3333333333"), calc("subtract", "-2", "0.50", "-2.5")]
    store.save(original)
    loaded = store.load()
    assert loaded == tuple(original)
    assert str(loaded[2].operand_b) == "0.50"  # no float conversion


def test_load_header_only_file_returns_empty(store):
    store.save([])
    assert store.load() == ()


def test_load_missing_file(store):
    with pytest.raises(OperationError, match="not found"):
        store.load()


def test_load_directory_instead_of_file(tmp_path):
    with pytest.raises(OperationError, match="Could not read"):
        HistoryStore(tmp_path).load()


def test_load_zero_byte_file(tmp_path):
    path = tmp_path / "h.csv"
    path.write_text("")
    with pytest.raises(ValidationError, match="empty"):
        HistoryStore(path).load()


def test_load_undecodable_file(tmp_path):
    path = tmp_path / "h.csv"
    path.write_bytes(b"\xff\xfe\xfa\xfb")
    with pytest.raises(ValidationError, match="malformed"):
        HistoryStore(path).load()


def test_load_row_with_extra_fields(tmp_path):
    path = tmp_path / "h.csv"
    path.write_text(f"{HEADER}\nadd,1,2,3,2026-01-02T03:04:05\nadd,1,2,3,2026-01-02T03:04:05,x,y\n")
    with pytest.raises(ValidationError, match="malformed"):
        HistoryStore(path).load()


def test_load_missing_columns(tmp_path):
    path = tmp_path / "h.csv"
    path.write_text("operation,result\nadd,3\n")
    with pytest.raises(ValidationError, match="missing columns: operand_a, operand_b, timestamp"):
        HistoryStore(path).load()


@pytest.mark.parametrize("row", [
    "add,abc,2,3,2026-01-02T03:04:05",     # bad number
    "add,NaN,2,3,2026-01-02T03:04:05",     # non-finite number
    "add,1,2,3,yesterday",                 # bad timestamp
    "add,1",                               # short row
])
def test_load_reports_the_bad_row(tmp_path, row):
    path = tmp_path / "h.csv"
    path.write_text(f"{HEADER}\nadd,1,2,3,2026-01-02T03:04:05\n{row}\n")
    with pytest.raises(ValidationError, match="Row 3"):
        HistoryStore(path).load()


def test_load_ignores_extra_columns(tmp_path):
    path = tmp_path / "h.csv"
    path.write_text(f"{HEADER},note\nadd,1,2,3,2026-01-02T03:04:05,hello\n")
    assert len(HistoryStore(path).load()) == 1