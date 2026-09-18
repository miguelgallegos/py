from multi_strategy_bot import optimize_strategy


def test_optimize_strategy_respects_explicit_threshold_overrides():
    strategy = {
        "buy_threshold": -0.1,
        "sell_threshold": 0.2,
        "ladder": (0.35, 0.75, 1.0),
        "buy_candidates": [-0.03, -0.025, -0.02, -0.0175, -0.015, -0.0125, -0.01],
        "sell_candidates": [0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055],
    }

    results = optimize_strategy(
        "FNGU",
        "5m",
        "2026-08-16",
        "2026-09-18",
        5000.0,
        strategy,
    )

    assert results
    assert {result["buy_threshold"] for result in results} == {-0.1}
    assert {result["sell_threshold"] for result in results} == {0.2}
