// ========================================
// HAMBURGER MENU FUNCTIONALITY
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    // Page-level UI initialization (tools grid, tabs, hero headings)
    const toolType = window.PDF_CONVERTER_TOOL_TYPE || '';

    // Hide all categories first
    try {
        document.querySelectorAll('.tools-category').forEach(cat => {
            cat.classList.remove('active-category');
            if (cat.style) cat.style.display = 'none';
        });

        // Show Convert PDF category by default
        const convertPdfCategory = document.querySelector('.tools-category[data-category="convert-pdf"]');
        if (convertPdfCategory) {
            convertPdfCategory.classList.add('active-category');
            convertPdfCategory.style.display = 'block';
        }

        // Set Convert PDF tab as active
        document.querySelectorAll('.tool-tab').forEach(t => t.classList.remove('active'));
        const convertPdfTab = document.querySelector('.tool-tab[data-category="convert-pdf"]');
        if (convertPdfTab) convertPdfTab.classList.add('active');

        // Helper to update file type hint
        function updateFileTypeHintLocal(type) {
            const hints = {
                'pdf-to-word': 'Supported format: PDF',
                'word-to-pdf': 'Supported format: DOCX, DOC',
                'pdf-to-excel': 'Supported format: PDF',
                'excel-to-pdf': 'Supported format: XLSX, XLS',
                'pdf-to-ppt': 'Supported format: PDF',
                'ppt-to-pdf': 'Supported format: PPTX, PPT',
                'pdf-to-jpg': 'Supported format: PDF',
                'jpg-to-pdf': 'Supported format: JPG, JPEG',
                'pdf-to-png': 'Supported format: PDF',
                'png-to-pdf': 'Supported format: PNG',
                'merge-pdf': 'Supported format: PDF (multiple files)',
                'split-pdf': 'Supported format: PDF',
                'compress-pdf': 'Supported format: PDF'
            };
            const hintElement = document.getElementById('fileTypeHint');
            if (hintElement) hintElement.textContent = hints[type] || '';
        }

        if (toolType && toolType !== 'None' && toolType !== '') {
            window.currentConversionType = toolType;
            updateFileTypeHintLocal(toolType);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    } catch (e) {
        // DOM might not contain tools UI on other pages; ignore errors
        console.debug('PDF converter UI init skipped:', e && e.message);
    }
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
// PDF CONVERTER FUNCTIONALITY
// ========================================

// Get current conversion type from page
window.currentConversionType = window.PDF_CONVERTER_TOOL_TYPE || '';

console.log('PDF Converter Loaded - Tool Type:', window.currentConversionType);

document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const downloadLink = document.getElementById('downloadLink');
    const progressFill = document.getElementById('progressFill');

    if (!uploadArea || !fileInput) {
        console.warn('Upload area or file input not found');
        return;
    }

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
        uploadArea.addEventListener(eventName, function(e) {
            uploadArea.classList.add('dragover');
            uploadArea.style.background = 'linear-gradient(135deg, #667eea20 0%, #764ba220 100%)';
            uploadArea.style.borderColor = '#667eea';
        }, false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, function(e) {
            uploadArea.classList.remove('dragover');
            uploadArea.style.background = '#fafafa';
            uploadArea.style.borderColor = '#e0e0e0';
        }, false);
    });

    // Handle dropped files
    uploadArea.addEventListener('drop', function(e) {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            // Trigger file select handler
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    }, false);

    // Add click handler for upload area
    uploadArea.addEventListener('click', function(e) {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            return;
        }
        fileInput.click();
    });

    // File input change handler
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Hide upload area, show preview
            uploadArea.style.display = 'none';
            if (filePreview) filePreview.style.display = 'block';
            if (fileName) fileName.textContent = file.name;
            if (fileSize) fileSize.textContent = formatFileSize(file.size);
            // Auto convert after a short delay
            setTimeout(() => convertFile(), 500);
        }
    });

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
        else return (bytes / 1048576).toFixed(2) + ' MB';
    }

    function convertFile() {
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file');
            return;
        }
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
            'pdf-to-word': '/api/pdf/to-word',
            'word-to-pdf': '/api/pdf/from-word',
            'pdf-to-excel': '/api/pdf/to-excel',
            'excel-to-pdf': '/api/pdf/from-excel',
            'pdf-to-ppt': '/api/pdf/to-ppt',
            'ppt-to-pdf': '/api/pdf/from-ppt',
            'pdf-to-jpg': '/api/pdf/to-jpg',
            'jpg-to-pdf': '/api/pdf/from-jpg',
            'pdf-to-png': '/api/pdf/to-png',
            'png-to-pdf': '/api/pdf/from-png',
            'merge-pdf': '/api/pdf/merge',
            'split-pdf': '/api/pdf/split',
            'compress-pdf': '/api/pdf/compress'
        };
        const endpoint = endpoints[window.currentConversionType];

        fetch(endpoint, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            clearInterval(progressInterval);
            if (progressFill) progressFill.style.width = '100%';
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Conversion failed');
                });
            }
            return response.blob();
        })
        .then(blob => {
            if (loading) loading.style.display = 'none';
            if (result) result.style.display = 'block';
            const url = window.URL.createObjectURL(blob);
            if (downloadLink) {
                downloadLink.href = url;
                const extensions = {
                    'pdf-to-word': 'docx',
                    'word-to-pdf': 'pdf',
                    'pdf-to-excel': 'xlsx',
                    'excel-to-pdf': 'pdf',
                    'pdf-to-ppt': 'pptx',
                    'ppt-to-pdf': 'pdf',
                    'pdf-to-jpg': 'zip',
                    'jpg-to-pdf': 'pdf',
                    'pdf-to-png': 'zip',
                    'png-to-pdf': 'pdf',
                    'merge-pdf': 'pdf',
                    'split-pdf': 'zip',
                    'compress-pdf': 'pdf'
                };
                const originalName = file.name.split('.')[0];
                const ext = extensions[window.currentConversionType] || 'pdf';
                downloadLink.download = `converted_${originalName}.${ext}`;
                // Add auto-refresh after download
                downloadLink.addEventListener('click', function() {
                    setTimeout(function() {
                        location.reload();
                    }, 1000);
                });
            }
        })
        .catch(error => {
            clearInterval(progressInterval);
            if (loading) loading.style.display = 'none';
            showError(error.message);
        });
    }

    function showError(message) {
        if (filePreview) filePreview.style.display = 'none';
        const error = document.getElementById('error');
        const errorP = error ? error.querySelector('p') : null;
        if (error) error.style.display = 'block';
        if (errorP) errorP.textContent = message;
    }

    window.removeFile = function() {
        resetConverter();
    }
    window.resetConverter = function() {
        if (fileInput) fileInput.value = '';
        if (filePreview) filePreview.style.display = 'none';
        if (loading) loading.style.display = 'none';
        if (result) result.style.display = 'none';
        const error = document.getElementById('error');
        if (error) error.style.display = 'none';
        if (uploadArea) uploadArea.style.display = 'block';
        if (progressFill) progressFill.style.width = '0%';
    }
});
