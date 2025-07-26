/* GAPS Facilitator - Utility Functions */

/**
 * Helper to extract list items from a quadrant
 * @param {string} listId - The ID of the list element
 * @returns {Array} Array of text content from list items (clean thought text only)
 */
function getQuadrantListById(listId) {
    const list = document.getElementById(listId);
    if (!list) return [];
    
    return Array.from(list.querySelectorAll('li')).map(li => {
        // Try to get just the thought text, excluding buttons and controls
        const thoughtElement = li.querySelector('.thought-text') || li.querySelector('span:first-child');
        if (thoughtElement) {
            return thoughtElement.textContent.trim();
        }
        
        // Fallback: get all text but try to clean it up
        let text = li.textContent.trim();
        
        // Remove common button text and UI elements
        text = text.replace(/\s*✏️\s*/g, '');
        text = text.replace(/\s*🗑️\s*/g, '');
        text = text.replace(/\s*Move to\.\.\.\s*/g, '');
        text = text.replace(/\s*(Goal|Status|Analysis|Plan)\s*/g, '');
        text = text.replace(/\s+/g, ' '); // Normalize whitespace
        
        return text.trim();
    }).filter(text => text.length > 0); // Remove empty entries
}

/**
 * Helper to get CSRF token from meta tag
 * @returns {string} CSRF token value
 */
function getCsrfToken() {
    const meta = document.querySelector('meta[name=csrf-token]');
    return meta ? meta.getAttribute('content') : '';
}

/**
 * Initialize board ID from Flask/Jinja context
 */
function initializeBoardId() {
    window.boardId = typeof window.boardId !== 'undefined' ? window.boardId : (typeof board_id !== 'undefined' ? board_id : null);
}

/**
 * Show notification to user
 * @param {string} message - Message to display
 * @param {boolean} isError - Whether this is an error notification
 */
function showNotification(message, isError = false) {
    const notification = document.querySelector('.notification');
    if (!notification) return;
    
    notification.textContent = message;
    notification.style.background = isError ? '#e74c3c' : '#007bff';
    notification.style.display = 'block';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

/**
 * Refresh quadrants display (full page reload)
 */
function refreshQuadrants() {
    location.reload();
}

/**
 * Update quadrant in background without page refresh (for Interactive Mode)
 */
function updateQuadrantInBackground(quadrant, thought, thoughtId = null) {
    console.log(`[DEBUG] Background update: Adding "${thought}" to ${quadrant} quadrant`);
    
    // Find the quadrant container (using actual template IDs)
    const quadrantMap = {
        'status': 'status-list',
        'goal': 'goal-list', 
        'analysis': 'analysis-list',
        'plan': 'plan-list'
    };
    
    const containerId = quadrantMap[quadrant];
    if (!containerId) {
        console.error(`[DEBUG] Unknown quadrant: ${quadrant}`);
        return;
    }
    
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`[DEBUG] Quadrant container not found: ${containerId}`);
        return;
    }
    
    // Create new thought element (matching template structure)
    const thoughtElement = document.createElement('li');
    thoughtElement.className = 'thought-item';
    const safeThoughtId = thoughtId || 0;
    const escapedThought = thought.replace(/'/g, "\\'");
    
    thoughtElement.innerHTML = `
        <span class="thought-content">${thought}</span>
        <div class="thought-controls">
            <button onclick="editThought(${safeThoughtId}, '${escapedThought}', this)" title="Edit">✏️</button>
            <select onchange="moveThought(${safeThoughtId}, this.value, this)">
                <option value="">Move to...</option>
                <option value="goal">Goal</option>
                <option value="analysis">Analysis</option>
                <option value="plan">Plan</option>
                <option value="status">Status</option>
            </select>
            <button onclick="deleteThought(${safeThoughtId}, this)" title="Delete">🗑️</button>
        </div>
    `;
    
    // Add to quadrant
    container.appendChild(thoughtElement);
    
    console.log(`[DEBUG] Successfully added thought to ${quadrant} quadrant in background`);
}

// Make functions available globally
window.refreshQuadrants = refreshQuadrants;
window.updateQuadrantInBackground = updateQuadrantInBackground;

// Initialize utilities when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeBoardId();
});
