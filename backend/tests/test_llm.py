import asyncio
import json
from types import SimpleNamespace

import pytest

from app import llm
from app.errors import LLMError
from app.schemas import AnalysisReport, RiskFactorDiff


def _walk_objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for v in node.values():
            yield from _walk_objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_objects(v)


@pytest.mark.parametrize("model", [AnalysisReport, RiskFactorDiff])
def test_strict_schema_is_closed_and_inlined(model):
    schema = llm.strict_schema(model)
    text = json.dumps(schema)
    assert "$ref" not in text and "$defs" not in text
    objects = list(_walk_objects(schema))
    assert objects
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


def test_strict_schema_keeps_fields_named_title():
    schema = llm.strict_schema(RiskFactorDiff)
    change = schema["properties"]["added"]["items"]
    assert "title" in change["properties"]  # a field called "title", not the schema keyword
    assert schema["properties"]["summary"]["description"]


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def _response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        model="claude-test",
        usage=SimpleNamespace(input_tokens=100, output_tokens=20, cache_read_input_tokens=0),
    )


def _install(monkeypatch, response):
    messages = FakeMessages(response)
    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(messages=messages))
    return messages


def test_structured_parses_and_sends_schema(monkeypatch):
    payload = {"summary": "s", "added": [], "removed": [], "escalated": [], "deemphasized": []}
    messages = _install(monkeypatch, _response(json.dumps(payload)))
    parsed, usage = asyncio.run(llm.structured("sys", "prompt", RiskFactorDiff))
    assert parsed.summary == "s"
    assert usage["inputTokens"] == 100 and usage["model"] == "claude-test"
    fmt = messages.kwargs["output_config"]["format"]
    assert fmt["type"] == "json_schema" and fmt["schema"]["type"] == "object"
    assert messages.kwargs["output_config"]["effort"]
    assert "tool_choice" not in messages.kwargs  # forced tool use is not allowed on current models


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_structured_rejects_refusal_and_truncation(monkeypatch, stop_reason):
    _install(monkeypatch, _response("{}", stop_reason=stop_reason))
    with pytest.raises(LLMError):
        asyncio.run(llm.structured("sys", "prompt", RiskFactorDiff))


def test_structured_rejects_schema_mismatch(monkeypatch):
    _install(monkeypatch, _response('{"summary": 1}'))
    with pytest.raises(LLMError):
        asyncio.run(llm.structured("sys", "prompt", RiskFactorDiff))
