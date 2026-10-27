from app.services.edgar import extract_sections, html_to_text


def test_html_to_text_keeps_line_structure_and_drops_markup(fixture_text):
    text = html_to_text(fixture_text("example_10k.html"))
    assert "color:red" not in text
    assert "\nItem 1A. Risk Factors\n" in text
    assert "  " not in text  # whitespace collapsed


def test_10k_sections_skip_table_of_contents(fixture_text):
    sections = extract_sections(html_to_text(fixture_text("example_10k.html")), "10-K")
    assert set(sections) == {"business", "risk_factors", "mda", "market_risk"}
    # The TOC entry ("Risk Factors\n9") must lose to the real section body.
    assert "single supplier" in sections["risk_factors"]
    assert "Unresolved Staff Comments" not in sections["risk_factors"]
    assert "Total revenue increased 12%" in sections["mda"]
    assert "repurchased $300 million" in sections["mda"]
    assert sections["market_risk"].startswith("Item 7A.")


def test_10q_mda_is_part_one_item_two_not_part_two(fixture_text):
    sections = extract_sections(html_to_text(fixture_text("example_10q.html")), "10-Q")
    assert "Software subscriptions grew 28%" in sections["mda"]
    assert "Unregistered Sales" not in sections["mda"]
    assert "tariffs on imported sensors" in sections["risk_factors"]


def test_heading_needs_matching_title_words():
    body = "x " * 300
    text = f"Item 7. Exhibits and Other Things\n{body}\nItem 8. Financial Statements\nend"
    assert "mda" not in extract_sections(text, "10-K")
