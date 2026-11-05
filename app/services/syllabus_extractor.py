import io
import re
import uuid
import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field

from app.schemas import ExtractedBookRecord, BookType, SyllabusUploadResponse
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Common academic publishers for regex matching
KNOWN_PUBLISHERS = [
    "Pearson", "Wiley", "McGraw-Hill", "McGraw Hill", "O'Reilly", "MIT Press",
    "Cambridge University Press", "Oxford University Press", "Springer", "Addison-Wesley",
    "Addison Wesley", "Prentice Hall", "Prentice-Hall", "Cengage", "Packt", "Elsevier",
    "Morgan Kaufmann", "Academic Press", "Routledge", "Sybex", "W. H. Freeman",
    "HarperCollins", "W. W. Norton", "Simon & Schuster", "Taylor & Francis",
    "No Starch Press", "No Starch", "Penguin Classics", "Penguin", "Dover", "OpenStax",
    "CRC Press", "Chapman & Hall", "Sams Publishing", "Sams", "Wrox", "John Wiley",
    "IEEE Press", "Bantam", "Signet", "Vintage", "Bloomsbury", "Macmillan",
    "Course Technology", "Arpaci-Dusseau Books", "Arpaci-Dusseau"
]

PUBLISHER_SUFFIX_PATTERN = re.compile(
    r"\b(press|publishers?|publishing|publications?|books?|classics|media|house|company|sons|co\.)\b",
    re.IGNORECASE
)

NON_BOOK_PATTERNS = re.compile(
    r"^(outcome|credit|objective|syllabus|prerequisite|assessment|evaluation|grading|week\s*\d+|lecture\s*\d+|exam|midterm|final\s*exam|homework|attendance)\b",
    re.IGNORECASE
)

# Section header regexes
TEXTBOOK_HEADERS = re.compile(
    r"\b(text\s*books?|prescribed\s*books?|required\s*text(?:s)?|core\s*reading|main\s*textbooks?|prescribed\s*textbooks?)\b",
    re.IGNORECASE
)
REFERENCE_HEADERS = re.compile(
    r"\b(reference\s*books?|references?|recommended\s*reading|suggested\s*reading|further\s*reading|supplementary\s*reading|bibliography|recommended\s*books?)\b",
    re.IGNORECASE
)
UNIT_HEADERS = re.compile(
    r"\b(unit\s*[-:]?\s*[0-9IVXLCDM]+|module\s*[-:]?\s*[0-9IVXLCDM]+|chapter\s*[-:]?\s*[0-9IVXLCDM]+|course\s*(?:title|name|code)\s*[-:]|subject\s*[-:])",
    re.IGNORECASE
)


def is_publisher_token(token: str) -> bool:
    clean = token.strip()
    if any(pub.lower() == clean.lower() or pub.lower() in clean.lower() for pub in KNOWN_PUBLISHERS):
        return True
    if PUBLISHER_SUFFIX_PATTERN.search(clean) and len(clean.split()) <= 4:
        return True
    return False


class SyllabusExtractor:
    """
    Robust university syllabus parser supporting PDF, DOCX, and TXT files.
    Extracts course subjects, reading list sections, and structured reference books
    with page numbers, snippets, and confidence scoring.
    """

    def __init__(self):
        self.gemini = GeminiService()

    def extract_text_from_file(self, content: bytes, filename: str) -> Tuple[List[Tuple[int, str]], str]:
        """
        Extract text from file bytes preserving page numbers where possible.
        Returns: (pages_list [(page_num, text)], file_type)
        """
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(content), "PDF"
        elif ext in (".docx", ".doc"):
            return self._extract_docx(content), "DOCX"
        else:
            return self._extract_txt(content), "TXT"

    def _extract_pdf(self, content: bytes) -> List[Tuple[int, str]]:
        """Extract pages from PDF using pypdf, with OCR detection for scanned documents."""
        pages = []
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            has_scanned_pages = False

            for i, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                # If extracted text is very short and page contains images, document is likely scanned
                if len(text) < 40 and hasattr(page, "images") and len(page.images) > 0:
                    has_scanned_pages = True
                    logger.info(f"Page {i+1} has {len(page.images)} image(s) with minimal embedded text ({len(text)} chars); detected scanned page.")
                    # If Gemini is configured and available, perform OCR via multimodal flash
                    if self.gemini.is_available:
                        try:
                            # Extract primary image bytes
                            img_obj = page.images[0]
                            img_bytes = img_obj.data
                            prompt = "Perform high-accuracy OCR on this scanned academic syllabus page. Transcribe all text, especially course subjects, units, textbooks, reference books, authors, publishers, editions, and ISBNs verbatim."
                            from google.genai import types
                            resp = self.gemini._client.models.generate_content(
                                model=self.gemini.model_name,
                                contents=[
                                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                                    prompt
                                ]
                            )
                            if resp and resp.text:
                                text = resp.text
                                logger.info(f"OCR successfully extracted {len(text)} chars from scanned page {i+1}")
                        except Exception as ocr_err:
                            logger.warning(f"Gemini OCR fallback for page {i+1} failed: {ocr_err}")

                pages.append((i + 1, text))

            if has_scanned_pages:
                logger.info("PDF document processed with scanned page detection and OCR handling.")

        except Exception as e:
            logger.warning(f"pypdf extraction error: {e}")
            # Fallback
            text = content.decode("utf-8", errors="ignore")
            pages.append((1, text))
        return pages

    def _extract_docx(self, content: bytes) -> List[Tuple[int, str]]:
        """Extract paragraphs from DOCX."""
        pages = []
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            all_text = []
            for p in doc.paragraphs:
                if p.text.strip():
                    all_text.append(p.text.strip())
            for t in doc.tables:
                for row in t.rows:
                    row_txt = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_txt:
                        all_text.append(row_txt)
            pages.append((1, "\n".join(all_text)))
        except Exception as e:
            logger.warning(f"python-docx extraction error: {e}, falling back to xml extraction")
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    text_parts = [node.text for node in tree.iterfind(".//w:t", ns) if node.text]
                    pages.append((1, "\n".join(text_parts)))
            except Exception as e2:
                logger.warning(f"Zipfile xml extraction failed: {e2}")
                pages.append((1, content.decode("utf-8", errors="ignore")))
        return pages

    def _extract_txt(self, content: bytes) -> List[Tuple[int, str]]:
        """Extract lines from plain text."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="ignore")

        # Split on form-feed character if present, otherwise single page
        parts = text.split("\f")
        pages = []
        for i, part in enumerate(parts):
            if part.strip():
                pages.append((i + 1, part))
        return pages if pages else [(1, text)]

    def _extract_metadata(self, pages: List[Tuple[int, str]]) -> Dict[str, Optional[str]]:
        """Extract university, department, programme, semester, and academic year."""
        all_text = "\n".join([p[1] for p in pages[:4]])
        meta = {
            "university": None,
            "department": None,
            "programme": None,
            "semester": None,
            "academic_year": None
        }

        # University / College
        uni_match = re.search(
            r"([A-Za-z0-9\s,&]+(?:university|institute\s+of\s+technology|college|polytechnic)\b|(?:university|institute|college)\s+of\s+[A-Za-z0-9\s,&]+)",
            all_text,
            re.IGNORECASE
        )
        if uni_match:
            uni = uni_match.group(0).strip().splitlines()[0].strip()
            if 4 <= len(uni) <= 80:
                meta["university"] = uni

        # Department
        dept_match = re.search(r"department\s+of\s+([A-Za-z0-9\s,&]+)", all_text, re.IGNORECASE)
        if dept_match:
            meta["department"] = dept_match.group(0).strip().splitlines()[0].strip()

        # Programme
        prog_match = re.search(
            r"(?:programme|degree|course)\s*[:\-–]\s*([A-Za-z0-9\.\s&]+)|\b(B\.?E\.?|B\.?Tech|B\.?Sc|M\.?Tech|M\.?S|M\.?C\.?A)\s+(?:in\s+)?([A-Za-z0-9\s&]+)",
            all_text,
            re.IGNORECASE
        )
        if prog_match:
            meta["programme"] = prog_match.group(0).strip().splitlines()[0].strip()

        # Semester
        sem_match = re.search(r"\b(semester|sem)\s*[-:]?\s*([0-9IVXLCDM]+|\w+)", all_text, re.IGNORECASE)
        if sem_match:
            meta["semester"] = f"{sem_match.group(1).capitalize()} {sem_match.group(2).upper()}"

        # Academic Year
        ay_match = re.search(r"\b(20\d\d\s*[-–]\s*20?\d\d)\b", all_text)
        if ay_match:
            meta["academic_year"] = ay_match.group(1).strip()

        return meta

    def parse_syllabus(
        self,
        content: bytes,
        filename: str,
        syllabus_id: Optional[str] = None,
        return_metadata: bool = False
    ):
        """
        Main extraction pipeline:
        1. Extract text and page numbers
        2. Detect courses and subjects
        3. Identify textbook/reference book lines
        4. Parse structured bibliographic attributes (clean_title, authors list, edition, priority)
        5. Merge duplicates and calculate confidence
        """
        syl_id = syllabus_id or f"syl_{uuid.uuid4().hex[:10]}"
        pages, file_type = self.extract_text_from_file(content, filename)
        total_pages = len(pages)
        metadata = self._extract_metadata(pages)

        subjects: List[str] = []
        raw_candidates: List[ExtractedBookRecord] = []

        current_subject = "General Syllabus Reading"
        current_subject_code = None
        current_book_type = BookType.TEXTBOOK
        in_reading_section = False

        subject_patterns = [
            re.compile(r"^(?:subject|course|paper)\s*(?:\d+)?\s*[:\-–]\s*(.+)", re.IGNORECASE),
            re.compile(r"^([A-Z]{2,5}\s*[-]?\s*\d{3,4}[A-Z]?)\s*[:\-–]\s*(.+)", re.IGNORECASE),
            re.compile(r"^(?:course\s*title|subject\s*title|course\s*name)\s*[:\-–]\s*(.+)", re.IGNORECASE),
        ]

        for page_num, page_text in pages:
            lines = [l.strip() for l in page_text.splitlines() if l.strip()]

            for line in lines:
                # 1. Check for Subject / Course Titles
                matched_subject = None
                matched_code = None

                for pat in subject_patterns:
                    m = pat.search(line)
                    if m:
                        if len(m.groups()) == 2:
                            matched_code = m.group(1).strip()
                            matched_subject = f"{matched_code} - {m.group(2).strip()}"
                        else:
                            matched_subject = m.group(1).strip()
                            code_in_subj = re.search(r"\b([A-Z]{2,5}\s*[-]?\s*\d{3,4}[A-Z]?)\b", matched_subject)
                            if code_in_subj:
                                matched_code = code_in_subj.group(1).strip()
                        break

                if matched_subject and len(matched_subject) >= 3 and not NON_BOOK_PATTERNS.search(matched_subject):
                    current_subject = matched_subject
                    current_subject_code = matched_code
                    if current_subject not in subjects:
                        subjects.append(current_subject)
                    in_reading_section = False
                    continue

                # Unit / Module header
                if UNIT_HEADERS.search(line) and len(line) < 80:
                    if not current_subject or current_subject == "General Syllabus Reading":
                        current_subject = line.strip()
                        if current_subject not in subjects:
                            subjects.append(current_subject)
                    in_reading_section = False
                    continue

                # 2. Check for Section headers
                if TEXTBOOK_HEADERS.search(line):
                    current_book_type = BookType.TEXTBOOK
                    in_reading_section = True
                    continue
                elif REFERENCE_HEADERS.search(line):
                    current_book_type = BookType.REFERENCE
                    in_reading_section = True
                    continue

                # 3. Parse Bibliographic Lines
                # Check if line looks like a citation (numbered list, author-title pattern, or contains year/publisher/ISBN)
                if in_reading_section or self._looks_like_citation(line):
                    book = self._parse_citation_line(
                        line=line,
                        syllabus_id=syl_id,
                        default_subject=current_subject,
                        subject_code=current_subject_code,
                        default_type=current_book_type,
                        page_number=page_num
                    )
                    if book:
                        raw_candidates.append(book)

        # Merge duplicates
        merged_books = self._merge_duplicate_books(raw_candidates)

        if not subjects and merged_books:
            subjects = list(set(b.subject for b in merged_books if b.subject))

        if return_metadata:
            return subjects, merged_books, total_pages, metadata
        return subjects, merged_books, total_pages

    def _looks_like_citation(self, line: str) -> bool:
        """Heuristic check if a line is a bibliographic reference."""
        if len(line) < 12 or len(line) > 350:
            return False

        if NON_BOOK_PATTERNS.search(line.strip()):
            return False

        # Starts with numbered reference: "1.", "[1]", "(1)"
        if re.match(r"^(\d{1,2}[\.\)]|\[\d{1,2}\]|\([a-z0-9]+\)|[•\-\*])\s+", line):
            return True

        # Contains year in parentheses: "(2018)" or ", 2019"
        if re.search(r"[\(,]\s*(19\d\d|20\d\d)\s*[\),]", line):
            return True

        # Contains known academic publisher or publisher token
        if any(pub.lower() in line.lower() for pub in KNOWN_PUBLISHERS):
            return True
        if PUBLISHER_SUFFIX_PATTERN.search(line):
            return True

        # Contains ISBN
        if re.search(r"\bISBN\b", line, re.IGNORECASE):
            return True

        # Contains edition: "3rd ed", "4th edition"
        if re.search(r"\b\d+(?:st|nd|rd|th)?\s+ed(?:ition)?\b", line, re.IGNORECASE):
            return True

        return False

    def normalize_clean_title(
        self,
        title: str,
        publisher: Optional[str] = None,
        edition: Optional[str] = None,
        year: Optional[int] = None
    ) -> str:
        """
        Clean and normalize book title by stripping messy artifacts:
        - Publisher names (e.g., Pearson, Wiley, McGraw-Hill, O'Reilly, MIT Press, Springer, Prentice Hall)
        - Edition designations (e.g., '3rd Ed', '10th Edition', '(3rd ed.)', 'First Edition')
        - Extraneous publication years (e.g., '(2018)', ', 2018', '[2020]')
        - Volume and part indicators (e.g., 'Vol. 1', 'Volume 2', 'Part I')
        - ISBN tokens and citation quotation marks
        Produces a clean title optimized for digital library API queries.
        """
        if not title:
            return ""

        working = title.strip()

        # 1. Strip enclosing quotes
        working = re.sub(r'^["“\'`]+|["”\'`]+$', '', working).strip()

        # 2. Strip publisher name if appended to title
        if publisher:
            working = re.sub(r'[\-,\s:]+\b' + re.escape(publisher) + r'\b', '', working, flags=re.IGNORECASE)
            working = re.sub(r'\b' + re.escape(publisher) + r'\b', '', working, flags=re.IGNORECASE)
        for pub in KNOWN_PUBLISHERS:
            working = re.sub(r'[\-,\s:]+\b' + re.escape(pub) + r'\b', '', working, flags=re.IGNORECASE)

        # 3. Strip publisher suffixes
        working = re.sub(r'[\-,\s:]+\b(?:press|publishers?|publishing|publications?|classics)\b', '', working, flags=re.IGNORECASE)

        # 4. Strip edition indicators (e.g., "3rd Ed", "10th Edition", "(3rd ed.)")
        working = re.sub(
            r'[\(,\[]?\s*\b(?:\d+(?:st|nd|rd|th)?|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+ed(?:ition)?\.?\s*[\),\]]?',
            '',
            working,
            flags=re.IGNORECASE
        )
        working = re.sub(r'[\(,\[]?\s*\b\d+\s*ed\b\.?\s*[\),\]]?', '', working, flags=re.IGNORECASE)

        # 5. Strip extraneous publication years (e.g., "(2018)", ", 2018", "[2024]")
        working = re.sub(r'[\(,\[]?\s*\b(?:19\d\d|20\d\d)\b\s*[\),\]]?', '', working)

        # 6. Strip volume / part / chapter tokens
        working = re.sub(r'[\-,\s:]+\b(?:vol(?:ume)?\.?|part)\s+[0-9IVXLCDM]+\b', '', working, flags=re.IGNORECASE)

        # 7. Strip trailing ISBN mentions
        working = re.sub(r'[\-,\s:]+\bISBN(?:-1[03])?:?\s*[0-9Xx\-]{10,17}\b', '', working, flags=re.IGNORECASE)

        # 8. Clean up whitespace and edge punctuation
        working = re.sub(r'\s+', ' ', working).strip(" ,-.:;\"'()[]{}")
        return working if len(working) >= 3 else title.strip()

    def parse_authors_list(self, author_str: Optional[str]) -> List[str]:
        """
        Parse author citation string into a clean structured list of author names.
        Handles styles: 'Silberschatz, A., Galvin, P.B., and Gagne, G.',
        'Tanenbaum, A. S., & Woodhull, A. S.', 'Andrew S. Tanenbaum and Herbert Bos'.
        """
        if not author_str:
            return []

        clean_a = re.sub(r'\b(?:et\s+al\.?|and\s+others)\b', '', author_str, flags=re.IGNORECASE).strip()

        # Split on '&' or ' and '
        raw_segments = re.split(r'\s*&\s*|\s+and\s+', clean_a, flags=re.IGNORECASE)
        authors = []
        for seg in raw_segments:
            seg = seg.strip(" ,-.:;")
            if not seg:
                continue
            comma_parts = [p.strip() for p in seg.split(",") if p.strip()]
            if len(comma_parts) > 2:
                for cp in comma_parts:
                    if len(cp) >= 2:
                        authors.append(cp)
            else:
                authors.append(seg)

        # Deduplicate while preserving order
        seen = set()
        unique_authors = []
        for a in authors:
            a_clean = re.sub(r'\s+', ' ', a).strip(" ,-.:;")
            if a_clean and a_clean.lower() not in seen:
                seen.add(a_clean.lower())
                unique_authors.append(a_clean)

        return unique_authors

    def _parse_citation_line(
        self,
        line: str,
        syllabus_id: str,
        default_subject: str,
        default_type: BookType,
        page_number: int,
        subject_code: Optional[str] = None
    ) -> Optional[ExtractedBookRecord]:
        """
        Parse a single syllabus citation line into an ExtractedBookRecord.
        """
        clean_line = line.strip()
        # Remove leading number/bullet: "1. ", "[2] ", "• "
        clean_line = re.sub(r"^(\d{1,2}[\.\)]|\[\d{1,2}\]|\([a-z0-9]+\)|[•\-\*])\s*", "", clean_line).strip()

        if len(clean_line) < 10:
            return None

        # Ignore non-book text like "Outcome:", "Credits:", "Evaluation:"
        if NON_BOOK_PATTERNS.search(clean_line):
            return None

        # Extract ISBN
        isbn_match = re.search(r"\b(?:ISBN(?:-1[03])?:?\s*)?([0-9Xx\-]{10,17})\b", clean_line, re.IGNORECASE)
        isbn = None
        if isbn_match:
            cand_isbn = re.sub(r"[^0-9Xx]", "", isbn_match.group(1))
            if len(cand_isbn) in (10, 13):
                isbn = isbn_match.group(1).strip()
                clean_line = clean_line.replace(isbn_match.group(0), "").strip()

        # Extract Year
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_line)
        year = int(year_match.group(1)) if year_match else None

        # Extract Edition
        edition_match = re.search(
            r"\b(\d+(?:st|nd|rd|th)?\s+ed(?:ition)?|(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+edition)\b",
            clean_line,
            re.IGNORECASE
        )
        edition = edition_match.group(1) if edition_match else None

        # Extract Publisher
        publisher = None
        for pub in KNOWN_PUBLISHERS:
            if re.search(r"\b" + re.escape(pub) + r"\b", clean_line, re.IGNORECASE):
                publisher = pub
                break

        # Extract Title & Author & refine Publisher
        title, author, detected_pub = self._extract_title_and_author(
            clean_line, edition, publisher, str(year) if year else None
        )
        if detected_pub and not publisher:
            publisher = detected_pub

        if not title or len(title) < 3:
            return None

        # Clean title & author
        title = re.sub(r"\s+", " ", title).strip(" ,-.:;")
        if author:
            author = re.sub(r"\s+", " ", author).strip(" ,-.:;")

        # Reject if title is just course/unit heading or evaluation
        if NON_BOOK_PATTERNS.search(title) or len(title) < 3:
            return None

        # Normalize clean title (stripping publisher, edition e.g. '3rd Ed', extraneous years)
        clean_title = self.normalize_clean_title(title, publisher, edition, year)
        authors_list = self.parse_authors_list(author)

        # Structured priority status
        if default_type == BookType.TEXTBOOK:
            priority_status = "REQUIRED"
        elif default_type == BookType.REFERENCE:
            priority_status = "RECOMMENDED"
        else:
            priority_status = "OPTIONAL"

        # Calculate extraction confidence
        confidence = 0.70
        if author:
            confidence += 0.15
        if year:
            confidence += 0.05
        if edition or publisher:
            confidence += 0.05
        if isbn:
            confidence += 0.05
        confidence = round(min(confidence, 0.98), 2)

        return ExtractedBookRecord(
            id=f"book_{uuid.uuid4().hex[:10]}",
            syllabus_id=syllabus_id,
            title=title,
            clean_title=clean_title,
            author=author,
            authors=authors_list,
            edition=edition,
            year=year,
            publisher=publisher,
            isbn=isbn,
            book_type=default_type,
            priority_status=priority_status,
            subject=default_subject,
            subject_code=subject_code,
            page_number=page_number,
            context_snippet=line[:250],
            confidence=confidence,
            is_selected=True,
            created_at=datetime.now(timezone.utc).isoformat()
        )

    def _extract_title_and_author(
        self,
        line: str,
        edition: Optional[str],
        publisher: Optional[str],
        year_str: Optional[str]
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Extract book title, author, and detected publisher using delimiter & quote rules.
        Supports standard styles: APA, Harvard, IEEE, quoted titles, and multi-author citations.
        """
        working = line.strip()

        # 1. Quoted title pattern: Author, "Title", Publisher OR "Title" by Author
        quote_match = re.search(r'["“\']([^"”\']{4,120})["”\']', working)
        if quote_match:
            title = quote_match.group(1).strip()
            before_quote = working[:quote_match.start()].strip(" ,-:")
            after_quote = working[quote_match.end():].strip(" ,-:")
            if re.search(r'^\s*by\s+', after_quote, re.IGNORECASE) or ' by ' in after_quote.lower():
                by_parts = re.split(r'\s+by\s+', ' ' + after_quote, flags=re.IGNORECASE, maxsplit=1)
                author = by_parts[1].split(',')[0].strip() if len(by_parts) > 1 else None
            elif before_quote and len(before_quote) >= 3 and not re.search(r"\b(unit|chapter|reference|textbook)\b", before_quote, re.I):
                author = before_quote
            elif after_quote and len(after_quote.split()) <= 4:
                author = after_quote
            else:
                author = None
            return title, author, publisher

        # 2. APA / Harvard citation format: Author(s) (Year). Title...
        apa_match = re.search(r'^(?P<author>.+?)\s*\((?P<year>19\d\d|20\d\d)\)[\.,\s]+(?P<rest>[^\.\(]+)', working)
        if apa_match:
            raw_author = apa_match.group("author").strip(" ,-:")
            raw_title = apa_match.group("rest").strip(" ,-:")
            if len(raw_title) >= 3 and len(raw_author) >= 3:
                return raw_title, raw_author, publisher

        # 3. "Title by Author" pattern
        if " by " in working.lower():
            parts = re.split(r"\s+by\s+", working, flags=re.IGNORECASE, maxsplit=1)
            title = parts[0].strip(" ,-:")
            after = parts[1].strip(" ,-:")
            author = after.split(",")[0].strip() if "," in after else after
            if publisher and publisher.lower() in author.lower():
                author = re.sub(r"\b" + re.escape(publisher) + r"\b.*", "", author, flags=re.I).strip(" ,-:")
            return title, author, publisher

        # 4. Standard citation stripping
        clean_working = working
        detected_publisher = publisher
        if detected_publisher:
            clean_working = re.sub(r"\b" + re.escape(detected_publisher) + r"\b", "", clean_working, flags=re.I)
        if edition:
            clean_working = re.sub(r"\b" + re.escape(edition) + r"\b", "", clean_working, flags=re.I)
        if year_str:
            clean_working = re.sub(r"\b" + re.escape(year_str) + r"\b", "", clean_working)
        clean_working = re.sub(r"\s+", " ", clean_working).strip(" ,-.:;")

        # Period separation with initial protection (Author. Title. Publisher)
        period_split = [p.strip() for p in re.split(r'(?<!\b[A-Za-z])\.\s+', clean_working) if p.strip()]
        if len(period_split) >= 2:
            cand_author = period_split[0]
            cand_title = ". ".join(period_split[1:])
            if len(cand_title) >= 3 and ("," in cand_author or " and " in cand_author or len(cand_author.split()) <= 5):
                sub_parts = [p.strip() for p in cand_title.split(",") if p.strip()]
                final_title_parts = []
                for p in sub_parts:
                    if is_publisher_token(p):
                        if not detected_publisher:
                            detected_publisher = p
                    else:
                        final_title_parts.append(p)
                title = ", ".join(final_title_parts)
                return title, cand_author, detected_publisher

        # Delimited by hyphen: "Mary Shelley - Frankenstein" or "Author - Title"
        if " - " in clean_working:
            parts = [p.strip() for p in clean_working.split(" - ") if p.strip()]
            if len(parts) >= 2:
                if len(parts[0].split()) <= 4 and not any(w.lower() in parts[0].lower() for w in ["introduction", "principles", "operating", "data", "modern", "python"]):
                    author = parts[0]
                    title = " - ".join(parts[1:])
                else:
                    title = parts[0]
                    author = parts[1] if len(parts[1].split()) <= 4 else None
                return title, author, detected_publisher

        # Comma-separated citation: e.g. "Silberschatz, Galvin, Gagne, Operating System Concepts"
        raw_parts = [p.strip() for p in clean_working.split(",") if p.strip()]
        cleaned_parts = []
        for p in raw_parts:
            if is_publisher_token(p):
                if not detected_publisher:
                    detected_publisher = p
            else:
                cleaned_parts.append(p)

        if len(cleaned_parts) >= 2:
            title_keywords = [
                "introduction", "principles", "operating", "fundamentals", "handbook", "complete",
                "crash", "course", "modern", "programming", "learning", "data", "concepts", "guide",
                "foundations", "design", "algorithms", "networks", "engineering", "intelligence",
                "systems", "database", "computer", "architecture"
            ]

            author_segments = []
            title_segments = []
            found_title = False

            for i, part in enumerate(cleaned_parts):
                part_lower = part.lower()
                is_name_like = (
                    len(part.split()) <= 3
                    and not any(kw in part_lower for kw in title_keywords)
                    and ":" not in part
                    and ";" not in part
                )
                if not found_title:
                    if is_name_like and (i < len(cleaned_parts) - 1):
                        author_segments.append(part)
                    else:
                        found_title = True
                        title_segments.append(part)
                else:
                    title_segments.append(part)

            if author_segments and title_segments:
                author = ", ".join(author_segments)
                title = ", ".join(title_segments)
                return title, author, detected_publisher
            else:
                author = cleaned_parts[0]
                title = ", ".join(cleaned_parts[1:])
                return title, author, detected_publisher

        # Fallback: whole clean line as title
        return clean_working.strip(" ,-.:"), None, detected_publisher

    def _merge_duplicate_books(self, books: List[ExtractedBookRecord]) -> List[ExtractedBookRecord]:
        """
        Merge identical books appearing across multiple units or sections,
        preserving all associated subjects and snippets.
        """
        merged_map: Dict[str, ExtractedBookRecord] = {}

        for b in books:
            norm_title = re.sub(r"[^\w\s]", "", b.title.lower()).strip()
            norm_author = re.sub(r"[^\w\s]", "", (b.author or "").lower()).strip()
            key = f"{norm_title}::{norm_author[:15]}"

            if key in merged_map:
                existing = merged_map[key]
                # Combine subjects if different
                if b.subject and b.subject not in (existing.subject or ""):
                    existing.subject = f"{existing.subject}; {b.subject}" if existing.subject else b.subject
                # Update missing metadata if this occurrence has more details
                if not existing.isbn and b.isbn:
                    existing.isbn = b.isbn
                if not existing.publisher and b.publisher:
                    existing.publisher = b.publisher
                if not existing.edition and b.edition:
                    existing.edition = b.edition
                if not existing.year and b.year:
                    existing.year = b.year
                if not existing.clean_title and b.clean_title:
                    existing.clean_title = b.clean_title
                if not existing.authors and b.authors:
                    existing.authors = b.authors
                if not existing.priority_status and b.priority_status:
                    existing.priority_status = b.priority_status
                existing.confidence = max(existing.confidence, b.confidence)
            else:
                merged_map[key] = b

        return list(merged_map.values())


syllabus_extractor = SyllabusExtractor()
