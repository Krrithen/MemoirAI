from functools import lru_cache

from app.config import get_settings
from app.providers.llm import LLM, GeminiLLM, OllamaLLM
from app.providers.transcriber import AssemblyAITranscriber, FasterWhisperTranscriber, Transcriber


@lru_cache
def get_transcriber() -> Transcriber:
    s = get_settings()
    if s.transcriber == "assemblyai":
        if not s.assemblyai_api_key:
            raise RuntimeError("TRANSCRIBER=assemblyai needs ASSEMBLYAI_API_KEY")
        return AssemblyAITranscriber(s.assemblyai_api_key)
    return FasterWhisperTranscriber(s.whisper_model, s.whisper_compute_type)


@lru_cache
def get_llm() -> LLM:
    s = get_settings()
    if s.llm == "gemini":
        if not s.gemini_api_key:
            raise RuntimeError("LLM=gemini needs GEMINI_API_KEY")
        return GeminiLLM(s.gemini_api_key, s.gemini_model, s.llm_temperature)
    return OllamaLLM(s.ollama_url, s.ollama_model, s.llm_timeout_s, s.llm_temperature)
