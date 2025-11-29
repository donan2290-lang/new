"""
File Validator Utility
Validate uploaded files for security and integrity
"""

import os
import magic  # python-magic
from werkzeug.utils import secure_filename

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    # PDF
    'application/pdf': ['.pdf'],
    
    # Images
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    'image/bmp': ['.bmp'],
    
    # Documents
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    'application/msword': ['.doc'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.ms-powerpoint': ['.ppt'],
}

def validate_file_extension(filename, allowed_extensions):
    """
    Check if file extension is allowed
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions (e.g., {'pdf', 'jpg'})
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions

def validate_file_mime_type(file_path):
    """
    Validate file MIME type matches extension
    
    Args:
        file_path: Path to the file
    
    Returns:
        tuple: (is_valid, mime_type, error_message)
    """
    try:
        # Detect MIME type
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(file_path)
        
        # Get file extension
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check if MIME type is allowed
        if detected_mime not in ALLOWED_MIME_TYPES:
            return False, detected_mime, f"File type not allowed: {detected_mime}"
        
        # Check if extension matches MIME type
        expected_extensions = ALLOWED_MIME_TYPES.get(detected_mime, [])
        if ext not in expected_extensions:
            return False, detected_mime, f"File extension {ext} does not match MIME type {detected_mime}"
        
        return True, detected_mime, None
        
    except Exception as e:
        return False, None, f"Error validating file: {str(e)}"

def validate_file_size(file_path, max_size_mb=50):
    """
    Check if file size is within limits
    
    Args:
        file_path: Path to the file
        max_size_mb: Maximum allowed size in MB
    
    Returns:
        tuple: (is_valid, size_bytes, error_message)
    """
    try:
        size_bytes = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if size_bytes > max_size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            return False, size_bytes, f"File too large: {size_mb:.2f} MB (max: {max_size_mb} MB)"
        
        return True, size_bytes, None
        
    except Exception as e:
        return False, 0, f"Error checking file size: {str(e)}"

def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal and other attacks
    
    Args:
        filename: Original filename
    
    Returns:
        str: Sanitized filename
    """
    # Use werkzeug's secure_filename
    safe_name = secure_filename(filename)
    
    # Additional sanitization
    # Remove any remaining special characters
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '._- ')
    
    # Limit length
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255-len(ext)] + ext
    
    return safe_name

def validate_upload(file, allowed_extensions, max_size_mb=50):
    """
    Complete validation for uploaded file
    
    Args:
        file: Flask file object
        allowed_extensions: Set of allowed extensions
        max_size_mb: Maximum file size in MB
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if file exists
    if not file or file.filename == '':
        return False, "No file provided"
    
    # Validate extension
    if not validate_file_extension(file.filename, allowed_extensions):
        return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
    
    # Save temporarily to validate MIME and size
    temp_path = None
    try:
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp()
        os.close(temp_fd)
        file.save(temp_path)
        
        # Validate MIME type
        is_valid_mime, mime_type, mime_error = validate_file_mime_type(temp_path)
        if not is_valid_mime:
            return False, mime_error
        
        # Validate size
        is_valid_size, size_bytes, size_error = validate_file_size(temp_path, max_size_mb)
        if not is_valid_size:
            return False, size_error
        
        # Reset file pointer for later use
        file.seek(0)
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"
    
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
