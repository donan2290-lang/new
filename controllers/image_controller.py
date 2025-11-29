"""
Image Tools Controller
Handles all image manipulation operations:
- Format conversion (JPG, PNG, WebP)
- Remove background
- Remove watermark
- Remove object
- Enhance image
- Upscale image
- Restore photo
- Fix blur
- Colorize photo
- Resize image
- Compress image
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

# Import image processing libraries
try:
    from PIL import Image, ImageEnhance, ImageFilter
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Create Blueprint
image_bp = Blueprint('image', __name__, url_prefix='/api/image')

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def generate_unique_filename(original_filename, suffix=''):
    """Generate unique filename"""
    name, ext = os.path.splitext(original_filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    if suffix:
        return f"{name}_{suffix}_{timestamp}_{unique_id}{ext}"
    return f"{name}_{timestamp}_{unique_id}{ext}"

# ==================== JPG to PNG ====================
@image_bp.route('/jpg-to-png', methods=['POST'])
def jpg_to_png():
    """Convert JPG to PNG"""
    if not PIL_AVAILABLE:
        return jsonify({'success': False, 'error': 'PIL not available'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        # Convert to PNG
        img = Image.open(input_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        output_filename = filename.rsplit('.', 1)[0] + '.png'
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename, 'converted'))
        img.save(output_path, 'PNG', optimize=True)
        
        # Cleanup
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== PNG to JPG ====================
@image_bp.route('/png-to-jpg', methods=['POST'])
def png_to_jpg():
    """Convert PNG to JPG"""
    if not PIL_AVAILABLE:
        return jsonify({'success': False, 'error': 'PIL not available'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        # Convert to JPG
        img = Image.open(input_path)
        
        # Handle transparency
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        output_filename = filename.rsplit('.', 1)[0] + '.jpg'
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename, 'converted'))
        img.save(output_path, 'JPEG', quality=95, optimize=True)
        
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True, mimetype='image/jpeg')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WebP to JPG ====================
@image_bp.route('/webp-to-jpg', methods=['POST'])
def webp_to_jpg():
    """Convert WebP to JPG"""
    if not PIL_AVAILABLE:
        return jsonify({'success': False, 'error': 'PIL not available'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        # Convert WebP to JPG
        img = Image.open(input_path)
        
        # Handle transparency
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        output_filename = filename.rsplit('.', 1)[0] + '.jpg'
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename, 'converted'))
        img.save(output_path, 'JPEG', quality=95, optimize=True)
        
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True, mimetype='image/jpeg')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Remove Background ====================
@image_bp.route('/remove-background', methods=['POST'])
def remove_background():
    """Remove background from image using AI"""
    if not REMBG_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Background removal not available. Install rembg library.'
        }), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        # Remove background
        with open(input_path, 'rb') as i:
            input_data = i.read()
            output_data = rembg_remove(input_data)
        
        output_filename = filename.rsplit('.', 1)[0] + '_no_bg.png'
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename))
        
        with open(output_path, 'wb') as o:
            o.write(output_data)
        
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Resize Image ====================
@image_bp.route('/resize', methods=['POST'])
def resize_image():
    """Resize image to specified dimensions"""
    if not PIL_AVAILABLE:
        return jsonify({'success': False, 'error': 'PIL not available'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        width = request.form.get('width', type=int)
        height = request.form.get('height', type=int)
        maintain_aspect = request.form.get('maintain_aspect', 'true').lower() == 'true'
        
        if not width and not height:
            return jsonify({'success': False, 'error': 'Width or height required'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        img = Image.open(input_path)
        original_width, original_height = img.size
        
        # Calculate new dimensions
        if maintain_aspect:
            if width and not height:
                height = int(original_height * (width / original_width))
            elif height and not width:
                width = int(original_width * (height / original_height))
            else:
                # Both provided, use smaller ratio
                ratio = min(width / original_width, height / original_height)
                width = int(original_width * ratio)
                height = int(original_height * ratio)
        else:
            width = width or original_width
            height = height or original_height
        
        # Resize
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        output_filename = f"{filename.rsplit('.', 1)[0]}_resized.{filename.rsplit('.', 1)[1]}"
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename))
        resized_img.save(output_path, quality=95, optimize=True)
        
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Compress Image ====================
@image_bp.route('/compress', methods=['POST'])
def compress_image():
    """Compress image file size"""
    if not PIL_AVAILABLE:
        return jsonify({'success': False, 'error': 'PIL not available'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        quality = request.form.get('quality', 85, type=int)
        quality = max(10, min(100, quality))  # Clamp between 10-100
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        img = Image.open(input_path)
        
        # Convert RGBA to RGB for JPEG
        if img.mode == 'RGBA' and filename.lower().endswith(('.jpg', '.jpeg')):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        output_filename = f"{filename.rsplit('.', 1)[0]}_compressed.{filename.rsplit('.', 1)[1]}"
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename))
        
        # Save with compression
        save_kwargs = {'optimize': True}
        if filename.lower().endswith(('.jpg', '.jpeg')):
            save_kwargs['quality'] = quality
        
        img.save(output_path, **save_kwargs)
        
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Enhance Image ====================
@image_bp.route('/enhance', methods=['POST'])
def enhance_image():
    """Enhance image quality (brightness, contrast, sharpness)"""
    if not PIL_AVAILABLE:
        return jsonify({'success': False, 'error': 'PIL not available'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        brightness = request.form.get('brightness', 1.2, type=float)
        contrast = request.form.get('contrast', 1.2, type=float)
        sharpness = request.form.get('sharpness', 1.5, type=float)
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, generate_unique_filename(filename))
        file.save(input_path)
        
        img = Image.open(input_path)
        
        # Apply enhancements
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpness)
        
        output_filename = f"{filename.rsplit('.', 1)[0]}_enhanced.{filename.rsplit('.', 1)[1]}"
        output_path = os.path.join(OUTPUT_FOLDER, generate_unique_filename(output_filename))
        img.save(output_path, quality=95, optimize=True)
        
        os.remove(input_path)
        
        return send_file(output_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Placeholder for AI Features ====================
@image_bp.route('/remove-watermark', methods=['POST'])
def remove_watermark():
    """Remove watermark (requires AI model)"""
    return jsonify({
        'success': False,
        'error': 'Watermark removal requires AI model. Coming soon!'
    }), 501

@image_bp.route('/remove-object', methods=['POST'])
def remove_object():
    """Remove object (requires AI model)"""
    return jsonify({
        'success': False,
        'error': 'Object removal requires AI model. Coming soon!'
    }), 501

@image_bp.route('/upscale', methods=['POST'])
def upscale_image():
    """Upscale image (requires AI model)"""
    return jsonify({
        'success': False,
        'error': 'Image upscaling requires AI model. Coming soon!'
    }), 501

@image_bp.route('/restore', methods=['POST'])
def restore_photo():
    """Restore old photo (requires AI model)"""
    return jsonify({
        'success': False,
        'error': 'Photo restoration requires AI model. Coming soon!'
    }), 501

@image_bp.route('/fix-blur', methods=['POST'])
def fix_blur():
    """Fix blurry image (requires AI model)"""
    return jsonify({
        'success': False,
        'error': 'Blur fixing requires AI model. Coming soon!'
    }), 501

@image_bp.route('/colorize', methods=['POST'])
def colorize_photo():
    """Colorize black and white photo (requires AI model)"""
    return jsonify({
        'success': False,
        'error': 'Photo colorization requires AI model. Coming soon!'
    }), 501

# ==================== Health Check ====================
@image_bp.route('/health', methods=['GET'])
def health_check():
    """Check which image libraries are available"""
    return jsonify({
        'success': True,
        'libraries': {
            'pillow': PIL_AVAILABLE,
            'rembg': REMBG_AVAILABLE,
            'opencv': CV2_AVAILABLE
        }
    })
