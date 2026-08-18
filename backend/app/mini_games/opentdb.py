import html
import logging
import random

import httpx

logger = logging.getLogger(__name__)

OPENTDB_BASE_URL = "https://opentdb.com"
OPENTDB_ATTRIBUTION = "Trivia questions courtesy of Open Trivia DB (opentdb.com), CC BY-SA 4.0."


class OpenTdbRequestError(Exception):
    """opentdb.com call failed (transport error or non-2xx/non-success
    response code). Callers should treat the sync as a no-op, not raise -
    the trivia bank keeps serving whatever it already has cached."""


async def fetch_opentdb_questions(amount: int = 50) -> list[tuple[str, list[str], str]]:
    """Fetches `amount` multiple-choice questions from opentdb.com in a
    single request. Returns (question_text, shuffled_options, correct_option)
    tuples with HTML entities decoded. Intended to be called from an
    unscheduled sync/maintenance path (see sync_trivia_from_opentdb), never
    per-round from live call traffic - opentdb asks for roughly one request
    per 5s per IP (tasks/mini-games.md), and this fetches a batch to cache
    server-side instead."""
    try:
        async with httpx.AsyncClient(base_url=OPENTDB_BASE_URL, timeout=10) as client:
            response = await client.get("/api.php", params={"amount": amount, "type": "multiple"})
    except httpx.HTTPError as exc:
        raise OpenTdbRequestError(f"opentdb request failed: {exc}") from exc

    if response.is_error:
        raise OpenTdbRequestError(f"opentdb request failed: {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise OpenTdbRequestError(f"opentdb returned malformed JSON: {exc}") from exc

    if data.get("response_code") != 0:
        raise OpenTdbRequestError(f"opentdb returned response_code={data.get('response_code')}")

    questions: list[tuple[str, list[str], str]] = []
    for item in data.get("results", []):
        question = html.unescape(item["question"])
        correct = html.unescape(item["correct_answer"])
        incorrect = [html.unescape(a) for a in item["incorrect_answers"]]
        options = [correct, *incorrect]
        random.shuffle(options)
        questions.append((question, options, correct))

    return questions
