"""Audit and approval models for Book Acquisition Agent.
Re-exports canonical CandidateApprovalRequest and ApprovalRecord from app.schemas.
"""
from app.schemas import CandidateApprovalRequest, ApprovalRecord

__all__ = ["CandidateApprovalRequest", "ApprovalRecord"]
