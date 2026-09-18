import json

from run_backtest import render_results


SAMPLE_RESULTS = {
    "symbol": "AAPL",
    "start": "2024-01-01",
    "end": "2024-04-01",
    "interval": "1d",
    "final_equity": 12345.67,
    "return_pct": 12.34,
    "trades": [
        {"timestamp": "2024-01-02", "side": "LONG", "entry": 100.0, "exit": 105.0, "qty": 10.0, "pnl": 50.0, "reason": "signal_flip"}
    ],
}


def test_render_results_text() -> None:
    rendered = render_results(SAMPLE_RESULTS, "text")
    assert "Final equity" in rendered
    assert "AAPL" in rendered


def test_render_results_json() -> None:
    rendered = render_results(SAMPLE_RESULTS, "json")
    payload = json.loads(rendered)
    assert payload["symbol"] == "AAPL"
    assert payload["final_equity"] == 12345.67


def test_render_results_csv() -> None:
    rendered = render_results(SAMPLE_RESULTS, "csv")
    assert "symbol,final_equity,return_pct" in rendered
    assert "AAPL" in rendered


def test_render_results_html() -> None:
    rendered = render_results(SAMPLE_RESULTS, "html")
    assert "<html" in rendered.lower()
    assert "AAPL" in rendered
