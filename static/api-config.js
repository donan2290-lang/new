// API Configuration for Railway Backend
const API_BASE_URL = 'https://your-app.railway.app';  // Ganti dengan URL Railway Anda setelah deploy

// Helper function untuk fetch dengan error handling
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Export untuk digunakan di file lain
window.API_CONFIG = {
    baseUrl: API_BASE_URL,
    request: apiRequest
};
