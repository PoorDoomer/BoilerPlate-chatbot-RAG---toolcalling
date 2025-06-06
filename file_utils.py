import os
import mimetypes
import magic
from typing import Optional, Tuple
from pathlib import Path

class FileManager:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Allowed file types and their extensions
        self.allowed_types = {
            'text': ['.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.go', '.rs']
        }
        
        # Maximum file size (10MB)
        self.max_file_size = 10 * 1024 * 1024
    
    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type using multiple methods
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: Detected file type
        """
        try:
            # Method 1: Use python-magic for MIME type detection
            try:
                mime_type = magic.from_file(file_path, mime=True)
                if mime_type:
                    main_type = mime_type.split('/')[0]
                    if main_type in ['text', 'image', 'audio', 'video', 'application']:
                        return mime_type
            except Exception as e:
                print(f"[DEBUG] Magic detection failed: {e}")
            
            # Method 2: Use mimetypes module
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                return mime_type
            
            # Method 3: File extension based detection
            extension = Path(file_path).suffix.lower()
            for category, extensions in self.allowed_types.items():
                if extension in extensions:
                    return f"{category}/{extension[1:]}"  # Remove the dot
            
            return "application/octet-stream"  # Default binary type
            
        except Exception as e:
            print(f"[DEBUG] File type detection failed: {e}")
            return "unknown/unknown"
    
    def validate_file(self, file_path: str, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file
        
        Args:
            file_path (str): Path to the uploaded file
            filename (str): Original filename
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return False, f"File size ({file_size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)"
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check file extension
            extension = Path(filename).suffix.lower()
            all_allowed_extensions = []
            for extensions in self.allowed_types.values():
                all_allowed_extensions.extend(extensions)
            
            if extension not in all_allowed_extensions:
                return False, f"File type '{extension}' is not allowed. Allowed types: {all_allowed_extensions}"
            
            # Basic file content validation
            try:
                # Try to read first few bytes to ensure file is readable
                with open(file_path, 'rb') as f:
                    first_bytes = f.read(1024)
                    if not first_bytes:
                        return False, "File appears to be corrupted or empty"
            except Exception as e:
                return False, f"Cannot read file: {str(e)}"
            
            return True, None
            
        except Exception as e:
            return False, f"File validation error: {str(e)}"
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Save uploaded file to disk
        
        Args:
            file_content (bytes): File content
            filename (str): Original filename
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, file_path, error_message)
        """
        try:
            # Generate unique filename to avoid conflicts
            base_name = Path(filename).stem
            extension = Path(filename).suffix
            counter = 1
            
            # Find unique filename
            new_filename = filename
            while (self.upload_dir / new_filename).exists():
                new_filename = f"{base_name}_{counter}{extension}"
                counter += 1
            
            file_path = self.upload_dir / new_filename
            
            # Write file content
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Validate the saved file
            is_valid, error_msg = self.validate_file(str(file_path), filename)
            if not is_valid:
                # Remove invalid file
                try:
                    os.remove(file_path)
                except:
                    pass
                return False, None, error_msg
            
            return True, str(file_path), None
            
        except Exception as e:
            return False, None, f"Failed to save file: {str(e)}"
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get comprehensive file information
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            dict: File information
        """
        try:
            path_obj = Path(file_path)
            stats = path_obj.stat()
            
            return {
                'filename': path_obj.name,
                'file_path': str(path_obj),
                'file_size': stats.st_size,
                'file_type': self.detect_file_type(file_path),
                'extension': path_obj.suffix.lower(),
                'created_at': stats.st_ctime,
                'modified_at': stats.st_mtime,
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK)
            }
        except Exception as e:
            return {
                'error': f"Cannot get file info: {str(e)}"
            }
    
    def delete_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a file from disk
        
        Args:
            file_path (str): Path to the file to delete
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True, None
            else:
                return False, "File does not exist"
        except Exception as e:
            return False, f"Failed to delete file: {str(e)}" 