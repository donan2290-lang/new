// ========================================
// HAMBURGER MENU FUNCTIONALITY
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.getElementById('hamburgerBtn');
    const nav = document.getElementById('mainNav');
    const overlay = document.getElementById('navOverlay');
    const closeBtn = document.getElementById('closeNavBtn');
    const body = document.body;
    
    // Check if all required elements exist
    if (!hamburger || !nav || !overlay) {
        console.warn('Hamburger menu elements not found');
        return;
    }
    
    function openMenu() {
        nav.classList.add('active');
        overlay.classList.add('active');
        hamburger.classList.add('active');
        body.classList.add('menu-open');
        hamburger.setAttribute('aria-expanded', 'true');
    }
    
    function closeMenu() {
        nav.classList.remove('active');
        overlay.classList.remove('active');
        hamburger.classList.remove('active');
        body.classList.remove('menu-open');
        hamburger.setAttribute('aria-expanded', 'false');
    }
    
    hamburger.addEventListener('click', function() {
        if (nav.classList.contains('active')) {
            closeMenu();
        } else {
            openMenu();
        }
    });
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMenu);
    }
    
    overlay.addEventListener('click', closeMenu);
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && nav.classList.contains('active')) {
            closeMenu();
        }
    });
    
    const navLinks = nav.querySelectorAll('a');
    if (navLinks.length > 0) {
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    closeMenu();
                }
            });
        });
    }
    
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth > 768 && nav.classList.contains('active')) {
                closeMenu();
            }
        }, 250);
    });
});

// ========================================
// IMAGE CONVERTER FUNCTIONALITY
// ========================================

// Get current conversion type from page
window.currentConversionType = window.IMAGE_CONVERTER_TOOL_TYPE || '';

console.log('Image Converter Loaded - Tool Type:', window.currentConversionType);

// Setup drag & drop after DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    if (!uploadArea || !fileInput) {
        console.warn('Upload area or file input not found');
        return;
    }
    
    console.log('Setting up drag & drop for upload area');
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight drop area when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight(e) {
        uploadArea.classList.add('dragover');
        uploadArea.style.background = 'linear-gradient(135deg, #667eea20 0%, #764ba220 100%)';
        uploadArea.style.borderColor = '#667eea';
        console.log('Drag over - highlighted');
    }
    
    function unhighlight(e) {
        uploadArea.classList.remove('dragover');
        uploadArea.style.background = '#fafafa';
        uploadArea.style.borderColor = '#e0e0e0';
        console.log('Drag leave - unhighlighted');
    }
    
    // Handle dropped files
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        console.log('Drop event triggered');
        const dt = e.dataTransfer;
        const files = dt.files;
        
        console.log('Files dropped:', files.length);
        
        if (files.length > 0) {
            // Assign files to input element
            fileInput.files = files;
            // Trigger file select handler
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    }
    
    // Add click handler for upload area
    uploadArea.addEventListener('click', function(e) {
        // Don't trigger if clicking the button itself
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            return;
        }
        fileInput.click();
    });
    
    // File input change handler
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        console.log('File selected:', file ? file.name : 'none');
        
        if (file) {
            handleFileSelect(file);
        }
    });
});

function handleFileSelect(file) {
    console.log('Handling file:', file.name, file.type, file.size);
    
    const uploadArea = document.getElementById('uploadArea');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const previewImg = document.getElementById('previewImg');
    
    // Hide upload area
    if (uploadArea) uploadArea.style.display = 'none';
    
    // Show preview
    if (filePreview) filePreview.style.display = 'block';
    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = formatFileSize(file.size);
    
    // Show image preview
    if (previewImg && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
    
    // Auto convert after a short delay
    setTimeout(() => {
        convertFile();
    }, 500);
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
    else return (bytes / 1048576).toFixed(2) + ' MB';
}

function convertFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        console.error('No file selected');
        showError('Please select a file');
        return;
    }
    
    console.log('Converting file:', file.name, 'Type:', window.currentConversionType);
    
    const filePreview = document.getElementById('filePreview');
    const loading = document.getElementById('loading');
    const progressFill = document.getElementById('progressFill');
    
    if (filePreview) filePreview.style.display = 'none';
    if (loading) loading.style.display = 'block';
    
    const formData = new FormData();
    formData.append('file', file);
    
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 10;
        if (progressFill) progressFill.style.width = progress + '%';
        if (progress >= 90) clearInterval(progressInterval);
    }, 200);
    
    // Determine endpoint based on conversion type
    const endpoints = {
        'jpg-to-png': '/api/image/jpg-to-png',
        'png-to-jpg': '/api/image/png-to-jpg',
        'webp-to-jpg': '/api/image/webp-to-jpg'
    };
    
    const endpoint = endpoints[window.currentConversionType];
    console.log('Using endpoint:', endpoint);
    
    fetch(endpoint, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        clearInterval(progressInterval);
        if (progressFill) progressFill.style.width = '100%';
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Conversion failed');
            });
        }
        return response.blob();
    })
    .then(blob => {
        console.log('Conversion successful, blob size:', blob.size);
        
        if (loading) loading.style.display = 'none';
        const result = document.getElementById('result');
        if (result) result.style.display = 'block';
        
        const url = window.URL.createObjectURL(blob);
        const downloadLink = document.getElementById('downloadLink');
        
        if (downloadLink) {
            downloadLink.href = url;
            
            const extensions = {
                'jpg-to-png': 'png',
                'png-to-jpg': 'jpg',
                'webp-to-jpg': 'jpg'
            };
            
            const originalName = file.name.split('.')[0];
            const newExt = extensions[window.currentConversionType] || 'jpg';
            downloadLink.download = `converted_${originalName}.${newExt}`;
            
            // Add auto-refresh after download
            downloadLink.addEventListener('click', function() {
                setTimeout(function() {
                    location.reload();
                }, 1000);
            });
        }
    })
    .catch(error => {
        console.error('Conversion error:', error);
        clearInterval(progressInterval);
        if (loading) loading.style.display = 'none';
        showError(error.message);
    });
}

function showError(message) {
    const filePreview = document.getElementById('filePreview');
    const error = document.getElementById('error');
    const errorP = error ? error.querySelector('p') : null;
    
    if (filePreview) filePreview.style.display = 'none';
    if (error) error.style.display = 'block';
    if (errorP) errorP.textContent = message;
}

function removeFile() {
    resetConverter();
}

function resetConverter() {
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const error = document.getElementById('error');
    const uploadArea = document.getElementById('uploadArea');
    const progressFill = document.getElementById('progressFill');
    
    if (fileInput) fileInput.value = '';
    if (filePreview) filePreview.style.display = 'none';
    if (loading) loading.style.display = 'none';
    if (result) result.style.display = 'none';
    if (error) error.style.display = 'none';
    if (uploadArea) uploadArea.style.display = 'block';
    if (progressFill) progressFill.style.width = '0%';
    
    console.log('Converter reset');
}
