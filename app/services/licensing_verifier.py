import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.schemas import LicenseStatus, LicensingEvidence
from app.services.gemini_verifier import gemini_verifier

logger = logging.getLogger(__name__)


async def verify_licensing(
    source_name: str,
    source_url: str,
    title: str,
    published_year: Optional[int],
    raw_rights: Optional[str] = None,
    terms_url: Optional[str] = None,
    google_books_access_info: Optional[Dict[str, Any]] = None,
    open_library_details: Optional[Dict[str, Any]] = None
) -> LicensingEvidence:
    """
    Independently verify licensing evidence for a candidate book.
    NEVER relies on identity confidence score.
    Returns one of three states:
      - VERIFIED_FOR_PERMITTED_DOWNLOAD
      - NEEDS_REVIEW
      - NOT_ELIGIBLE
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    evidence_details: List[str] = []

    # Case 1: Project Gutenberg
    if "gutenberg" in source_name.lower():
        evidence_details.append("Source is Project Gutenberg: items in main catalog are validated public domain in the USA.")
        evidence_details.append("License terms confirm unrestricted educational and personal use.")
        return LicensingEvidence(
            status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
            license_name="Public Domain (Project Gutenberg Catalog)",
            rights_statement=raw_rights or "Public domain in the USA.",
            source_url=source_url,
            terms_url=terms_url or "https://www.gutenberg.org/policy/license.html",
            evidence_details=evidence_details,
            verified_at=now_iso,
            intended_use="educational_reference_acquisition",
            is_legally_downloadable=True
        )

    # Case 2: Open Access Monograph / Textbook (DOAB / OSTEP / Creative Commons)
    if raw_rights and any(cc in raw_rights.lower() for cc in ["cc-by", "creative commons", "cc0", "open access"]):
        evidence_details.append(f"Explicit open licensing declared in repository: '{raw_rights}'.")
        evidence_details.append("Creative Commons / Open Access terms grant authorization for educational downloading.")
        return LicensingEvidence(
            status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
            license_name=raw_rights,
            rights_statement=raw_rights,
            source_url=source_url,
            terms_url=terms_url or source_url,
            evidence_details=evidence_details,
            verified_at=now_iso,
            intended_use="educational_reference_acquisition",
            is_legally_downloadable=True
        )

    # Case 3: Google Books Access Info
    if google_books_access_info:
        public_domain = google_books_access_info.get("publicDomain", False)
        access_view_status = google_books_access_info.get("accessViewStatus", "")
        viewability = google_books_access_info.get("viewability", "")

        if public_domain and access_view_status in ("FULL_PUBLIC_DOMAIN", "FULL_PURCHASED"):
            evidence_details.append("Google Books AccessInfo reports item as fully verified Public Domain.")
            return LicensingEvidence(
                status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
                license_name="Public Domain (Google Books Full Access)",
                rights_statement="Google Books confirmed public domain volume.",
                source_url=source_url,
                terms_url="https://books.google.com/intl/en/googlebooks/about/terms.html",
                evidence_details=evidence_details,
                verified_at=now_iso,
                intended_use="educational_reference_acquisition",
                is_legally_downloadable=True
            )
        elif viewability in ("PARTIAL", "NO_PAGES") or not public_domain:
            evidence_details.append(f"Google Books reports accessViewStatus='{access_view_status}', viewability='{viewability}'.")
            evidence_details.append("Protected by commercial copyright. Paywall/commercial purchase required.")
            evidence_details.append("Mandatory safeguard: Anti-piracy rule strictly blocks acquisition.")
            return LicensingEvidence(
                status=LicenseStatus.NOT_ELIGIBLE,
                license_name="Commercial Copyright (In-Print / Retail)",
                rights_statement="All rights reserved. Restricted preview or commercial purchase required.",
                source_url=source_url,
                terms_url="https://books.google.com/intl/en/googlebooks/about/terms.html",
                evidence_details=evidence_details,
                verified_at=now_iso,
                intended_use="educational_reference_acquisition",
                is_legally_downloadable=False
            )

    # Case 4: Open Library Controlled Digital Lending (CDL)
    if open_library_details:
        lending_id = open_library_details.get("lending_identifier_s")
        ia_col = open_library_details.get("ia_collection_s", "")

        if lending_id or "inlibrary" in ia_col.lower() or "printdisabled" in ia_col.lower():
            evidence_details.append("Open Library records this volume under Controlled Digital Lending (in-library loan).")
            evidence_details.append("Borrowing loans allow controlled temporary viewing; permanent file downloading is strictly prohibited.")
            return LicensingEvidence(
                status=LicenseStatus.NOT_ELIGIBLE,
                license_name="Controlled Digital Lending (Borrow-Only)",
                rights_statement="Controlled digital lending loan. No permanent file download permitted.",
                source_url=source_url,
                terms_url="https://openlibrary.org/help/faq/borrow",
                evidence_details=evidence_details,
                verified_at=now_iso,
                intended_use="educational_reference_acquisition",
                is_legally_downloadable=False
            )

    # Case 5: Statutory US Pre-1929 Publication Rule
    if published_year and published_year < 1929:
        evidence_details.append(f"Publication year is {published_year} (< 1929 statutory US copyright threshold).")
        evidence_details.append("Work has formally entered the public domain in the United States.")
        return LicensingEvidence(
            status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
            license_name="Public Domain (Pre-1929 Publication)",
            rights_statement="Published prior to 1929; copyright expired in the United States.",
            source_url=source_url,
            terms_url="https://www.copyright.gov/title17/",
            evidence_details=evidence_details,
            verified_at=now_iso,
            intended_use="educational_reference_acquisition",
            is_legally_downloadable=True
        )

    # Case 6: Ambiguous / Raw Rights Text Present
    if raw_rights and raw_rights.strip():
        gemini_result = await gemini_verifier.verify_rights_statement(
            title=title,
            published_year=published_year,
            rights_text=raw_rights,
            source_name=source_name
        )
        is_dl = gemini_result.get("is_legally_downloadable", False)
        status_raw = gemini_result.get("status", "unknown_unverified")

        if is_dl and status_raw in ("public_domain", "open_access"):
            mapped_status = LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD
        elif status_raw in ("commercial_copyrighted", "borrowable_controlled"):
            mapped_status = LicenseStatus.NOT_ELIGIBLE
        else:
            mapped_status = LicenseStatus.NEEDS_REVIEW

        evidence_details.append(gemini_result.get("rationale", "Evaluated via rights statement analysis."))

        return LicensingEvidence(
            status=mapped_status,
            license_name=gemini_result.get("license_name", "Analyzed Licensing Rights"),
            rights_statement=raw_rights,
            source_url=source_url,
            terms_url=terms_url or source_url,
            evidence_details=evidence_details,
            verified_at=now_iso,
            intended_use="educational_reference_acquisition",
            is_legally_downloadable=is_dl
        )

    # Default fallback: Unclear / Missing licensing evidence -> NEEDS_REVIEW
    evidence_details.append("No explicit public domain or open access declaration discovered.")
    evidence_details.append("Mandatory safeguard: Ambiguous licensing requires manual review; downloading is blocked.")
    return LicensingEvidence(
        status=LicenseStatus.NEEDS_REVIEW,
        license_name="Unverified / Ambiguous Rights",
        rights_statement="Rights statement absent or unverified.",
        source_url=source_url,
        terms_url=None,
        evidence_details=evidence_details,
        verified_at=now_iso,
        intended_use="educational_reference_acquisition",
        is_legally_downloadable=False
    )
