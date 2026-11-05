import logging
from typing import Optional
from fastapi import APIRouter, Query

from app.schemas import AcquisitionHistoryResponse
from app.db.repository import repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Acquisition History & Audit"])


@router.get("/history", response_model=AcquisitionHistoryResponse)
async def get_acquisition_history(
    record_type: Optional[str] = Query(default=None, description="Filter by 'SEARCH', 'APPROVAL', or 'DOWNLOAD'"),
    status: Optional[str] = Query(default=None, description="Filter by status (e.g. 'COMPLETED', 'ACTIVE', 'EXPIRED')"),
    limit: int = Query(default=100, ge=1, le=500, description="Max records to return")
):
    """
    Retrieve unified, immutable audit history across all real discovery searches,
    human licensing approvals, and authorized file acquisition downloads.
    """
    records = repository.get_acquisition_history(
        record_type=record_type,
        status=status,
        limit=limit
    )

    return AcquisitionHistoryResponse(
        total_records=len(records),
        records=records
    )
