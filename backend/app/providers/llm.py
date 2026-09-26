import logging
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

Emotion = Literal["Joy", "Love", "Gratitude", "Hope", "Contentment", "Surprise", "Curiosity", "Anger"]


class Enrichment(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    story: str = Field(min_length=1)
    emotions: list[Emotion] = Field(max_length=3)


SYSTEM_PROMPT = """You lightly edit a spoken transcript of a personal memory into clean written text.
The speaker's own account is the only source of truth.

Story rules:
- Keep the speaker's words and first-person voice. Fix grammar, and remove filler words
  (um, uh, like, you know), false starts and repetition.
- Keep every fact the speaker said: names, places, dates, numbers, events.
- Never add anything the speaker did not say: no sensory details, feelings, thoughts,
  actions, objects, people, places, dialogue, or reflections on what the moment meant.
- The story should be about as long as the transcript, or shorter. Do not expand it.

Title: a few words, using only facts from the transcript.
Emotions: up to three that the speaker expressed, only from:
  Joy, Love, Gratitude, Hope, Contentment, Surprise, Curiosity, Anger.

Respond with JSON only: {"title": ..., "story": ..., "emotions": [...]}"""


class EnrichmentFailed(Exception):
    """Raised when the model can't produce a valid {title, story, emotions}."""


class LLM(Protocol):
    def enrich(self, transcript: str) -> Enrichment: ...


def _with_one_retry(generate) -> Enrichment:
    """Call generate() and validate; retry once on invalid output, then give up."""
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            return Enrichment.model_validate_json(generate())
        except ValidationError as e:
            last_error = e
            logger.warning("Invalid enrichment output (attempt %d): %s", attempt, e)
    raise EnrichmentFailed(f"Model returned invalid output twice: {last_error}")


class OllamaLLM:
    """Local model via Ollama, with the output constrained to Enrichment's JSON schema."""

    def __init__(self, base_url: str, model: str, timeout_s: float, temperature: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.temperature = temperature

    def enrich(self, transcript: str) -> Enrichment:
        def generate() -> str:
            try:
                resp = httpx.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": transcript},
                        ],
                        "format": Enrichment.model_json_schema(),
                        "stream": False,
                        "think": False,
                        "options": {"temperature": self.temperature},
                    },
                    timeout=self.timeout_s,
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise EnrichmentFailed(f"Ollama request failed: {e}") from e
            return resp.json()["message"]["content"]

        return _with_one_retry(generate)


class GeminiLLM:
    """Hosted model, opt-in with LLM=gemini."""

    def __init__(self, api_key: str, model: str, temperature: float):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._types = genai.types
        self.model = model
        self.temperature = temperature

    def enrich(self, transcript: str) -> Enrichment:
        def generate() -> str:
            try:
                resp = self._client.models.generate_content(
                    model=self.model,
                    contents=transcript,
                    config=self._types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_json_schema=Enrichment.model_json_schema(),
                        temperature=self.temperature,
                    ),
                )
            except Exception as e:
                raise EnrichmentFailed(f"Gemini request failed: {e}") from e
            return resp.text or ""

        return _with_one_retry(generate)
