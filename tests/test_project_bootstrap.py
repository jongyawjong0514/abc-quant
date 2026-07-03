from abc_quant import __version__
from abc_quant.data.validation import required_market_columns


def test_version_exists() -> None:
    assert isinstance(__version__, str)


def test_required_market_columns() -> None:
    cols = required_market_columns()
    assert {"date", "ticker", "open", "high", "low", "close", "volume"}.issubset(cols)
