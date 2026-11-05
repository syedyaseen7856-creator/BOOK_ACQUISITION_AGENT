import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiRightsVerifier:
    """
    Analyzes ambiguous book copyright statements and license declarations
    using Google Gemini Flash API.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}. Falling back to rule-based.")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def verify_rights_statement(
        self,
        title: str,
        published_year: Optional[int],
        rights_text: str,
        source_name: str
    ) -> Dict[str, Any]:
        """
        Use Gemini Flash to classify ambiguous rights statements.
        Returns a structured dictionary with status, license_name, is_downloadable, and rationale.
        """
        if not self.is_available:
            return self._heuristic_fallback(rights_text, published_year)

        prompt = f"""
You are a copyright and digital rights compliance specialist for an educational book acquisition system.
Analyze the following book rights metadata and determine if the work is legally authorized for unrestricted downloading.

Book Title: {title}
Publication Year: {published_year or 'Unknown'}
Source Repository: {source_name}
Raw Rights/License Text: "{rights_text}"

Legal Rules:
1. Only Public Domain (e.g. published before 1929 in the US, or explicit CC0/Public Domain) and Open Access (CC-BY, CC-BY-SA) may be marked as downloadable.
2. In-copyright commercial books, library loan/Controlled Digital Lending (CDL), and restricted preview items MUST NEVER be marked as downloadable.
3. If rights are ambiguous, missing, or unverified, mark as 'unknown_unverified' and set is_legally_downloadable to false.

Respond ONLY with valid JSON in this exact structure:
{{
  "status": "public_domain" | "open_access" | "borrowable_controlled" | "commercial_copyrighted" | "unknown_unverified",
  "license_name": "<Short clean license name>",
  "is_legally_downloadable": true | false,
  "confidence": 0.0 to 1.0,
  "rationale": "<Concise explanation of legal reasoning>"
}}
"""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            raw_text = response.text.strip()
            # Clean markdown code blocks if present
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`").replace("json\n", "", 1)
            result = json.loads(raw_text)
            return {
                "status": result.get("status", "unknown_unverified"),
                "license_name": result.get("license_name", "Unverified License"),
                "is_legally_downloadable": bool(result.get("is_legally_downloadable", False)),
                "rationale": result.get("rationale", "Verified by Gemini Flash rights analysis."),
                "verification_method": "gemini_flash_llm"
            }
        except Exception as e:
            logger.warning(f"Gemini verification failed ({e}), using heuristic fallback.")
            return self._heuristic_fallback(rights_text, published_year)

    def _heuristic_fallback(self, rights_text: str, published_year: Optional[int]) -> Dict[str, Any]:
        """Safe deterministic fallback if Gemini Flash is offline or not configured."""
        text_lower = (rights_text or "").lower()

        if "public domain" in text_lower or (published_year and published_year < 1929):
            return {
                "status": "public_domain",
                "license_name": "Public Domain (Pre-1929 / Declared)",
                "is_legally_downloadable": True,
                "rationale": "Verified as public domain based on publication date (<1929) or explicit statement.",
                "verification_method": "rule_based_fallback"
            }

        if any(cc in text_lower for cc in ["cc-by", "creative commons", "open access", "cc0"]):
            return {
                "status": "open_access",
                "license_name": "Creative Commons / Open Access",
                "is_legally_downloadable": True,
                "rationale": "Explicit Creative Commons or Open Access license detected.",
                "verification_method": "rule_based_fallback"
            }

        if any(term in text_lower for term in ["borrow", "lending", "controlled digital lending", "loan"]):
            return {
                "status": "borrowable_controlled",
                "license_name": "Controlled Digital Lending (Borrow Only)",
                "is_legally_downloadable": False,
                "rationale": "Controlled digital lending library book. Not authorized for unrestricted file download.",
                "verification_method": "rule_based_fallback"
            }

        if any(term in text_lower for term in ["all rights reserved", "copyright", "in print", "commercial", "retail"]):
            return {
                "status": "commercial_copyrighted",
                "license_name": "Commercial Copyright (All Rights Reserved)",
                "is_legally_downloadable": False,
                "rationale": "Standard commercial copyright. Local file download is strictly unauthorized.",
                "verification_method": "rule_based_fallback"
            }

        return {
            "status": "unknown_unverified",
            "license_name": "Unverified Rights",
            "is_legally_downloadable": False,
            "rationale": "Insufficient licensing metadata. Download disallowed by safeguard policy.",
            "verification_method": "rule_based_fallback"
        }


gemini_verifier = GeminiRightsVerifier()
