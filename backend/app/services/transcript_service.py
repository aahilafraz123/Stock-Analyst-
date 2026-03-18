from earningscall import get_company
import re

def get_latest_earnings_transcript(ticker: str) -> dict:
    """
    Fetch the most recent earnings call transcript for a ticker.
    Returns structured transcript with prepared remarks and Q&A separated.
    """
    try:
        company = get_company(ticker.lower())
        if not company:
            return None

        # Get the most recent event
        events = list(company.events())
        if not events:
            return None

        # Find most recent past event
        latest_event = None
        from datetime import datetime
        for event in events:
            if datetime.now().timestamp() > event.conference_date.timestamp():
                latest_event = event
                break

        if not latest_event:
            return None

        transcript = company.get_transcript(event=latest_event)
        if not transcript or not transcript.text:
            return None

        full_text = transcript.text

        # Clean up the text
        full_text = re.sub(r'\s+', ' ', full_text).strip()

        # Try to split into prepared remarks and Q&A
        qa_markers = [
            "question-and-answer",
            "question and answer",
            "q&a session",
            "open the floor to questions",
            "we will now begin the question",
            "operator: thank you",
            "we'll now open",
            "open for questions",
            "turn it over to questions",
            "first question",
            "our first question",
            "take your first question",
            "open the call to questions",
            "open the lines for questions",
            "begin our q&a",
            "start the q&a",
        ]

        prepared_remarks = full_text
        qa_section = ""

        text_lower = full_text.lower()
        for marker in qa_markers:
            idx = text_lower.find(marker)
            if idx > 1000:  # Make sure we have meaningful prepared remarks
                prepared_remarks = full_text[:idx].strip()
                qa_section = full_text[idx:idx + 8000].strip()
                break

        return {
            "ticker": ticker.upper(),
            "quarter": latest_event.quarter,
            "year": latest_event.year,
            "conferenceDate": str(latest_event.conference_date)[:10],
            "preparedRemarks": prepared_remarks[:10000],
            "qaSection": qa_section[:5000],
            "fullTranscriptLength": len(full_text),
        }

    except Exception as e:
        print(f"[{ticker}] Transcript fetch failed: {e}")
        return None
