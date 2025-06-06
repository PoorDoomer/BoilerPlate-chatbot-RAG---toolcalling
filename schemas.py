from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# User schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username must be 3-50 characters")
    email: str = Field(..., description="Valid email address")

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str

# Conversation schemas
class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Conversation title")

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: str
    updated_at: str

class ConversationList(BaseModel):
    conversations: List[ConversationResponse]
    total: int

# Message schemas
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Message content cannot be empty")
    file_id: Optional[int] = Field(None, description="Optional file attachment ID")

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    role: str
    created_at: str
    file_id: Optional[int] = None

class ConversationHistory(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]

# Chat request schema
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Chat message content")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID, or None for new conversation")
    user_id: int = Field(..., description="User ID for the chat")

class ChatResponse(BaseModel):
    message: MessageResponse
    assistant_response: MessageResponse
    conversation: ConversationResponse

# File upload schemas
class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    uploaded_at: str

# Error response schema
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

# Success response schema
class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None 