"""Ollama integration for patch note summarization."""

import os
import logging
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


@dataclass
class PatchSummary:
    """Summarized patch notes."""
    summary: str
    features: list[str]


def ensure_model_available() -> bool:
    """Check if the model is available, pull if not."""
    try:
        # Check if model exists
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]

            if OLLAMA_MODEL.split(":")[0] in model_names:
                logger.info(f"Model {OLLAMA_MODEL} is available")
                return True

        # Model not found, pull it
        logger.info(f"Pulling model {OLLAMA_MODEL}...")
        response = requests.post(
            f"{OLLAMA_HOST}/api/pull",
            json={"name": OLLAMA_MODEL},
            timeout=600,  # 10 minute timeout for large models
            stream=True
        )

        # Stream the response to show progress
        for line in response.iter_lines():
            if line:
                logger.debug(f"Pull progress: {line.decode()}")

        logger.info(f"Model {OLLAMA_MODEL} pulled successfully")
        return True

    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}")
        return False
    except Exception as e:
        logger.error(f"Error ensuring model availability: {e}")
        return False


def summarize_patch(title: str, content: str) -> PatchSummary:
    """Summarize patch notes using Ollama."""
    if not content:
        return PatchSummary(
            summary="No content available for this patch.",
            features=[]
        )

    prompt = f"""Analyze the following Star Citizen patch notes and provide:
1. A brief 1-2 sentence summary of what this patch is about
2. A list of NEW FEATURES only (not bug fixes, not improvements to existing features)

Patch Title: {title}

Patch Content:
{content[:6000]}

Respond in this exact format:
SUMMARY: [Your 1-2 sentence summary here]

FEATURES:
- [Feature 1]
- [Feature 2]
- [Feature 3]

If there are no new features, write "FEATURES: None"
"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 500
                }
            },
            timeout=120
        )

        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.status_code}")
            return PatchSummary(
                summary=f"Patch: {title}",
                features=[]
            )

        result = response.json().get("response", "")
        return parse_llm_response(result, title)

    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}")
        return PatchSummary(
            summary=f"Patch: {title} (summarization unavailable)",
            features=[]
        )
    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        return PatchSummary(
            summary=f"Patch: {title}",
            features=[]
        )


def parse_llm_response(response: str, fallback_title: str) -> PatchSummary:
    """Parse the LLM response into structured data."""
    summary = fallback_title
    features = []

    lines = response.strip().split("\n")

    # Parse summary
    for line in lines:
        if line.upper().startswith("SUMMARY:"):
            summary = line[8:].strip()
            break

    # Parse features
    in_features = False
    for line in lines:
        if "FEATURES:" in line.upper():
            in_features = True
            # Check if features are on the same line
            after_colon = line.split(":", 1)[-1].strip()
            if after_colon.lower() not in ["none", ""]:
                if after_colon.startswith("-"):
                    features.append(after_colon[1:].strip())
            continue

        if in_features:
            line = line.strip()
            if line.startswith("-"):
                feature = line[1:].strip()
                if feature and feature.lower() != "none":
                    features.append(feature)
            elif line.startswith("*"):
                feature = line[1:].strip()
                if feature and feature.lower() != "none":
                    features.append(feature)

    return PatchSummary(summary=summary, features=features)


def wait_for_ollama(max_retries: int = 30, retry_delay: int = 10) -> bool:
    """Wait for Ollama to become available."""
    import time

    for i in range(max_retries):
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("Ollama is available")
                return True
        except requests.exceptions.ConnectionError:
            pass

        logger.info(f"Waiting for Ollama... ({i + 1}/{max_retries})")
        time.sleep(retry_delay)

    logger.error("Ollama did not become available")
    return False
