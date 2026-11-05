import json
import logging
import re
from typing import Optional, Dict, Any, List
from app.config import settings
from app.schemas import BookSearchQuery

logger = logging.getLogger(__name__)


class GeminiService:
    """
    LLM assistance using Google Gemini Flash API.
    Responsibilities:
      - Interpret book requests & extract structured metadata
      - Normalize titles, author names, and edition details
      - Generate comparison explanations between candidates
    Authoritative confidence scoring, licensing certification, and approval gates
    remain strictly deterministic in Python.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize google-genai client: {e}")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def parse_unstructured_query(self, text: str) -> BookSearchQuery:
        """
        Parse raw syllabus reading list text or natural language prompt
        into structured BookSearchQuery fields.
        """
        if not self.is_available:
            return self._heuristic_parse(text)

        prompt = f"""
You are a bibliographic citation parser for an academic syllabus processing system.
Extract structured bibliographic fields from the following text:

"{text}"

Return ONLY a valid JSON object matching this schema:
{{
  "title": "<Extracted Title or null>",
  "author": "<Primary Author Name or null>",
  "isbn": "<Extracted ISBN-10 or 13 or null>",
  "edition": "<Edition string or null>",
  "year": <Integer 4-digit publication year or null>,
  "subject": "<Subject area or null>"
}}
"""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n", "", raw).rstrip("`").strip()
            data = json.loads(raw)
            return BookSearchQuery(
                title=data.get("title"),
                author=data.get("author"),
                isbn=data.get("isbn"),
                edition=data.get("edition"),
                year=data.get("year"),
                subject=data.get("subject"),
                use_mock_data=False
            )
        except Exception as e:
            logger.warning(f"Gemini query parsing failed ({e}), using heuristic parser.")
            return self._heuristic_parse(text)

    def _heuristic_parse(self, text: str) -> BookSearchQuery:
        """Deterministic fallback when Gemini is offline."""
        isbn_match = re.search(r"\b(?:ISBN(?:-1[03])?:?\s*)?(?=[0-9X]{10}|(?=(?:[0-9]+[-\s]){3})[-0-9X]{13}|97[89][0-9]{10}|(?=(?:[0-9]+[-\s]){4})[-0-9]{17})([0-9]{1,5}[-\s]?[0-9]+[-\s]?[0-9]+[-\s]?[0-9X]+)\b", text, re.I)
        isbn = isbn_match.group(1).replace("-", "").replace(" ", "") if isbn_match else None

        year_match = re.search(r"\b(19\d\d|20\d\d)\b", text)
        year = int(year_match.group(1)) if year_match else None

        edition_match = re.search(r"\b(\d+(?:st|nd|rd|th)\s+ed(?:ition)?)\b", text, re.I)
        edition = edition_match.group(1) if edition_match else None

        # Clean text
        clean_text = text
        if isbn_match:
            clean_text = clean_text.replace(isbn_match.group(0), "")
        if year_match:
            clean_text = clean_text.replace(year_match.group(0), "")

        parts = [p.strip() for p in clean_text.split(" by ") if p.strip()]
        if len(parts) == 2:
            title, author = parts[0], parts[1]
        else:
            title, author = clean_text.strip(), None

        return BookSearchQuery(
            title=title or None,
            author=author or None,
            isbn=isbn,
            edition=edition,
            year=year
        )


gemini_service = GeminiService()
