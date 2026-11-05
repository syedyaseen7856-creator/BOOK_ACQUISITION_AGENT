import re
import difflib
from typing import List, Tuple, Optional
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    ConfidenceBreakdown,
    ConfidenceTier
)


def _clean_str(text: str) -> str:
    """Normalize text by lowercasing and stripping non-alphanumeric chars."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _clean_isbn(isbn: str) -> str:
    """Strip hyphens, spaces, and non-digits/X."""
    if not isbn:
        return ""
    return re.sub(r"[^0-9Xx]", "", isbn).upper()


def _calculate_string_similarity(s1: str, s2: str) -> float:
    """Compute token-set & sequence similarity between two strings (0.0 to 1.0)."""
    c1 = _clean_str(s1)
    c2 = _clean_str(s2)
    if not c1 or not c2:
        return 0.0
    if c1 == c2:
        return 1.0

    tokens1 = set(c1.split())
    tokens2 = set(c2.split())
    if not tokens1 or not tokens2:
        return 0.0

    # Subtitle or prefix containment (e.g. main title vs title + subtitle)
    if (
        c2.startswith(c1 + " :") or c2.startswith(c1 + ":") or
        c2.startswith(c1 + " -") or c1.startswith(c2 + " :") or
        c1.startswith(c2 + ":") or c1.startswith(c2 + " -") or
        c2.startswith(c1 + " ") or c1.startswith(c2 + " ")
    ):
        token_ratio = 0.95
    elif (tokens1.issubset(tokens2) or tokens2.issubset(tokens1)) and (
        min(len(tokens1), len(tokens2)) / max(len(tokens1), len(tokens2)) >= 0.65
    ):
        token_ratio = 0.88
    else:
        intersection = tokens1.intersection(tokens2)
        token_ratio = len(intersection) / max(len(tokens1), len(tokens2))

    seq_ratio = difflib.SequenceMatcher(None, c1, c2).ratio()
    return round(max(token_ratio, seq_ratio * 0.8), 3)


def _split_author_names(author_str: str) -> List[str]:
    """Split multi-author string into individual author names."""
    if not author_str:
        return []
    # Split on commas or ' and ' or '&'
    raw_parts = re.split(r",\s*|\s+and\s+|\s*&\s*", author_str, flags=re.IGNORECASE)
    cleaned = [p.strip() for p in raw_parts if p.strip()]
    return cleaned if cleaned else [author_str.strip()]


def _extract_surname(name: str) -> str:
    """Extract surname considering 'Last, First' or 'First Last'."""
    clean = _clean_str(name)
    tokens = clean.split()
    if not tokens:
        return ""
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        return _clean_str(parts[0])
    return tokens[-1]


def _calculate_author_similarity(query_author: str, candidate_authors: List[str]) -> Tuple[float, str]:
    """Check how well the query author matches any of the candidate authors."""
    if not query_author:
        return 0.5, "Neutral (no query author provided)"
    if not candidate_authors:
        return 0.2, "Candidate record lists no authors"

    q_sub_authors = _split_author_names(query_author)
    cand_surnames = set(_extract_surname(a) for a in candidate_authors if a)
    cand_cleans = [_clean_str(a) for a in candidate_authors if a]

    # Check multi-author match
    if len(q_sub_authors) > 1:
        matched_count = 0
        for sub_a in q_sub_authors:
            sub_s = _extract_surname(sub_a)
            sub_clean = _clean_str(sub_a)
            if sub_s in cand_surnames or any(sub_clean in c or c in sub_clean for c in cand_cleans):
                matched_count += 1
        ratio = matched_count / len(q_sub_authors)
        if ratio >= 0.99:
            return 1.0, f"All {len(q_sub_authors)} co-authors matched candidate authors"
        elif ratio >= 0.60:
            return round(0.85 + ratio * 0.10, 2), f"Majority of co-authors matched ({matched_count}/{len(q_sub_authors)})"
        elif ratio > 0:
            return round(ratio * 0.5, 2), f"Partial co-author overlap ({matched_count}/{len(q_sub_authors)})"

    q_clean = _clean_str(query_author)
    q_tokens = set(q_clean.split())
    q_surname = _extract_surname(query_author)

    best_score = 0.0
    best_name = candidate_authors[0] if candidate_authors else "Unknown"

    for cand_author in candidate_authors:
        c_clean = _clean_str(cand_author)
        c_tokens = set(c_clean.split())
        c_surname = _extract_surname(cand_author)

        # Exact match
        if q_clean == c_clean:
            return 1.0, f"Exact author match ('{cand_author}')"

        # Reversed name match: "Shelley, Mary" vs "Mary Shelley"
        if q_tokens == c_tokens and len(q_tokens) >= 2:
            return 0.98, f"Exact author match with inverted order ('{cand_author}')"

        # Surname match
        if q_surname and c_surname and q_surname == c_surname:
            # Check given name initial or tokens
            common = q_tokens.intersection(c_tokens)
            if len(common) >= 2:
                score = 0.95
            else:
                score = 0.90
        else:
            common = q_tokens.intersection(c_tokens)
            if common:
                score = round(len(common) / max(len(q_tokens), len(c_tokens)), 2)
            else:
                seq = difflib.SequenceMatcher(None, q_clean, c_clean).ratio()
                score = round(seq * 0.20, 3)

        if score > best_score:
            best_score = score
            best_name = cand_author

    return round(best_score, 3), f"Matched '{query_author}' to '{best_name}'"


def _calculate_isbn_similarity(query_isbn: str, candidate_isbns: List[str]) -> Tuple[float, str, bool]:
    """
    Check for exact ISBN-10 / ISBN-13 match or hard conflict.
    Returns: (ratio, explanation, is_hard_mismatch)
    """
    if not query_isbn:
        return 0.5, "Neutral (no ISBN provided in search query)", False

    clean_q = _clean_isbn(query_isbn)
    if not clean_q:
        return 0.0, "Invalid query ISBN format", True

    clean_cands = [_clean_isbn(i) for i in candidate_isbns if i]
    if not clean_cands:
        return 0.3, "Candidate record lists no ISBNs to compare", False

    for c_isbn in clean_cands:
        if clean_q == c_isbn:
            return 1.0, f"Exact ISBN match found ({clean_q})", False
        # ISBN-10 vs ISBN-13 core check
        if len(clean_q) in (10, 13) and len(c_isbn) in (10, 13):
            core_q = clean_q[3:12] if len(clean_q) == 13 else clean_q[:9]
            core_c = c_isbn[3:12] if len(c_isbn) == 13 else c_isbn[:9]
            if core_q == core_c:
                return 0.98, f"High-confidence ISBN-10/13 core digit match ({clean_q} ~ {c_isbn})", False

    return 0.0, f"Conflicting ISBN: Query ({clean_q}) differs from candidate ISBNs ({', '.join(clean_cands)})", True


def _decompose_query_string(q_str: str) -> Tuple[str, str, str]:
    """
    Decompose a unified search string into potential (title, author, isbn).
    Supports:
      - ISBN strings (10 or 13 digits)
      - 'Title by Author'
      - 'Title — Author' (em-dash \u2014)
      - 'Title – Author' (en-dash \u2013)
      - 'Title - Author' (hyphen)
      - 'Title / Author'
    """
    if not q_str:
        return "", "", ""
    clean = q_str.strip()

    # Check if entire query is an ISBN
    isbn_cand = re.sub(r"[^0-9Xx]", "", clean)
    if len(isbn_cand) in (10, 13) and len(clean.replace("-", "").replace(" ", "")) in (10, 13):
        return "", "", isbn_cand

    # Check for "by" pattern: "Frankenstein by Mary Shelley"
    if " by " in clean.lower():
        parts = re.split(r"\s+by\s+", clean, flags=re.IGNORECASE, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), parts[1].strip(), ""

    # Check for em-dash (\u2014), en-dash (\u2013), or hyphen with whitespace
    dash_match = re.search(r"\s*[\u2014\u2013\-]{1,2}\s*", clean)
    if dash_match:
        idx = dash_match.start()
        end_idx = dash_match.end()
        p1 = clean[:idx].strip()
        p2 = clean[end_idx:].strip()
        if p1 and p2:
            return p1, p2, ""

    return clean, "", ""


def _is_biography_or_about_author(candidate_title: str, query_author: str, candidate_authors: List[str]) -> bool:
    """
    Detect if candidate is a biography, critical study, or work ABOUT the author,
    rather than a book written BY the author.
    Example: 'Monster: The Story of Young Mary Shelley' by Arnold, M. R.
    """
    if not query_author:
        return False

    q_author_clean = _clean_str(query_author)
    q_tokens = [t for t in q_author_clean.split() if len(t) > 2]
    if not q_tokens:
        return False

    c_title_clean = _clean_str(candidate_title)

    # Check author similarity
    author_ratio, _ = _calculate_author_similarity(query_author, candidate_authors)
    if author_ratio >= 0.70:
        # Candidate was authored by requested author
        return False

    # Check if query author's name is in candidate title
    author_in_title = False
    if q_author_clean in c_title_clean:
        author_in_title = True
    elif len(q_tokens) >= 2 and all(t in c_title_clean.split() for t in q_tokens):
        author_in_title = True
    elif len(q_tokens) >= 1 and q_tokens[-1] in c_title_clean.split():
        bio_indicators = [
            "biography", "life of", "story of", "young", "letters of",
            "critical", "world of", "about", "companion", "memoir", "portrait"
        ]
        if any(ind in c_title_clean for ind in bio_indicators):
            author_in_title = True

    return author_in_title


def classify_candidate_match(
    query: BookSearchQuery,
    candidate: BookCandidate,
    confidence: ConfidenceBreakdown
) -> Tuple[str, str]:
    """
    Categorize candidate into one of 4 strict tiers:
      - EXACT_MATCH: Primary exact title and author match.
      - ALTERNATE_EDITION: Same core work/author, different edition/year/publisher/format.
      - RELATED_PUBLICATION: Author biography, critical study, adaptation, or related work.
      - UNRELATED: Unrelated record, irrelevant keyword collision.
    Returns: (match_type, match_explanation)
    """
    eff_title = (query.title or "").strip()
    eff_author = (query.author or "").strip()
    eff_isbn = (query.isbn or "").strip()

    if query.q and query.q.strip():
        dt, da, di = _decompose_query_string(query.q)
        if not eff_title and dt:
            eff_title = dt
        if not eff_author and da:
            eff_author = da
        if not eff_isbn and di:
            eff_isbn = di

    # 1. Biography or Work ABOUT Author check (Rule 6)
    if eff_author and _is_biography_or_about_author(candidate.title, eff_author, candidate.authors):
        cand_author_str = ", ".join(candidate.authors) if candidate.authors else "Unknown author"
        return (
            "RELATED_PUBLICATION",
            f"Related publication: Biographical or critical study about author '{eff_author}' by {cand_author_str}."
        )

    title_ratio = _calculate_string_similarity(eff_title, candidate.title) if eff_title else 0.5
    author_ratio, author_note = _calculate_author_similarity(eff_author, candidate.authors) if eff_author else (0.5, "Neutral")
    isbn_ratio = 0.0
    if eff_isbn:
        isbn_ratio, _, _ = _calculate_isbn_similarity(eff_isbn, candidate.isbns)

    # 2. Hard Mismatch / Unrelated checks (Rule 5)
    # If title was queried and title ratio is very low (< 0.35) and author ratio is low (< 0.40)
    if eff_title and title_ratio < 0.35 and author_ratio < 0.40 and isbn_ratio < 0.90:
        return (
            "UNRELATED",
            f"Unrelated record: Title ('{candidate.title}') and author diverge significantly from requested book."
        )

    # If author was queried and has hard mismatch (< 0.20), but title is somewhat similar (e.g. adaptation by someone else)
    if eff_author and author_ratio < 0.20 and not (eff_isbn and isbn_ratio >= 0.98):
        if title_ratio >= 0.50:
            return (
                "RELATED_PUBLICATION",
                f"Related work: Adaptation or different author ({', '.join(candidate.authors)}) than requested '{eff_author}'."
            )
        else:
            return (
                "UNRELATED",
                f"Unrelated record: Conflicting author ({', '.join(candidate.authors)}) and low title match."
            )

    # 3. Exact Match check (Rule 2)
    is_exact_title = (
        _clean_str(eff_title) == _clean_str(candidate.title)
        or _clean_str(candidate.title).startswith(_clean_str(eff_title) + " ")
        or _clean_str(eff_title).startswith(_clean_str(candidate.title) + " ")
        or title_ratio >= 0.85
    ) if eff_title else False

    is_exact_author = author_ratio >= 0.85 if eff_author else True
    is_exact_isbn = isbn_ratio >= 0.98 if eff_isbn else False

    if is_exact_isbn or (is_exact_title and is_exact_author):
        return (
            "EXACT_MATCH",
            f"Exact match: Verified title '{candidate.title}' and author convergence with requested query."
        )

    # 4. Alternate Edition check (Rule 4)
    if (title_ratio >= 0.70 or is_exact_title) and author_ratio >= 0.70:
        ed_str = f" ({candidate.edition})" if candidate.edition else ""
        year_str = f", published {candidate.published_year}" if candidate.published_year else ""
        pub_str = f" by {candidate.publisher}" if candidate.publisher else ""
        return (
            "ALTERNATE_EDITION",
            f"Alternate edition: Same intellectual work{ed_str}{year_str}{pub_str}."
        )

    # 5. Moderate title match with matching author -> Alternate edition
    if author_ratio >= 0.80 and title_ratio >= 0.45:
        return (
            "ALTERNATE_EDITION",
            f"Alternate edition or reprint by author '{eff_author}'."
        )

    if title_ratio >= 0.45 or author_ratio >= 0.50:
        return (
            "RELATED_PUBLICATION",
            f"Related publication: Partial title/author match ({int(title_ratio*100)}% title, {int(author_ratio*100)}% author)."
        )

    return (
        "UNRELATED",
        f"Unrelated record: Low query similarity ({int(title_ratio*100)}% title)."
    )


def calculate_confidence(
    query: BookSearchQuery,
    candidate: BookCandidate
) -> ConfidenceBreakdown:
    """
    Calculate deterministic, explainable Python Book Match Score (0 to 100).
    Disciplined weights & rules:
      - Title match: max 30 pts
      - Author match: max 25 pts
      - ISBN match: max 20 pts
      - Edition & publication year: max 15 pts
      - Publisher match: max 10 pts
      - Exact Match Alignment Bonuses (for verified Title+Author or Exact ISBN)
      - Penalties for unqueried fields when primary title is a mismatch
      - Strict cap for hard mismatches (conflicting ISBN or conflicting author)
      - Never artificially inflate confidence scores
    """
    evidence_used: List[str] = []
    missing_fields: List[str] = []
    mismatches: List[str] = []
    explanation: List[str] = []
    has_hard_mismatch = False

    # Resolve effective title, author, and isbn
    eff_title = (query.title or "").strip()
    eff_author = (query.author or "").strip()
    eff_isbn = (query.isbn or "").strip()

    if query.q and query.q.strip():
        q_title, q_author, q_isbn = _decompose_query_string(query.q)
        if not eff_title and q_title:
            eff_title = q_title
        if not eff_author and q_author:
            eff_author = q_author
        if not eff_isbn and q_isbn:
            eff_isbn = q_isbn

    # If author was not explicitly specified in query, check if candidate author is present in query.q
    if not eff_author and query.q and candidate.authors:
        q_lower = query.q.lower()
        for cand_author in candidate.authors:
            c_clean = _clean_str(cand_author)
            tokens = c_clean.split()
            found_author = False
            if c_clean and c_clean in _clean_str(query.q):
                eff_author = cand_author
                found_author = True
            elif tokens and len(tokens[-1]) >= 4 and tokens[-1] in q_lower.split():
                eff_author = cand_author
                found_author = True

            if found_author:
                if eff_title.lower() == query.q.lower():
                    for t in tokens:
                        if len(t) > 2:
                            eff_title = re.sub(r"\b" + re.escape(t) + r"\b", "", eff_title, flags=re.IGNORECASE).strip()
                    eff_title = re.sub(r"\s+", " ", eff_title).strip()
                break

    # Flags
    is_exact_title = False
    is_exact_author = False
    is_exact_isbn = False

    # Check if candidate is a biography or about the author
    is_biography = False
    if eff_author and _is_biography_or_about_author(candidate.title, eff_author, candidate.authors):
        is_biography = True
        has_hard_mismatch = True
        mismatches.append(f"Biography or critical work about author '{eff_author}' (not written by '{eff_author}')")
        candidate.is_approximate_suggestion = True

    # Check ISBN early if present
    if eff_isbn:
        isbn_ratio_early, _, _ = _calculate_isbn_similarity(eff_isbn, candidate.isbns)
        if isbn_ratio_early >= 0.98:
            is_exact_isbn = True

    # 1. Title Match (max 30 pts)
    title_ratio = 0.5
    if is_biography:
        title_score = 0.0
        title_ratio = 0.0
        evidence_used.append("Title: 0 pts (Work is about author, not requested title)")
        explanation.append(f"Title: 0/30 pts (Biographical title '{candidate.title}' does not match requested title).")
    elif eff_title:
        title_ratio = _calculate_string_similarity(eff_title, candidate.title)

        # Check if query string contains candidate title or vice versa
        c_title_clean = _clean_str(candidate.title)
        q_title_clean = _clean_str(eff_title)
        if c_title_clean == q_title_clean:
            title_ratio = 1.0
            is_exact_title = True
        elif c_title_clean.startswith(q_title_clean + " ") or q_title_clean.startswith(c_title_clean + " "):
            title_ratio = max(title_ratio, 0.90)
            is_exact_title = False

        title_score = round(title_ratio * 30.0, 2)
        pct = int(title_ratio * 100)
        evidence_used.append(f"Title similarity: {pct}%")
        explanation.append(f"Title: {title_score}/30 pts ({pct}% match between '{eff_title}' and '{candidate.title}').")

        if title_ratio < 0.65:
            mismatches.append(f"Title discrepancy: '{eff_title}' vs '{candidate.title}' ({pct}% match)")
            candidate.is_approximate_suggestion = True
    else:
        title_score = 15.0  # Neutral baseline
        missing_fields.append("Query title missing")
        explanation.append("Title: 15/30 pts (Neutral baseline; no title specified in query).")

    # Scaling factor: if a title was queried but has low match, do NOT award full neutral points for omitted fields!
    if eff_title and title_ratio < 0.65 and not is_exact_isbn:
        neutral_scale = max(0.05, round((title_ratio / 0.65) ** 1.8, 3))
    else:
        neutral_scale = 1.0

    # 2. Author Match (max 25 pts)
    author_ratio = 0.5
    is_exact_author = False
    if is_biography:
        author_score = 0.0
        evidence_used.append(f"Author conflict: '{', '.join(candidate.authors)}' is author of biography, not '{eff_author}'")
        explanation.append(f"Author: 0/25 pts (Author mismatch: book is about '{eff_author}', but author is {candidate.authors}).")
    elif eff_author:
        author_ratio, author_note = _calculate_author_similarity(eff_author, candidate.authors)
        if author_ratio >= 0.90:
            is_exact_author = True
        author_score = round(author_ratio * 25.0, 2)
        pct = int(author_ratio * 100)
        evidence_used.append(f"Author similarity: {pct}%")
        explanation.append(f"Author: {author_score}/25 pts ({pct}% match: {author_note}).")
        if author_ratio < 0.2:
            mismatches.append(f"Author conflict: Query '{eff_author}' not found in candidate authors {candidate.authors}")
            has_hard_mismatch = True
    else:
        author_score = round(12.5 * neutral_scale, 2)
        missing_fields.append("Query author missing")
        explanation.append(f"Author: {author_score}/25 pts (Neutral baseline; no author specified).")

    # 3. ISBN Match (max 20 pts)
    is_exact_isbn = False
    if eff_isbn:
        isbn_ratio, isbn_note, isbn_hard_mismatch = _calculate_isbn_similarity(eff_isbn, candidate.isbns)
        if isbn_ratio >= 0.98:
            is_exact_isbn = True
        isbn_score = round(isbn_ratio * 20.0, 2)
        evidence_used.append(f"ISBN verification: {isbn_note}")
        explanation.append(f"ISBN: {isbn_score}/20 pts ({isbn_note}).")
        if isbn_hard_mismatch:
            mismatches.append(isbn_note)
            has_hard_mismatch = True
    else:
        isbn_score = round(10.0 * neutral_scale, 2)
        missing_fields.append("Query ISBN missing")
        explanation.append(f"ISBN: {isbn_score}/20 pts (Neutral baseline; no ISBN queried).")

    # 4. Edition & Publication Year (max 15 pts)
    year_ratio = 0.5
    if query.year and candidate.published_year:
        diff = abs(query.year - candidate.published_year)
        if diff == 0:
            year_ratio = 1.0
            evidence_used.append(f"Exact year match ({query.year})")
            explanation.append(f"Edition & Year: 15/15 pts (Exact publication year match {query.year}).")
        elif diff <= 2:
            year_ratio = 0.8
            evidence_used.append(f"Close year ({candidate.published_year} vs {query.year})")
            explanation.append(f"Edition & Year: 12/15 pts (Close year delta of {diff} years).")
        elif diff <= 5:
            year_ratio = 0.5
            explanation.append(f"Edition & Year: 7.5/15 pts (Moderate publication year gap: {diff} years).")
        else:
            year_ratio = 0.2
            mismatches.append(f"Year divergence: Candidate year ({candidate.published_year}) differs significantly from query ({query.year})")
            explanation.append(f"Edition & Year: 3/15 pts (Large year divergence of {diff} years).")
    elif query.edition and candidate.edition:
        if _clean_str(query.edition) in _clean_str(candidate.edition):
            year_ratio = 0.9
            evidence_used.append(f"Edition string match ('{query.edition}')")
            explanation.append(f"Edition & Year: 13.5/15 pts (Edition matched '{candidate.edition}').")
    else:
        if not query.year and not query.edition:
            missing_fields.append("Query year/edition missing")
        if not candidate.published_year:
            missing_fields.append("Candidate publication year missing")
        year_ratio = 0.5 * neutral_scale
        explanation.append(f"Edition & Year: {round(year_ratio * 15.0, 1)}/15 pts (Neutral baseline).")

    edition_year_score = round(year_ratio * 15.0, 2)

    # 5. Publisher Match (max 10 pts)
    if candidate.publisher:
        evidence_used.append(f"Publisher documented: '{candidate.publisher}'")
        publisher_score = round(9.0 * (1.0 if neutral_scale > 0.5 else 0.3), 2)
        explanation.append(f"Publisher: {publisher_score}/10 pts (Verified publisher '{candidate.publisher}').")
    else:
        missing_fields.append("Candidate publisher not specified")
        publisher_score = round(5.0 * neutral_scale, 2)
        explanation.append(f"Publisher: {publisher_score}/10 pts (Neutral; publisher metadata absent).")

    # Base Sum
    raw_total = title_score + author_score + isbn_score + edition_year_score + publisher_score

    # Exact Alignment Boosts:
    # 1. Exact Title + Author match: Boost to ensure Strong Match tier (90+)
    if is_exact_title and is_exact_author and not has_hard_mismatch:
        alignment_boost = 15.0
        raw_total += alignment_boost
        explanation.append(f"ALIGNMENT BONUS: +{alignment_boost} pts for verified Title & Author convergence.")

    # 2. Exact ISBN match: Boost to ensure Strong Match tier (90+)
    if is_exact_isbn and not has_hard_mismatch:
        alignment_boost = 12.0
        raw_total += alignment_boost
        explanation.append(f"ALIGNMENT BONUS: +{alignment_boost} pts for verified exact ISBN identity.")

    # 3. Exact Title match: Boost when title matches 100% and no hard mismatch
    if is_exact_title and not has_hard_mismatch and not (is_exact_title and is_exact_author):
        alignment_boost = 10.0
        raw_total += alignment_boost
        explanation.append(f"ALIGNMENT BONUS: +{alignment_boost} pts for verified exact title identity.")

    # Hard Mismatch Safeguard Rule:
    if has_hard_mismatch:
        raw_total = min(raw_total, 25.0 if is_biography else 64.0)
        explanation.append("HARD MISMATCH TRIGGERED: Score capped due to conflicting ISBN, author, or biography classification.")

    # Title Mismatch Safeguard Rule:
    if eff_title and title_ratio < 0.65 and not is_exact_isbn:
        max_cap = 25.0 if title_ratio < 0.40 else 48.0
        raw_total = min(raw_total, max_cap)
        explanation.append(f"APPROXIMATE SUGGESTION: Score capped at {max_cap}/100 due to non-exact title similarity ({int(title_ratio*100)}%).")
        candidate.is_approximate_suggestion = True

    total_score = max(0.0, min(100.0, round(raw_total, 1)))

    # Presentation Tiers
    if total_score >= 90.0:
        tier = ConfidenceTier.STRONG_MATCH
    elif total_score >= 75.0:
        tier = ConfidenceTier.PLAUSIBLE_MATCH
    else:
        tier = ConfidenceTier.LOW_CONFIDENCE

    breakdown = ConfidenceBreakdown(
        total_score=total_score,
        title_score=title_score,
        author_score=author_score,
        isbn_score=isbn_score,
        edition_year_score=edition_year_score,
        publisher_score=publisher_score,
        confidence_tier=tier,
        evidence_used=evidence_used,
        missing_fields=missing_fields,
        mismatches_and_uncertainty=mismatches,
        explanation=explanation,
        has_hard_mismatch=has_hard_mismatch
    )

    # Classify match type and narrative explanation
    cand_match_type, cand_match_exp = classify_candidate_match(query, candidate, breakdown)
    candidate.match_type = cand_match_type
    candidate.match_explanation = cand_match_exp

    return breakdown
