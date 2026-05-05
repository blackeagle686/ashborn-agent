"""
Ashborn Backend — Pydantic request/response schemas.
"""
from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    mode: str = "auto"   # "auto" | "plan" | "fast_ans"


class ToolResult(BaseModel):
    call_id: str
    result: str


class CompletionRequest(BaseModel):
    file_path: str
    content_before: str
    content_after: str


class CodeActionRequest(BaseModel):
    action: str
    file_path: str
    selected_text: str
    full_text: str


class ConfigUpdate(BaseModel):
    settings: dict


class TTSRequest(BaseModel):
    text: str
    lang: str = "en"
