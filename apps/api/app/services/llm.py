import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

ModelT = TypeVar("ModelT", bound=BaseModel)
logger = logging.getLogger(__name__)


class LlmClient:
    provider = "disabled"

    @property
    def enabled(self) -> bool:
        return False

    def generate_structured(
        self,
        *,
        output_model: type[ModelT],
        system_prompt: str,
        user_prompt: str,
    ) -> ModelT | None:
        logger.debug("LLM disabled; using deterministic fallback.")
        return None


class GeminiLlmClient(LlmClient):
    provider = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_structured(
        self,
        *,
        output_model: type[ModelT],
        system_prompt: str,
        user_prompt: str,
    ) -> ModelT | None:
        if not self.enabled:
            logger.info("Gemini skipped: GEMINI_API_KEY is not configured.")
            return None

        logger.info("Gemini request started: model=%s output_schema=%s", self.model, output_model.__name__)
        schema = output_model.model_json_schema()
        prompt = (
            f"{system_prompt}\n\n"
            "Return only valid JSON matching this Pydantic JSON schema. "
            "Do not wrap the JSON in markdown fences.\n\n"
            f"{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"{user_prompt}"
        )
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(self.model, safe='')}:generateContent"
            f"?key={urllib.parse.quote(self.api_key, safe='')}"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            error_body = _safe_error_body(error)
            logger.warning(
                "Gemini request failed: status=%s reason=%s body=%s",
                error.code,
                error.reason,
                error_body,
            )
            return None
        except urllib.error.URLError as error:
            logger.warning("Gemini request failed: url_error=%s", error.reason)
            return None
        except TimeoutError:
            logger.warning("Gemini request timed out after %s seconds.", settings.llm_timeout_seconds)
            return None
        except json.JSONDecodeError as error:
            logger.warning("Gemini response was not valid JSON: %s", error)
            return None

        text = _extract_gemini_text(data)
        if not text:
            logger.warning("Gemini response contained no text candidates.")
            return None

        try:
            generated = output_model.model_validate_json(_clean_json_text(text))
            logger.info("Gemini structured response validated: schema=%s", output_model.__name__)
            return generated
        except ValidationError as error:
            logger.warning(
                "Gemini structured response failed validation: schema=%s errors=%s raw_preview=%s",
                output_model.__name__,
                error.errors(),
                _preview(text),
            )
            return None


def get_llm_client() -> LlmClient:
    if settings.llm_provider.lower() == "gemini":
        return GeminiLlmClient(settings.gemini_api_key, settings.gemini_model)
    return LlmClient()


def _extract_gemini_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    texts = [str(part.get("text", "")) for part in parts if part.get("text")]
    return "\n".join(texts).strip()


def _clean_json_text(value: str) -> str:
    text = value.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _safe_error_body(error: urllib.error.HTTPError) -> str:
    try:
        return _preview(error.read().decode("utf-8", errors="replace"))
    except Exception:
        return ""


def _preview(value: str, limit: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."
