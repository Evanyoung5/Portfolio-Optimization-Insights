from pathlib import Path

import pytest

from app.connectors.broker_csv import BrokerCSVError, parse_brokerage_csv


FIXTURES = Path(__file__).parent / "fixtures" / "broker_csv"


@pytest.mark.parametrize(
    ("filename", "source", "symbols"),
    [
        ("fidelity_positions.csv", "fidelity", ["AAPL", "BND"]),
        ("etrade_positions.csv", "etrade", ["BRK_B", "MSFT"]),
        ("schwab_positions.csv", "schwab", ["SCHB", "SCHZ"]),
        ("coinbase_transactions.csv", "coinbase", ["BTC-USD", "ETH-USD"]),
    ],
)
def test_parses_sanitized_brokerage_exports(filename, source, symbols):
    result = parse_brokerage_csv((FIXTURES / filename).read_text())

    assert result.source == source
    assert [position.symbol for position in result.positions] == symbols
    assert all(position.quantity > 0 for position in result.positions)
    assert all(position.price > 0 for position in result.positions)
    assert all(position.cost_basis > 0 for position in result.positions)


def test_fidelity_import_preserves_cost_basis_and_market_price():
    result = parse_brokerage_csv((FIXTURES / "fidelity_positions.csv").read_text())
    apple = next(position for position in result.positions if position.symbol == "AAPL")

    assert apple.quantity == 10
    assert apple.price == 210.25
    assert apple.cost_basis == 1500
    assert apple.average_cost == 150
    assert apple.unrealized_gain_loss == 602.50


def test_coinbase_import_reconstructs_net_quantity_and_basis():
    result = parse_brokerage_csv((FIXTURES / "coinbase_transactions.csv").read_text())
    bitcoin = next(position for position in result.positions if position.symbol == "BTC-USD")
    ethereum = next(position for position in result.positions if position.symbol == "ETH-USD")

    assert bitcoin.quantity == pytest.approx(0.075)
    assert bitcoin.cost_basis == pytest.approx(3015)
    assert bitcoin.price == 50_000
    assert ethereum.quantity == pytest.approx(2.1)
    assert ethereum.cost_basis == pytest.approx(4310)


def test_duplicate_symbols_are_aggregated_across_accounts():
    result = parse_brokerage_csv(
        "symbol,quantity,current value,cost basis total\n"
        "AAPL,2,$400,$300\n"
        "AAPL,3,$630,$480\n"
    )

    assert len(result.positions) == 1
    assert result.positions[0].quantity == 5
    assert result.positions[0].price == 206
    assert result.positions[0].cost_basis == 780


def test_rejects_unknown_csv_shape():
    with pytest.raises(BrokerCSVError, match="No supported brokerage header"):
        parse_brokerage_csv("name,favorite color\nSample,green\n")
