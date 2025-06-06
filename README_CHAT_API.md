# Chat Interface API

A comprehensive, modular FastAPI-based chat interface with user management, conversation handling, message storage, and file upload capabilities.

## 🚀 Features

- **User Management**: Create and manage users with unique usernames and emails
- **Conversation Management**: Create, list, retrieve, and delete conversations
- **Message Handling**: Send messages, store conversation history, and retrieve chat logs
- **AI Integration**: Built-in LLM integration for AI responses
- **File Upload**: Upload files with automatic type detection and validation
- **Modular Design**: Clean, scalable architecture following KISS principles
- **Comprehensive Testing**: Full test suite for all components
- **SQLite Database**: Lightweight, file-based database with proper relations

## 📁 Project Structure

```
├── api.py                 # Main FastAPI application
├── models.py             # Database models and DatabaseManager
├── schemas.py            # Pydantic schemas for validation
├── file_utils.py         # File management with type detection
├── test_chat_api.py      # Comprehensive test suite
├── demo_api_usage.py     # API usage demonstration
├── llm.py                # LLM integration (existing)
├── database.db           # SQLite database
├── uploads/              # File upload directory (auto-created)
└── requirements.txt      # Dependencies
```

## 🛠️ Installation

1. **Activate your virtual environment**:
   ```bash
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest python-magic-bin python-multipart requests
   ```

3. **Run tests** (optional but recommended):
   ```bash
   python test_chat_api.py
   ```

4. **Start the API server**:
   ```bash
   python api.py
   ```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints Overview

#### Health & Info
- `GET /` - Root endpoint with API info
- `GET /health` - Health check endpoint

#### User Management
- `POST /users` - Create a new user
- `GET /users/{user_id}` - Get user by ID
- `GET /users/username/{username}` - Get user by username

#### Conversation Management
- `POST /conversations?user_id={user_id}` - Create new conversation
- `GET /users/{user_id}/conversations` - Get all user conversations
- `GET /conversations/{conversation_id}` - Get conversation details
- `DELETE /conversations/{conversation_id}` - Delete conversation

#### Message Management
- `GET /conversations/{conversation_id}/messages` - Get conversation history
- `POST /conversations/{conversation_id}/messages` - Add message to conversation

#### Chat Interface
- `POST /chat` - Main chat endpoint (handles AI responses)

#### File Management
- `POST /upload` - Upload file with type detection
- `GET /files/{file_id}` - Get file information

## 🔧 Usage Examples

### 1. Create a User
```python
import requests

response = requests.post("http://localhost:8000/users", json={
    "username": "john_doe",
    "email": "john@example.com"
})
user = response.json()
user_id = user["id"]
```

### 2. Start a Chat Conversation
```python
response = requests.post("http://localhost:8000/chat", json={
    "message": "Hello! How can you help me?",
    "user_id": user_id
})
chat_data = response.json()
conversation_id = chat_data["conversation"]["id"]
```

### 3. Continue the Conversation
```python
response = requests.post("http://localhost:8000/chat", json={
    "message": "Tell me about the weather",
    "user_id": user_id,
    "conversation_id": conversation_id
})
```

### 4. Get Conversation History
```python
response = requests.get(f"http://localhost:8000/conversations/{conversation_id}/messages")
history = response.json()
```

### 5. Upload a File
```python
files = {'file': ('document.txt', open('document.txt', 'rb'), 'text/plain')}
response = requests.post("http://localhost:8000/upload", files=files)
file_info = response.json()
```

## 🗄️ Database Schema

The API uses SQLite with the following tables:

### Users
- `id` (Primary Key)
- `username` (Unique)
- `email` (Unique)
- `created_at`

### Conversations
- `id` (Primary Key)
- `user_id` (Foreign Key)
- `title`
- `created_at`
- `updated_at`

### Messages
- `id` (Primary Key)
- `conversation_id` (Foreign Key)
- `content`
- `role` ('user' or 'assistant')
- `created_at`
- `file_id` (Optional Foreign Key)

### Uploaded Files
- `id` (Primary Key)
- `filename`
- `file_type`
- `file_size`
- `file_path`
- `uploaded_at`

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_chat_api.py
```

The tests cover:
- ✅ Database operations (users, conversations, messages, files)
- ✅ File management and type detection
- ✅ API endpoints functionality
- ✅ Error handling and validation
- ✅ Integration testing

## 🎯 Demo

Run the interactive demo to see all features:

```bash
python demo_api_usage.py
```

This will demonstrate:
1. Health check
2. User creation
3. Chat conversations
4. Message management
5. File uploads
6. All CRUD operations

## 🔒 Security Features

- **Input Validation**: Pydantic schemas validate all inputs
- **File Type Detection**: Multiple methods for secure file type detection
- **File Size Limits**: Configurable maximum file size (default: 10MB)
- **SQL Injection Protection**: Parameterized queries
- **Error Handling**: Comprehensive error responses

## ⚙️ Configuration

### File Upload Settings
Modify in `file_utils.py`:
```python
# Maximum file size (bytes)
self.max_file_size = 10 * 1024 * 1024  # 10MB

# Allowed file types
self.allowed_types = {
    'text': ['.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml'],
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
    'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'],
    # ...
}
```

### Database Settings
Modify in `models.py`:
```python
# Database path
db_manager = DatabaseManager("database.db")  # Change path as needed
```

## 📖 API Documentation (Interactive)

When the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔧 Troubleshooting

### Common Issues

1. **Module not found errors**:
   ```bash
   pip install -r requirements.txt
   pip install pytest python-magic-bin python-multipart requests
   ```

2. **Database permission errors**:
   - Ensure the directory is writable
   - Check if database.db is not locked by another process

3. **File upload issues**:
   - Verify `uploads/` directory exists and is writable
   - Check file size limits

4. **LLM authentication errors**:
   - This is expected if OpenRouter API credentials are not configured
   - The chat interface will still work, storing all messages

### Debug Mode

Enable debug logging by setting environment variables:
```bash
export DEBUG=1  # Linux/Mac
set DEBUG=1     # Windows
```

## 🚀 Production Deployment

For production deployment, consider:

1. **Use a production ASGI server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker api:app
   ```

2. **Environment configuration**:
   ```bash
   export DATABASE_URL="postgresql://..."  # If using PostgreSQL
   export SECRET_KEY="your-secret-key"
   export DEBUG=False
   ```

3. **Security headers and HTTPS**
4. **Database migrations and backups**
5. **Monitoring and logging**

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## 📄 License

This project is part of a larger chatbot RAG + tool calling system.

---

**Built with ❤️ using FastAPI, SQLite, and modern Python practices** 