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


_OUTPUT_RULES = """Title: a few words that capture the memory.
Emotions: up to three that are present in the memory, only from:
  Joy, Love, Gratitude, Hope, Contentment, Surprise, Curiosity, Anger.

Respond with JSON only: {"title": ..., "story": ..., "emotions": [...]}"""

# STORY_STYLE=creative (default): a vivid retelling that may add atmosphere.
CREATIVE_PROMPT = f"""You turn a spoken transcript of a personal memory into a warm, vivid written story.

Story rules:
- Always rewrite. Never return the transcript as it is, even if it already reads well.
- Write in the first person, in the speaker's voice: a short story of two or three paragraphs,
  roughly two to three times the length of the transcript, with an opening that sets the scene
  and an ending that lands the moment.
- Add atmosphere and sensory detail to bring the moment to life.
- Keep every fact the speaker said, and never change them: names, places, dates,
  numbers, who was there and what happened.

{_OUTPUT_RULES}"""

# STORY_STYLE=faithful: a light edit that adds nothing (see eval/faithfulness).
FAITHFUL_PROMPT = f"""You lightly edit a spoken transcript of a personal memory into clean written text.
The speaker's own account is the only source of truth.

Story rules:
- Keep the speaker's words and first-person voice. Fix grammar, and remove filler words
  (um, uh, like, you know), false starts and repetition.
- Keep every fact the speaker said: names, places, dates, numbers, events.
- Never add anything the speaker did not say: no sensory details, feelings, thoughts,
  actions, objects, people, places, dialogue, or reflections on what the moment meant.
- The story should be about as long as the transcript, or shorter. Do not expand it.
- The title must use only facts from the transcript, and emotions only ones the speaker expressed.

{_OUTPUT_RULES}"""

PROMPTS = {"creative": CREATIVE_PROMPT, "faithful": FAITHFUL_PROMPT}
DEFAULT_TEMPERATURE = {"creative": 0.7, "faithful": 0.0}


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

    def __init__(self, base_url: str, model: str, timeout_s: float, temperature: float, system_prompt: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.system_prompt = system_prompt

    def enrich(self, transcript: str) -> Enrichment:
        def generate() -> str:
            try:
                resp = httpx.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
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

    def __init__(self, api_key: str, model: str, temperature: float, system_prompt: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._types = genai.types
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt

    def enrich(self, transcript: str) -> Enrichment:
        def generate() -> str:
            try:
                resp = self._client.models.generate_content(
                    model=self.model,
                    contents=transcript,
                    config=self._types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        response_mime_type="application/json",
                        response_json_schema=Enrichment.model_json_schema(),
                        temperature=self.temperature,
                    ),
                )
            except Exception as e:
                raise EnrichmentFailed(f"Gemini request failed: {e}") from e
            return resp.text or ""

        return _with_one_retry(generate)
