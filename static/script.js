// ========================================
// HAMBURGER MENU FUNCTIONALITY
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.getElementById('hamburgerBtn');
    const nav = document.getElementById('mainNav');
    const overlay = document.getElementById('navOverlay');
    const closeBtn = document.getElementById('closeNavBtn');
    const body = document.body;
    
    // Open Menu
    function openMenu() {
        nav.classList.add('active');
        overlay.classList.add('active');
        hamburger.classList.add('active');
        body.classList.add('menu-open');
        hamburger.setAttribute('aria-expanded', 'true');
    }
    
    // Close Menu
    function closeMenu() {
        nav.classList.remove('active');
        overlay.classList.remove('active');
        hamburger.classList.remove('active');
        body.classList.remove('menu-open');
        hamburger.setAttribute('aria-expanded', 'false');
    }
    
    // Toggle Menu
    if (hamburger) {
        hamburger.addEventListener('click', function() {
            if (nav.classList.contains('active')) {
                closeMenu();
            } else {
                openMenu();
            }
        });
    }
    
    // Close via Close Button
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMenu);
    }
    
    // Close via Overlay Click
    if (overlay) {
        overlay.addEventListener('click', closeMenu);
    }
    
    // Close on ESC Key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && nav.classList.contains('active')) {
            closeMenu();
        }
    });
    
    // Close menu when clicking nav links (for smooth UX)
    const navLinks = nav.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeMenu();
            }
        });
    });
    
    // Handle Window Resize
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
// VIDEO DOWNLOAD FUNCTIONALITY
// ========================================

async function downloadVideo() {
    const urlInput = document.getElementById('videoUrl');
    const url = urlInput.value.trim();
    
    // Hide previous results/errors
    document.getElementById('result').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    document.getElementById('loading').style.display = 'none';
    
    // Validate URL
    if (!url) {
        showError('Please enter a video URL');
        return;
    }
    
    // Detect platform
    const platform = detectPlatform(url);
    if (!platform) {
        showError('Unsupported platform. Please use YouTube, TikTok, Instagram, Facebook, Twitter/X, Bilibili, Bilibili.tv, or Snack Video links.');
        return;
    }
    
    // Show loading
    document.getElementById('loading').style.display = 'block';
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                platform: platform
            })
        });
        
        const data = await response.json();
        
        document.getElementById('loading').style.display = 'none';
        
        if (response.ok && data.success) {
            displayResults(data, platform);
        } else {
            showError(data.error || 'Failed to process video. Please try again.');
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        showError('Network error. Please check your connection and try again.');
        console.error('Error:', error);
    }
}

function detectPlatform(url) {
    const patterns = {
        youtube: /(?:youtube\.com|youtu\.be)/i,
        facebook: /facebook\.com/i,
        instagram: /instagram\.com/i,
        tiktok: /tiktok\.com/i,
        twitter: /(?:twitter\.com|x\.com|t\.co)/i,
        bilibili_tv: /bilibili\.tv/i,  // Check bilibili.tv FIRST
        bilibili: /bilibili\.com/i,     // Then bilibili.com
        snackvideo: /snackvideo\.com/i
    };
    
    for (const [platform, pattern] of Object.entries(patterns)) {
        if (pattern.test(url)) {
            return platform;
        }
    }
    
    return null;
}

function displayResults(data, platform) {
    const resultDiv = document.getElementById('result');
    const thumbnail = document.getElementById('thumbnail');
    const title = document.getElementById('title');
    const duration = document.getElementById('duration');
    const downloadOptions = document.getElementById('downloadOptions');
    
    // Set video info with proxied thumbnail for Instagram/Facebook
    let thumbnailUrl = data.thumbnail || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="112"%3E%3Crect width="200" height="112" fill="%23ccc"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%23666"%3ENo Thumbnail%3C/text%3E%3C/svg%3E';
    
    // Use proxy for Instagram/Facebook thumbnails to bypass CORS
    if (data.thumbnail && (data.thumbnail.includes('cdninstagram.com') || data.thumbnail.includes('facebook.com') || data.thumbnail.includes('fbcdn.net'))) {
        thumbnailUrl = `/api/proxy-image?url=${encodeURIComponent(data.thumbnail)}`;
        console.log('Using image proxy for:', data.thumbnail);
    }
    
    thumbnail.src = thumbnailUrl;
    thumbnail.onerror = function() {
        console.error('Failed to load thumbnail, using fallback');
        this.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="112"%3E%3Crect width="200" height="112" fill="%23ccc"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%23666"%3ENo Thumbnail%3C/text%3E%3C/svg%3E';
    };
    
    title.textContent = data.title || 'Video';
    duration.textContent = data.duration ? `Duration: ${data.duration}` : '';
    
    // Clear previous options
    downloadOptions.innerHTML = '';
    
    // Debug: log the data to see what's wrong
    console.log('Video data received:', data);
    console.log('Formats available:', data.formats);
    if (data.formats && data.formats.length > 0) {
        console.log('First format detail:', data.formats[0]);
    }
    
    // Add download button with dropdown
    if (data.formats && data.formats.length > 0) {
        // Separate MP4 videos and others
        const mp4Videos = data.formats.filter(f => f.type !== 'Audio Only' && f.ext.toUpperCase() === 'MP4');
        const otherVideos = data.formats.filter(f => f.type !== 'Audio Only' && f.ext.toUpperCase() !== 'MP4');
        const audioFormats = data.formats.filter(f => f.type === 'Audio Only');
        
        // Get best MP4 format (highest quality)
        const bestFormat = mp4Videos.length > 0 ? mp4Videos[0] : data.formats[0];
        
        // Create button wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'download-button-wrapper';
        
        // Main download button (uses yt-dlp, not direct URL)
        const mainBtn = document.createElement('button');
        mainBtn.className = 'main-download-btn';
        mainBtn.textContent = 'Download';
        mainBtn.onclick = function() {
            const videoUrl = document.getElementById('videoUrl').value.trim();
            const cleanTitle = sanitizeFilename(data.title);
            const filename = `${cleanTitle} ${bestFormat.quality}.${bestFormat.ext.toLowerCase()}`;
            const directUrl = bestFormat.url && bestFormat.url.startsWith('http') ? bestFormat.url : null;
            downloadDirectToChrome(videoUrl, bestFormat.format_id, filename, directUrl, platform);
        };
        
        // Dropdown toggle
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'dropdown-toggle';
        toggleBtn.innerHTML = '▼';
        toggleBtn.onclick = function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        };
        
        // Dropdown menu
        const dropdown = document.createElement('div');
        dropdown.className = 'dropdown-menu';
        
        // Add MP4 videos section
        if (mp4Videos.length > 0) {
            const mp4Title = document.createElement('div');
            mp4Title.className = 'dropdown-section-title';
            mp4Title.textContent = 'MP4 Videos';
            dropdown.appendChild(mp4Title);
            
            mp4Videos.forEach(format => {
                dropdown.appendChild(createDropdownItem(format, data.title, platform));
            });
        }
        
        // Add other videos section
        if (otherVideos.length > 0) {
            const otherTitle = document.createElement('div');
            otherTitle.className = 'dropdown-section-title';
            otherTitle.textContent = 'Other Formats';
            dropdown.appendChild(otherTitle);
            
            otherVideos.forEach(format => {
                dropdown.appendChild(createDropdownItem(format, data.title, platform));
            });
        }
        
        // Add audio section
        if (audioFormats.length > 0) {
            const audioTitle = document.createElement('div');
            audioTitle.className = 'dropdown-section-title';
            audioTitle.textContent = 'Audio Only';
            dropdown.appendChild(audioTitle);
            
            audioFormats.forEach(format => {
                dropdown.appendChild(createDropdownItem(format, data.title, platform));
            });
        }
        
        wrapper.appendChild(mainBtn);
        wrapper.appendChild(toggleBtn);
        wrapper.appendChild(dropdown);
        downloadOptions.appendChild(wrapper);
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!wrapper.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    }
    
    // Show results
    resultDiv.style.display = 'block';
}

function createDropdownItem(format, title, platform) {
    const item = document.createElement('div');
    item.className = 'dropdown-item';
    
    const left = document.createElement('div');
    left.className = 'dropdown-item-left';
    
    const quality = document.createElement('div');
    quality.className = 'dropdown-quality';
    const badge = document.createElement('span');
    badge.className = 'format-badge';
    badge.textContent = format.ext;
    const qualityText = document.createTextNode(' ' + (format.quality || '').replace((format.ext || '').toUpperCase(), '').trim());
    quality.appendChild(badge);
    quality.appendChild(qualityText);
    
    const details = document.createElement('div');
    details.className = 'dropdown-details';
    details.textContent = `${format.resolution || format.type} • ${format.filesize}`;
    
    left.appendChild(quality);
    left.appendChild(details);
    item.appendChild(left);
    
    item.onclick = function(e) {
        e.stopPropagation(); // Stop event bubbling
        
        const cleanTitle = sanitizeFilename(title);
        const filename = `${cleanTitle} ${format.quality}.${format.ext.toLowerCase()}`;
        
        // Get original video URL from stored data
        const videoUrl = document.getElementById('videoUrl').value.trim();
        
        // Close dropdown first
        const dropdown = document.querySelector('.dropdown-menu');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
        
        // Use yt-dlp download for all platforms
        // Pass direct URL for Instagram (if available)
        const directUrl = format.url && format.url.startsWith('http') ? format.url : null;
        downloadDirectToChrome(videoUrl, format.format_id, filename, directUrl, platform);
    };
    
    return item;
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.querySelector('p').textContent = message;
    errorDiv.style.display = 'block';
}

function sanitizeFilename(filename) {
    // Clean filename properly - remove special chars but keep spaces and dashes
    return filename
        .replace(/[<>:"/\\|?*]/g, '') // Remove invalid chars
        .replace(/\s+/g, ' ')  // Normalize spaces
        .trim()
        .substring(0, 100);  // Keep reasonable length
}

// Global variable to track download cancellation
let downloadController = null;

// Direct download to Chrome Downloads folder (NEW METHOD)
async function downloadDirectToChrome(videoUrl, formatId, filename, directUrl, platform) {
    const loadingDiv = document.getElementById('loading');
    const loadingText = loadingDiv.querySelector('p');
    
    loadingDiv.style.display = 'block';
    loadingText.innerHTML = '<div class="progress-text">🔍 Mengambil link download...</div>';
    
    try {
        // Get direct download URL from server
        const response = await fetch('/api/get-download-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_url: videoUrl,
                format_id: formatId,
                platform: platform,
                direct_url: directUrl,
                filename: filename
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            console.error('Download failed:', data.error);
            throw new Error(data.error || 'Gagal mendapatkan link download');
        }
        
        loadingText.innerHTML = '<div class="progress-text">✅ Memulai download...</div>';
        
        // Get download URL from server (it's a proxy URL)
        const downloadLink = data.download_url;
        
        // Use ONLY <a> tag method - simple and works best
        const a = document.createElement('a');
        a.href = downloadLink;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup after click
        setTimeout(() => {
            if (a.parentNode) {
                document.body.removeChild(a);
            }
        }, 1000);
        
        loadingText.innerHTML = '<div class="progress-text">✅ Download Started!</div><div class="progress-details">Your video is being downloaded</div>';
        
        setTimeout(() => {
            loadingDiv.style.display = 'none';
        }, 3000);
        
    } catch (error) {
        loadingDiv.style.display = 'none';
        showError('Gagal mendapatkan link download: ' + error.message);
        console.error('Download error:', error);
    }
}

async function downloadWithYtdlp(videoUrl, formatId, filename, directUrl = null) {
    const loadingDiv = document.getElementById('loading');
    const loadingText = loadingDiv.querySelector('p');
    
    loadingDiv.style.display = 'block';
    loadingText.innerHTML = '<div class="progress-text">🔄 Mempersiapkan download...</div><button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>';
    
    downloadController = new AbortController();
    const sessionId = Date.now().toString();
    
    // Detect platform from URL
    const platform = detectPlatform(videoUrl);
    
    // Setup SSE for progress updates
    let eventSource = null;
    let hasSSEUpdate = false;
    
    try {
        console.log('Setting up SSE connection for session:', sessionId);
        eventSource = new EventSource(`/api/download-progress/${sessionId}`);
        
        eventSource.onopen = function() {
            console.log('SSE connection opened');
        };
        
        eventSource.onmessage = function(event) {
            console.log('SSE message:', event.data);
            const data = JSON.parse(event.data);
            hasSSEUpdate = true;
            
            if (data.status === 'complete' || data.status === 'timeout') {
                eventSource.close();
                return;
            }
            
            // Update UI based on status
            let icon = '🔄';
            if (data.status === 'extracting') icon = '🔍';
            else if (data.status === 'downloading') icon = '⬇️';
            else if (data.status === 'processing') icon = '⚙️';
            else if (data.status === 'streaming') icon = '📤';
            
            let progressHtml = `<div class="progress-text">${icon} ${data.message}</div>`;
            
            if (data.percent) {
                progressHtml += `<div class="progress-details">Progress: ${data.percent}%</div>`;
            }
            
            if (data.downloaded && data.total) {
                const downloadedMB = (data.downloaded / (1024 * 1024)).toFixed(1);
                const totalMB = (data.total / (1024 * 1024)).toFixed(1);
                const percent = Math.round((data.downloaded / data.total) * 100);
                progressHtml = `<div class="progress-text">${icon} ${data.message} ${percent}%</div>`;
                progressHtml += `<div class="progress-details">${downloadedMB}MB / ${totalMB}MB</div>`;
            } else if (data.downloaded) {
                const downloadedMB = (data.downloaded / (1024 * 1024)).toFixed(1);
                progressHtml += `<div class="progress-details">${downloadedMB}MB downloaded</div>`;
            }
            
            progressHtml += '<button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>';
            loadingText.innerHTML = progressHtml;
            
            // Re-attach cancel handler
            const cancelBtn = document.getElementById('cancelDownloadBtn');
            if (cancelBtn) {
                cancelBtn.onclick = function() {
                    if (eventSource) eventSource.close();
                    if (downloadController) {
                        downloadController.abort();
                        loadingDiv.style.display = 'none';
                        showError('Download dibatalkan.');
                    }
                };
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('SSE error:', error);
            console.log('SSE connection closed/failed');
            eventSource.close();
        };
    } catch (e) {
        console.error('SSE setup error:', e);
    }
    
    // Add cancel button event
    const cancelBtn = document.getElementById('cancelDownloadBtn');
    if (cancelBtn) {
        cancelBtn.onclick = function() {
            if (eventSource) eventSource.close();
            if (downloadController) {
                downloadController.abort();
                loadingDiv.style.display = 'none';
                showError('Download dibatalkan.');
            }
        };
    }
    
    try {
        // Call proxy-download endpoint with video URL and format ID
        const response = await fetch('/api/proxy-download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_url: videoUrl,
                direct_url: directUrl,
                format_id: formatId,
                filename: filename,
                session_id: sessionId,
                platform: platform
            }),
            signal: downloadController.signal
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Download failed');
        }
        
        // Get content length for progress
        const contentLength = response.headers.get('content-length');
        const total = parseInt(contentLength, 10);
        
        // If no SSE updates received, show manual progress
        if (!hasSSEUpdate) {
            loadingText.innerHTML = '<div class="progress-text">📥 Menerima file dari server...</div><button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>';
            const cancelBtn = document.getElementById('cancelDownloadBtn');
            if (cancelBtn) {
                cancelBtn.onclick = function() {
                    if (eventSource) eventSource.close();
                    if (downloadController) {
                        downloadController.abort();
                        loadingDiv.style.display = 'none';
                        showError('Download dibatalkan.');
                    }
                };
            }
        }
        
        // Read stream
        const reader = response.body.getReader();
        const chunks = [];
        let loaded = 0;
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            chunks.push(value);
            loaded += value.length;
            
            // Show streaming progress if no SSE
            if (!hasSSEUpdate && total) {
                const percent = Math.round((loaded / total) * 100);
                const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
                const totalMB = (total / (1024 * 1024)).toFixed(1);
                loadingText.innerHTML = `<div class="progress-text">📥 Menerima file... ${percent}%</div><div class="progress-details">${loadedMB}MB / ${totalMB}MB</div><button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>`;
                
                const cancelBtn = document.getElementById('cancelDownloadBtn');
                if (cancelBtn) {
                    cancelBtn.onclick = function() {
                        if (eventSource) eventSource.close();
                        if (downloadController) {
                            downloadController.abort();
                            loadingDiv.style.display = 'none';
                            showError('Download dibatalkan.');
                        }
                    };
                }
            }
        }
        
        loadingText.innerHTML = '<div class="progress-text">💾 Menyimpan file...</div>';
        
        // Create blob and trigger Chrome download
        const blob = new Blob(chunks);
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
        }, 100);
        
        // Close SSE connection
        if (eventSource) eventSource.close();
        
        loadingText.innerHTML = '<div class="progress-text">✅ Download Complete!</div><div class="progress-details">Your video has been saved</div>';
        setTimeout(() => {
            loadingDiv.style.display = 'none';
            loadingText.innerHTML = 'Processing your request...';
        }, 3000);
        
        downloadController = null;
        
    } catch (error) {
        if (eventSource) eventSource.close();
        
        if (error.name === 'AbortError') {
            console.log('Download cancelled');
            return;
        }
        
        loadingDiv.style.display = 'none';
        console.error('Download error:', error);
        showError('Download failed: ' + error.message);
    }
}

async function downloadFileDirect(url, filename) {
    try {
        // Create new AbortController for this download
        downloadController = new AbortController();
        
        // Show loading with progress and cancel button
        const loadingDiv = document.getElementById('loading');
        loadingDiv.style.display = 'block';
        const loadingText = loadingDiv.querySelector('p');
        loadingText.innerHTML = '<span>Memulai download...</span><button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>';
        
        // Add cancel button event
        const cancelBtn = document.getElementById('cancelDownloadBtn');
        cancelBtn.onclick = function() {
            if (downloadController) {
                downloadController.abort();
                loadingDiv.style.display = 'none';
                showError('Download dibatalkan oleh pengguna.');
            }
        };
        
        // Fetch file through proxy
        const response = await fetch('/api/proxy-download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                filename: filename
            }),
            signal: downloadController.signal
        });
        
        if (!response.ok) {
            throw new Error('Download failed');
        }
        
        // Get content length for progress
        const contentLength = response.headers.get('content-length');
        const total = parseInt(contentLength, 10);
        let loaded = 0;
        
        // Read stream with progress
        const reader = response.body.getReader();
        const chunks = [];
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            chunks.push(value);
            loaded += value.length;
            
            // Update progress
            if (total) {
                const percent = Math.round((loaded / total) * 100);
                const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
                const totalMB = (total / (1024 * 1024)).toFixed(1);
                loadingText.innerHTML = `<span>Downloading... ${percent}% (${loadedMB}MB / ${totalMB}MB)</span><button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>`;
            } else {
                const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
                loadingText.innerHTML = `<span>Downloading... ${loadedMB}MB</span><button class="cancel-btn" id="cancelDownloadBtn">✕ Batalkan</button>`;
            }
            
            // Re-attach cancel button event after update
            const cancelBtn = document.getElementById('cancelDownloadBtn');
            if (cancelBtn) {
                cancelBtn.onclick = function() {
                    if (downloadController) {
                        downloadController.abort();
                        loadingDiv.style.display = 'none';
                        showError('Download dibatalkan oleh pengguna.');
                    }
                };
            }
        }
        
        loadingText.textContent = 'Menyimpan file...';
        
        // Create blob from chunks
        const blob = new Blob(chunks);
        
        // Create download link
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
        }, 100);
        
        loadingText.textContent = 'Download selesai!';
        setTimeout(() => {
            loadingDiv.style.display = 'none';
            loadingText.textContent = 'Processing your request...';
        }, 2000);
        
        downloadController = null;
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Download cancelled by user');
            return;
        }
        
        document.getElementById('loading').style.display = 'none';
        console.error('Download error:', error);
        showError('Download gagal. Silakan coba lagi.');
        downloadController = null;
    }
}

// Allow Enter key to trigger download
document.getElementById('videoUrl').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        downloadVideo();
    }
});

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Tools Tab Filter System - Accessible
document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tool-tab');
    const categories = document.querySelectorAll('.tools-category');
    
    // Show only first category by default
    if (categories.length > 0) {
        categories[0].classList.add('show');
    }
    
    tabs.forEach((tab, index) => {
        tab.addEventListener('click', function() {
            const selectedCategory = this.getAttribute('data-category');
            
            // Update ARIA attributes
            tabs.forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            this.classList.add('active');
            this.setAttribute('aria-selected', 'true');
            
            // Show/hide categories with smooth transition
            categories.forEach(cat => {
                if (cat.getAttribute('data-category') === selectedCategory) {
                    cat.classList.add('show');
                } else {
                    cat.classList.remove('show');
                }
            });
        });
        
        // Keyboard navigation
        tab.addEventListener('keydown', function(e) {
            let targetTab;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                targetTab = tabs[(index + 1) % tabs.length];
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                targetTab = tabs[(index - 1 + tabs.length) % tabs.length];
            }
            if (targetTab) {
                targetTab.focus();
                targetTab.click();
            }
        });
    });
});
