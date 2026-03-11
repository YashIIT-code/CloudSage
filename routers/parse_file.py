"""
CloudSage – /api/parse-file router (Root).
Accepts uploaded CSV / JSON files and returns parsed CloudResource list.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
import sys
import os

from models import CloudResource
from services.file_parser import parse_file, validate_file

router = APIRouter()


@router.post("/parse-file", response_model=list[CloudResource])
async def parse_uploaded_file(file: UploadFile = File(...)):
    """Parse an uploaded CSV or JSON into a list of cloud resources."""

    content = await file.read()
    error = validate_file(file.filename or "unknown", len(content))
    if error:
        raise HTTPException(status_code=400, detail=error)

    try:
        resources = parse_file(content, file.filename or "unknown.csv")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}")

    if not resources:
        raise HTTPException(status_code=422, detail="No resources found in file.")

    return resources
