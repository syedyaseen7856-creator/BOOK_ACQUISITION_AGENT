import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.schemas import (
    SyllabusUploadResponse,
    SyllabusUpdateRequest,
    ExtractedBookRecord,
    BookType,
    SubjectBooksGroup,
    SyllabusSubjectsResponse
)
from app.db.repository import repository
from app.services.syllabus_extractor import syllabus_extractor
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/syllabus", tags=["Syllabus Book Extraction"])


@router.post("/upload", response_model=SyllabusUploadResponse)
async def upload_syllabus(
    file: UploadFile = File(...)
):
    """
    Upload an entire university syllabus (PDF, DOCX, or TXT).
    Automatically validates file type & size, extracts course subjects,
    detects textbook & reference book sections, parses bibliographic attributes,
    and returns an editable list of books with extraction confidence.
    """
    filename = file.filename or "syllabus.txt"
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    if ext not in (".pdf", ".docx", ".doc", ".txt", ".text", ".md"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: PDF (.pdf), Word (.docx), or Text (.txt)."
        )

    content = await file.read()
    file_size = len(content)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({file_size / (1024*1024):.1f}MB) exceeds limit of {settings.MAX_FILE_SIZE_MB}MB."
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    syllabus_id = f"syl_{uuid.uuid4().hex[:10]}"

    try:
        subjects, books, page_count, metadata = syllabus_extractor.parse_syllabus(
            content=content,
            filename=filename,
            syllabus_id=syllabus_id,
            return_metadata=True
        )

        # Persist upload and books to SQLite
        repository.save_syllabus_upload(
            syllabus_id=syllabus_id,
            filename=filename,
            file_type=ext.replace(".", "").upper(),
            file_size_bytes=file_size,
            page_count=page_count,
            extracted_subjects=subjects,
            raw_text=None,
            university=metadata.get("university"),
            department=metadata.get("department"),
            programme=metadata.get("programme"),
            semester=metadata.get("semester"),
            academic_year=metadata.get("academic_year")
        )

        repository.save_extracted_books(books)

        return SyllabusUploadResponse(
            syllabus_id=syllabus_id,
            filename=filename,
            file_type=ext.replace(".", "").upper(),
            file_size_bytes=file_size,
            page_count=page_count,
            university=metadata.get("university"),
            department=metadata.get("department"),
            programme=metadata.get("programme"),
            semester=metadata.get("semester"),
            academic_year=metadata.get("academic_year"),
            extracted_subjects=subjects,
            books=books,
            total_extracted=len(books),
            status="EXTRACTED",
            message=f"Successfully extracted {len(books)} reference book(s) across {len(subjects)} subject area(s)."
        )
    except Exception as e:
        logger.error(f"Syllabus extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing syllabus document: {str(e)}"
        )


class SyllabusRawTextInput(SyllabusUpdateRequest.__base__):
    text: str
    filename: Optional[str] = "syllabus_text.txt"
    course_title: Optional[str] = None


@router.post("/parse-text", response_model=SyllabusUploadResponse)
async def parse_syllabus_text(payload: SyllabusRawTextInput):
    """
    Parse raw syllabus text provided directly by user:
    - Extracts course titles, subjects, and all reference/textbooks.
    - Normalizes clean_title, authors list, edition, and priority status.
    - Saves structured records to database.
    """
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Syllabus text content cannot be empty.")

    filename = payload.filename or "syllabus_text.txt"
    content = raw_text.encode("utf-8")
    file_size = len(content)
    syllabus_id = f"syl_{uuid.uuid4().hex[:10]}"

    try:
        subjects, books, page_count, metadata = syllabus_extractor.parse_syllabus(
            content=content,
            filename=filename,
            syllabus_id=syllabus_id,
            return_metadata=True
        )

        if payload.course_title and payload.course_title.strip():
            c_title = payload.course_title.strip()
            if c_title not in subjects:
                subjects.insert(0, c_title)
            for b in books:
                if not b.subject or b.subject == "General Syllabus Reading":
                    b.subject = c_title

        repository.save_syllabus_upload(
            syllabus_id=syllabus_id,
            filename=filename,
            file_type="TXT",
            file_size_bytes=file_size,
            page_count=page_count,
            extracted_subjects=subjects,
            raw_text=raw_text,
            university=metadata.get("university"),
            department=metadata.get("department"),
            programme=metadata.get("programme"),
            semester=metadata.get("semester"),
            academic_year=metadata.get("academic_year")
        )

        repository.save_extracted_books(books)

        return SyllabusUploadResponse(
            syllabus_id=syllabus_id,
            filename=filename,
            file_type="TXT",
            file_size_bytes=file_size,
            page_count=page_count,
            university=metadata.get("university"),
            department=metadata.get("department"),
            programme=metadata.get("programme"),
            semester=metadata.get("semester"),
            academic_year=metadata.get("academic_year"),
            extracted_subjects=subjects,
            books=books,
            total_extracted=len(books),
            status="EXTRACTED",
            message=f"Successfully extracted {len(books)} reference book(s) across {len(subjects)} subject area(s)."
        )
    except Exception as e:
        logger.error(f"Raw syllabus text parsing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing raw syllabus text: {str(e)}"
        )


@router.get("/{syllabus_id}", response_model=SyllabusUploadResponse)
async def get_syllabus(syllabus_id: str):
    """
    Retrieve syllabus metadata and its extracted book records.
    """
    syl = repository.get_syllabus_upload(syllabus_id)
    if not syl:
        raise HTTPException(status_code=404, detail="Syllabus not found.")

    books = repository.get_extracted_books(syllabus_id)

    return SyllabusUploadResponse(
        syllabus_id=syl["id"],
        filename=syl["filename"],
        file_type=syl["file_type"],
        file_size_bytes=syl["file_size_bytes"],
        page_count=syl["page_count"],
        university=syl.get("university"),
        department=syl.get("department"),
        programme=syl.get("programme"),
        semester=syl.get("semester"),
        academic_year=syl.get("academic_year"),
        extracted_subjects=syl["extracted_subjects"],
        books=books,
        total_extracted=len(books),
        status=syl["status"]
    )


@router.get("/{syllabus_id}/subjects", response_model=SyllabusSubjectsResponse)
async def get_syllabus_subjects(syllabus_id: str):
    """
    Retrieve subjects grouped with their respective textbooks and reference books separately.
    Enables subject-level interactive exploration and targeted reference acquisition.
    """
    syl = repository.get_syllabus_upload(syllabus_id)
    if not syl:
        raise HTTPException(status_code=404, detail="Syllabus not found.")

    books = repository.get_extracted_books(syllabus_id)

    # Group books by subject
    subjects_map = {}

    for subj_name in syl.get("extracted_subjects", []):
        subjects_map[subj_name] = {
            "subject_name": subj_name,
            "subject_code": None,
            "textbooks": [],
            "reference_books": [],
            "suggested_readings": [],
            "total_books": 0
        }

    for b in books:
        subj_name = b.subject or "General Syllabus Reading"
        if subj_name not in subjects_map:
            subjects_map[subj_name] = {
                "subject_name": subj_name,
                "subject_code": b.subject_code,
                "textbooks": [],
                "reference_books": [],
                "suggested_readings": [],
                "total_books": 0
            }

        if b.subject_code and not subjects_map[subj_name]["subject_code"]:
            subjects_map[subj_name]["subject_code"] = b.subject_code

        if b.book_type == BookType.TEXTBOOK:
            subjects_map[subj_name]["textbooks"].append(b)
        elif b.book_type == BookType.REFERENCE:
            subjects_map[subj_name]["reference_books"].append(b)
        else:
            subjects_map[subj_name]["suggested_readings"].append(b)

        subjects_map[subj_name]["total_books"] += 1

    group_list = [
        SubjectBooksGroup(
            subject_name=v["subject_name"],
            subject_code=v["subject_code"],
            textbooks=v["textbooks"],
            reference_books=v["reference_books"],
            suggested_readings=v["suggested_readings"],
            total_books=v["total_books"]
        )
        for v in subjects_map.values()
    ]

    return SyllabusSubjectsResponse(
        syllabus_id=syl["id"],
        university=syl.get("university"),
        department=syl.get("department"),
        programme=syl.get("programme"),
        semester=syl.get("semester"),
        academic_year=syl.get("academic_year"),
        subjects=group_list,
        total_subjects=len(group_list)
    )


@router.put("/{syllabus_id}/books", response_model=List[ExtractedBookRecord])
async def update_syllabus_books(syllabus_id: str, request: SyllabusUpdateRequest):
    """
    Update or correct the list of extracted books for a syllabus.
    Allows user review, edition/author corrections, and checkbox selections.
    """
    syl = repository.get_syllabus_upload(syllabus_id)
    if not syl:
        raise HTTPException(status_code=404, detail="Syllabus not found.")

    # Validate that all books belong to this syllabus
    for b in request.books:
        b.syllabus_id = syllabus_id

    repository.update_extracted_books(syllabus_id, request.books)
    return repository.get_extracted_books(syllabus_id)


@router.post("/{syllabus_id}/books", response_model=ExtractedBookRecord)
async def add_syllabus_book(syllabus_id: str, book: ExtractedBookRecord):
    """
    Manually add a book entry to the extracted list.
    """
    syl = repository.get_syllabus_upload(syllabus_id)
    if not syl:
        raise HTTPException(status_code=404, detail="Syllabus not found.")

    book.syllabus_id = syllabus_id
    if not book.id:
        book.id = f"book_{uuid.uuid4().hex[:10]}"

    repository.add_extracted_book(book)
    return book


@router.delete("/{syllabus_id}/books/{book_id}")
async def delete_syllabus_book(syllabus_id: str, book_id: str):
    """
    Delete an extracted book from the syllabus.
    """
    repository.delete_extracted_book(book_id)
    return {"message": f"Extracted book '{book_id}' removed."}
