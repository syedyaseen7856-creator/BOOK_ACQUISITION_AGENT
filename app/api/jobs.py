from fastapi import APIRouter, HTTPException, Path
from app.schemas import DownloadJob
from app.db.repository import repository

router = APIRouter(tags=["Download Jobs"])


@router.get("/jobs/{job_id}", response_model=DownloadJob)
async def get_download_job_status(
    job_id: str = Path(..., description="Unique download job identifier")
):
    """
    Return the progress, status, file validation results, and provenance for a download job.
    """
    job = repository.get_download_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Download job '{job_id}' was not found."
        )
    return job
