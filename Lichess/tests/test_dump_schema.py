import pandas as pd

from src.dump import normalize_games_columns


def test_normalize_games_columns_handles_uppercase_headers() -> None:
    df = pd.DataFrame({
        "White": ["alice"],
        "Black": ["bob"],
        "Result": ["1-0"],
        "UTCDate": ["2016.01.01"],
        "UTCTime": ["00:00:00"],
        "WhiteElo": ["1600"],
        "BlackElo": ["1500"],
        "WhiteRatingDiff": ["10"],
        "BlackRatingDiff": ["-10"],
        "TimeControl": ["300+0"],
        "Termination": ["Normal"],
        "ECO": ["?"],
        "Opening": ["?"],
        "NumMoves": ["10"],
    })

    out = normalize_games_columns(df)

    assert "white" in out.columns
    assert "black" in out.columns
    assert "whiteelo" in out.columns
    assert "blackelo" in out.columns
    assert "nummoves" in out.columns
    assert out["whiteelo"].tolist() == ["1600"]
