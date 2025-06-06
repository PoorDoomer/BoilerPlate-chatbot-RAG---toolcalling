import sqlite3
import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class User:
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    created_at: Optional[str] = None
    
@dataclass
class Conversation:
    id: Optional[int] = None
    user_id: int = 0
    title: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Message:
    id: Optional[int] = None
    conversation_id: int = 0
    content: str = ""
    role: str = "user"  # "user" or "assistant"
    created_at: Optional[str] = None
    file_id: Optional[int] = None

@dataclass
class UploadedFile:
    id: Optional[int] = None
    filename: str = ""
    file_type: str = ""
    file_size: int = 0
    file_path: str = ""
    uploaded_at: Optional[str] = None

class DatabaseManager:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection with row factory for dict-like access"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_id INTEGER,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
                    FOREIGN KEY (file_id) REFERENCES uploaded_files (id) ON DELETE SET NULL
                )
            """)
            
            # Uploaded files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            print("[DEBUG] Database tables initialized successfully")

    # User operations
    def create_user(self, username: str, email: str) -> Optional[User]:
        """Create a new user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email) VALUES (?, ?)",
                    (username, email)
                )
                user_id = cursor.lastrowid
                conn.commit()
                
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return User(id=row['id'], username=row['username'], 
                               email=row['email'], created_at=row['created_at'])
        except sqlite3.IntegrityError as e:
            print(f"[DEBUG] Error creating user: {e}")
            return None
        except Exception as e:
            print(f"[DEBUG] Unexpected error creating user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return User(id=row['id'], username=row['username'], 
                           email=row['email'], created_at=row['created_at'])
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return User(id=row['id'], username=row['username'], 
                           email=row['email'], created_at=row['created_at'])
        return None

    # Conversation operations
    def create_conversation(self, user_id: int, title: str) -> Optional[Conversation]:
        """Create a new conversation"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                    (user_id, title)
                )
                conversation_id = cursor.lastrowid
                conn.commit()
                
                # Fetch the created conversation
                cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
                row = cursor.fetchone()
                if row:
                    return Conversation(id=row['id'], user_id=row['user_id'], 
                                      title=row['title'], created_at=row['created_at'],
                                      updated_at=row['updated_at'])
        except Exception as e:
            print(f"[DEBUG] Error creating conversation: {e}")
            return None
    
    def get_user_conversations(self, user_id: int) -> List[Conversation]:
        """Get all conversations for a user"""
        conversations = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            for row in rows:
                conversations.append(Conversation(
                    id=row['id'], user_id=row['user_id'], title=row['title'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                ))
        return conversations
    
    def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            if row:
                return Conversation(id=row['id'], user_id=row['user_id'], 
                                  title=row['title'], created_at=row['created_at'],
                                  updated_at=row['updated_at'])
        return None
    
    def update_conversation_timestamp(self, conversation_id: int):
        """Update conversation's updated_at timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )
            conn.commit()
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[DEBUG] Error deleting conversation: {e}")
            return False

    # Message operations
    def create_message(self, conversation_id: int, content: str, role: str = "user", 
                      file_id: Optional[int] = None) -> Optional[Message]:
        """Create a new message"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (conversation_id, content, role, file_id) VALUES (?, ?, ?, ?)",
                    (conversation_id, content, role, file_id)
                )
                message_id = cursor.lastrowid
                conn.commit()
                
                # Update conversation timestamp
                self.update_conversation_timestamp(conversation_id)
                
                # Fetch the created message
                cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
                row = cursor.fetchone()
                if row:
                    return Message(id=row['id'], conversation_id=row['conversation_id'],
                                 content=row['content'], role=row['role'],
                                 created_at=row['created_at'], file_id=row['file_id'])
        except Exception as e:
            print(f"[DEBUG] Error creating message: {e}")
            return None
    
    def get_conversation_messages(self, conversation_id: int) -> List[Message]:
        """Get all messages for a conversation"""
        messages = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,)
            )
            rows = cursor.fetchall()
            for row in rows:
                messages.append(Message(
                    id=row['id'], conversation_id=row['conversation_id'],
                    content=row['content'], role=row['role'],
                    created_at=row['created_at'], file_id=row['file_id']
                ))
        return messages

    # File operations
    def create_uploaded_file(self, filename: str, file_type: str, 
                           file_size: int, file_path: str) -> Optional[UploadedFile]:
        """Create a new uploaded file record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO uploaded_files (filename, file_type, file_size, file_path) VALUES (?, ?, ?, ?)",
                    (filename, file_type, file_size, file_path)
                )
                file_id = cursor.lastrowid
                conn.commit()
                
                # Fetch the created file record
                cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
                row = cursor.fetchone()
                if row:
                    return UploadedFile(id=row['id'], filename=row['filename'],
                                      file_type=row['file_type'], file_size=row['file_size'],
                                      file_path=row['file_path'], uploaded_at=row['uploaded_at'])
        except Exception as e:
            print(f"[DEBUG] Error creating file record: {e}")
            return None
    
    def get_file_by_id(self, file_id: int) -> Optional[UploadedFile]:
        """Get uploaded file by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if row:
                return UploadedFile(id=row['id'], filename=row['filename'],
                                  file_type=row['file_type'], file_size=row['file_size'],
                                  file_path=row['file_path'], uploaded_at=row['uploaded_at'])
        return None 