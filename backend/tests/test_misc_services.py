import pandas as pd

from app.rag.diff import quote_found
from app.services.insider import classify_transaction
from app.services.institutional import major_holders_summary
from app.services.market_data import num, pct_change
from app.services.transcripts import split_prepared_and_qa


def test_major_holders_labels_live_in_the_index():
    # Shape yfinance returns: labels as index, single "Value" column (the old code read a non-existent column).
    df = pd.DataFrame(
        {"Value": [0.021, 0.613, 6012]}, index=["insidersPercentHeld", "institutionsPercentHeld", "institutionsCount"]
    )
    df.columns.name = "Breakdown"
    summary = major_holders_summary(df)
    assert summary == {"insidersPercentHeld": 0.021, "institutionsPercentHeld": 0.613, "institutionsCount": 6012}


def test_num_handles_nan_and_inf():
    assert num(float("nan")) is None
    assert num(float("inf")) is None
    assert num("3.14159", 2) == 3.14
    assert num(None) is None
    assert pct_change(110, 100) == 10.0
    assert pct_change(110, 0) is None


def test_insider_classification():
    assert classify_transaction("Sale at price 190.00 per share.") == "SELL"
    assert classify_transaction("Purchase at price 10.00") == "BUY"
    assert classify_transaction("Stock Award(Grant) at price 0.00") == "AWARD"
    assert classify_transaction("Stock Gift") == "GIFT"


def test_transcript_split_finds_qa():
    prepared = "Thank you operator. " * 80
    text = prepared + "Operator: We will now begin the question-and-answer session. First question..."
    remarks, qa = split_prepared_and_qa(text)
    assert remarks.startswith("Thank you operator.") and "question" not in remarks.lower()
    assert qa.startswith("Operator: We will now begin the question-and-answer session")


def test_transcript_split_without_markers_keeps_everything():
    remarks, qa = split_prepared_and_qa("short call with no questions")
    assert remarks == "short call with no questions" and qa == ""


def test_quote_verification_tolerates_whitespace_case_and_ellipses():
    filing = "Supply chain disruptions could delay\nwidget production because several critical components are sourced."
    assert quote_found("supply chain disruptions could delay widget production", filing)
    assert quote_found("Supply chain disruptions … critical components are sourced", filing)
    assert not quote_found("Supply chain disruptions could halt all production", filing)
    assert not quote_found("too short", filing)
