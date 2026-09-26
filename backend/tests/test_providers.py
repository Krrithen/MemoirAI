import json

import httpx
import pytest

from app.providers.llm import EnrichmentFailed, OllamaLLM
from app.providers.transcriber import TranscriptionFailed, _require_text


def ollama_reply(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"message": {"content": content}},
        request=httpx.Request("POST", "http://ollama/api/chat"),
    )


@pytest.fixture
def replies(monkeypatch):
    """Queue of responses returned by successive httpx.post calls."""
    queue: list = []

    def fake_post(url, **kwargs):
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(httpx, "post", fake_post)
    return queue


def llm() -> OllamaLLM:
    return OllamaLLM("http://ollama", "test-model", timeout_s=5)


def enrichment_json(**overrides) -> str:
    data = {"title": "A Day", "story": "It was a good day.", "emotions": ["Joy"]}
    return json.dumps(data | overrides)


def test_story_containing_braces_parses(replies):
    """Regression: the old non-greedy regex broke on '{' inside the story."""
    story = 'She wrote {"not": "json"} on the fridge and we laughed.'
    replies.append(ollama_reply(enrichment_json(story=story)))
    assert llm().enrich("transcript").story == story


def test_invalid_output_is_retried_once(replies):
    replies += [ollama_reply("not json"), ollama_reply(enrichment_json())]
    assert llm().enrich("transcript").title == "A Day"
    assert replies == []


def test_invalid_output_twice_fails(replies):
    replies += [ollama_reply("not json"), ollama_reply("{}")]
    with pytest.raises(EnrichmentFailed):
        llm().enrich("transcript")


def test_emotion_outside_the_list_is_invalid(replies):
    replies += [ollama_reply(enrichment_json(emotions=["Nostalgia"]))] * 2
    with pytest.raises(EnrichmentFailed):
        llm().enrich("transcript")


def test_more_than_three_emotions_is_invalid(replies):
    replies += [ollama_reply(enrichment_json(emotions=["Joy", "Love", "Hope", "Anger"]))] * 2
    with pytest.raises(EnrichmentFailed):
        llm().enrich("transcript")


def test_ollama_unreachable_fails_cleanly(replies):
    replies.append(httpx.ConnectError("connection refused"))
    with pytest.raises(EnrichmentFailed, match="Ollama request failed"):
        llm().enrich("transcript")


@pytest.mark.parametrize("text", ["", "   ", None])
def test_blank_transcript_raises(text):
    with pytest.raises(TranscriptionFailed):
        _require_text(text)
