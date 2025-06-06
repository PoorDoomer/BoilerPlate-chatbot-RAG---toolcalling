from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional, List
import asyncio

# Import our custom modules
from models import DatabaseManager, User, Conversation, Message, UploadedFile
from schemas import (
    UserCreate, UserResponse, ConversationCreate, ConversationResponse, 
    ConversationList, MessageCreate, MessageResponse, ConversationHistory,
    ChatRequest, ChatResponse, FileUploadResponse, ErrorResponse, SuccessResponse
)
from file_utils import FileManager
from llm import LLM

app = FastAPI(
    title="Chat Interface API",
    description="Comprehensive chat interface with user management, conversations, messages, and file uploads",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize managers
db_manager = DatabaseManager()
file_manager = FileManager()
llm_client = LLM()

# Dependency to get database manager
def get_db():
    return db_manager

# Dependency to get file manager
def get_file_manager():
    return file_manager

# Dependency to get LLM client
def get_llm():
    return llm_client

@app.get("/")
def read_root():
    return {"message": "Chat Interface API is running", "version": "1.0.0"}

# User Management Endpoints
@app.post("/users", response_model=UserResponse, tags=["Users"])
def create_user(user_data: UserCreate, db: DatabaseManager = Depends(get_db)):
    """Create a new user"""
    try:
        user = db.create_user(user_data.username, user_data.email)
        if user:
            return UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                created_at=user.created_at
            )
        else:
            raise HTTPException(status_code=400, detail="User creation failed. Username or email might already exist.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user(user_id: int, db: DatabaseManager = Depends(get_db)):
    """Get user by ID"""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at
    )

@app.get("/users/username/{username}", response_model=UserResponse, tags=["Users"])
def get_user_by_username(username: str, db: DatabaseManager = Depends(get_db)):
    """Get user by username"""
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at
    )

# Conversation Management Endpoints
@app.post("/conversations", response_model=ConversationResponse, tags=["Conversations"])
def create_conversation(conversation_data: ConversationCreate, user_id: int, db: DatabaseManager = Depends(get_db)):
    """Create a new conversation for a user"""
    # Verify user exists
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    conversation = db.create_conversation(user_id, conversation_data.title)
    if not conversation:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )

@app.get("/users/{user_id}/conversations", response_model=ConversationList, tags=["Conversations"])
def get_user_conversations(user_id: int, db: DatabaseManager = Depends(get_db)):
    """Get all conversations for a user"""
    # Verify user exists
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    conversations = db.get_user_conversations(user_id)
    
    conversation_responses = [
        ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        ) for conv in conversations
    ]
    
    return ConversationList(conversations=conversation_responses, total=len(conversation_responses))

@app.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Conversations"])
def get_conversation(conversation_id: int, db: DatabaseManager = Depends(get_db)):
    """Get conversation by ID"""
    conversation = db.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )

@app.delete("/conversations/{conversation_id}", response_model=SuccessResponse, tags=["Conversations"])
def delete_conversation(conversation_id: int, db: DatabaseManager = Depends(get_db)):
    """Delete a conversation and all its messages"""
    # Verify conversation exists
    conversation = db.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    success = db.delete_conversation(conversation_id)
    if success:
        return SuccessResponse(message="Conversation deleted successfully")
    else:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

# Message Management Endpoints
@app.get("/conversations/{conversation_id}/messages", response_model=ConversationHistory, tags=["Messages"])
def get_conversation_history(conversation_id: int, db: DatabaseManager = Depends(get_db)):
    """Get conversation with all its messages"""
    conversation = db.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.get_conversation_messages(conversation_id)
    
    conversation_response = ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )
    
    message_responses = [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            content=msg.content,
            role=msg.role,
            created_at=msg.created_at,
            file_id=msg.file_id
        ) for msg in messages
    ]
    
    return ConversationHistory(conversation=conversation_response, messages=message_responses)

@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, tags=["Messages"])
def create_message(conversation_id: int, message_data: MessageCreate, db: DatabaseManager = Depends(get_db)):
    """Add a message to a conversation"""
    # Verify conversation exists
    conversation = db.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    message = db.create_message(
        conversation_id=conversation_id,
        content=message_data.content,
        role="user",
        file_id=message_data.file_id
    )
    
    if not message:
        raise HTTPException(status_code=500, detail="Failed to create message")
    
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        content=message.content,
        role=message.role,
        created_at=message.created_at,
        file_id=message.file_id
    )

# Chat Endpoint (Main interaction)
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest, db: DatabaseManager = Depends(get_db), llm: LLM = Depends(get_llm)):
    """Main chat endpoint that handles user messages and generates AI responses"""
    try:
        # Verify user exists
        user = db.get_user_by_id(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get or create conversation
        if request.conversation_id:
            conversation = db.get_conversation_by_id(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conversation.user_id != request.user_id:
                raise HTTPException(status_code=403, detail="Access denied to this conversation")
        else:
            # Create new conversation with message as title (truncated)
            title = request.message[:50] + "..." if len(request.message) > 50 else request.message
            conversation = db.create_conversation(request.user_id, title)
            if not conversation:
                raise HTTPException(status_code=500, detail="Failed to create conversation")
        
        # Create user message
        user_message = db.create_message(
            conversation_id=conversation.id,
            content=request.message,
            role="user"
        )
        
        if not user_message:
            raise HTTPException(status_code=500, detail="Failed to create user message")
        
        # Generate AI response using LLM
        try:
            ai_response_content = llm.get_completion(request.message)
            
            # Create assistant message
            assistant_message = db.create_message(
                conversation_id=conversation.id,
                content=ai_response_content,
                role="assistant"
            )
            
            if not assistant_message:
                raise HTTPException(status_code=500, detail="Failed to create assistant message")
        
        except Exception as e:
            # If LLM fails, create a fallback response
            print(f"[DEBUG] LLM failed: {e}")
            assistant_message = db.create_message(
                conversation_id=conversation.id,
                content="I apologize, but I'm experiencing technical difficulties. Please try again later.",
                role="assistant"
            )
        
        # Return response
        return ChatResponse(
            message=MessageResponse(
                id=user_message.id,
                conversation_id=user_message.conversation_id,
                content=user_message.content,
                role=user_message.role,
                created_at=user_message.created_at,
                file_id=user_message.file_id
            ),
            assistant_response=MessageResponse(
                id=assistant_message.id,
                conversation_id=assistant_message.conversation_id,
                content=assistant_message.content,
                role=assistant_message.role,
                created_at=assistant_message.created_at,
                file_id=assistant_message.file_id
            ),
            conversation=ConversationResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# File Upload Endpoints
@app.post("/upload", response_model=FileUploadResponse, tags=["Files"])
async def upload_file(file: UploadFile = File(...), fm: FileManager = Depends(get_file_manager), db: DatabaseManager = Depends(get_db)):
    """Upload a file with type detection"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Save file
        success, file_path, error_msg = fm.save_uploaded_file(file_content, file.filename)
        
        if not success:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Get file info
        file_info = fm.get_file_info(file_path)
        
        # Save file record to database
        uploaded_file = db.create_uploaded_file(
            filename=file_info['filename'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            file_path=file_path
        )
        
        if not uploaded_file:
            # Clean up file if database record creation fails
            fm.delete_file(file_path)
            raise HTTPException(status_code=500, detail="Failed to create file record")
        
        return FileUploadResponse(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            file_type=uploaded_file.file_type,
            file_size=uploaded_file.file_size,
            uploaded_at=uploaded_file.uploaded_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] File upload error: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.get("/files/{file_id}", response_model=FileUploadResponse, tags=["Files"])
def get_file_info(file_id: int, db: DatabaseManager = Depends(get_db)):
    """Get file information by ID"""
    uploaded_file = db.get_file_by_id(file_id)
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileUploadResponse(
        id=uploaded_file.id,
        filename=uploaded_file.filename,
        file_type=uploaded_file.file_type,
        file_size=uploaded_file.file_size,
        uploaded_at=uploaded_file.uploaded_at
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "file_manager": "ready",
        "llm": "ready"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)