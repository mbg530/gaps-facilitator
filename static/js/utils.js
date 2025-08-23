/* GAPS Facilitator - Utility Functions */

// Lightweight gated logger. Enable by setting window.DEBUG_VERBOSE = true
// or localStorage.setItem('debug_verbose','1').
window.DEBUG_VERBOSE = typeof window.DEBUG_VERBOSE !== 'undefined'
  ? window.DEBUG_VERBOSE
  : (typeof localStorage !== 'undefined' && localStorage.getItem('debug_verbose') === '1');

function dlog(...args) { if (window.DEBUG_VERBOSE) console.log(...args); }
function dwarn(...args) { if (window.DEBUG_VERBOSE) console.warn(...args); }
function derror(...args) { if (window.DEBUG_VERBOSE) console.error(...args); }

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
    dlog(`[DEBUG] Background update: Adding "${thought}" to ${quadrant} quadrant`);
    
    // First, save to database
    const boardId = window.boardId;
    if (!boardId) {
        derror(`[DEBUG] No board ID available for saving thought`);
        return;
    }
    
    // Save to database via centralized API helper
    postJSON('/add_thought', {
        content: thought,
        quadrant: quadrant,
        board_id: boardId
    })
    .then(result => {
        if (result && result.success) {
            const createdId = result.thought_id || (result.thought && result.thought.id);
            dlog(`[DEBUG] Successfully saved thought to database with ID: ${createdId}`);
            addThoughtToDOM(quadrant, thought, createdId);
        } else {
            derror(`[DEBUG] Failed to save thought to database:`, result && (result.error || result.message));
            addThoughtToDOM(quadrant, thought, thoughtId || 0);
        }
    })
    .catch(err => {
        derror(`[DEBUG] Error saving thought to database:`, err);
        if (err && err.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        // Still add to DOM for immediate feedback
        addThoughtToDOM(quadrant, thought, thoughtId || 0);
    });
}

/**
 * Add thought to DOM (helper function)
 */
function addThoughtToDOM(quadrant, thought, thoughtId) {
    // Find the quadrant container (using actual template IDs)
    const quadrantMap = {
        'status': 'status-list',
        'goal': 'goal-list', 
        'analysis': 'analysis-list',
        'plan': 'plan-list'
    };
    
    const containerId = quadrantMap[quadrant];
    if (!containerId) {
        derror(`[DEBUG] Unknown quadrant: ${quadrant}`);
        return;
    }
    
    const container = document.getElementById(containerId);
    if (!container) {
        derror(`[DEBUG] Quadrant container not found: ${containerId}`);
        return;
    }
    
    // Create new thought element (matching template structure)
    const thoughtElement = document.createElement('li');
    thoughtElement.className = 'thought-item';
    thoughtElement.setAttribute('data-thought-id', thoughtId);
    const escapedThought = thought.replace(/'/g, "\\'");
    
    thoughtElement.innerHTML = `
        <span class="thought-content">${thought}</span>
        <div class="thought-controls">
            <button onclick="editThought(${thoughtId}, '${escapedThought}', this)" title="Edit">✏️</button>
            <select onchange="moveThought(${thoughtId}, this.value, this)">
                <option value="">Move to...</option>
                <option value="goal">Goal</option>
                <option value="analysis">Analysis</option>
                <option value="plan">Plan</option>
                <option value="status">Status</option>
            </select>
            <button onclick="deleteThought(${thoughtId}, this)" title="Delete">🗑️</button>
        </div>
    `;
    
    // Add to quadrant
    container.appendChild(thoughtElement);
    
    dlog(`[DEBUG] Successfully added thought to ${quadrant} quadrant DOM with ID: ${thoughtId}`);
}

/**
 * Fetch board summary (counts and recent thoughts per quadrant)
 * @param {string|number} boardId
 */
async function fetchBoardSummary(boardId) {
    if (!boardId) throw new Error('boardId required');
    return await getJSON(`/board_summary?board_id=${encodeURIComponent(boardId)}`);
}

/**
 * Fetch AI-generated executive summary for the board
 * @param {string|number} boardId
 */
async function fetchBoardAISummary(boardId, opts = {}) {
    if (!boardId) throw new Error('boardId required');
    const tone = (opts.tone || getStoredTone() || 'neutral').toLowerCase();
    const length = (opts.length || getStoredLength() || 'medium').toLowerCase();
    const url = `/board_ai_summary?board_id=${encodeURIComponent(boardId)}&tone=${encodeURIComponent(tone)}&length=${encodeURIComponent(length)}`;
    return await getJSON(url);
}

/**
 * Fetch LLM-based Goals↔Status alignment
 * @param {string|number} boardId
 */
async function fetchBoardAlignment(boardId) {
    if (!boardId) throw new Error('boardId required');
    const url = `/board_alignment?board_id=${encodeURIComponent(boardId)}`;
    return await getJSON(url);
}

/**
 * Debounce utility: returns a function that delays invoking fn until delay ms have elapsed
 */
function debounce(fn, delay = 1500) {
    let t = null;
    return function(...args) {
        if (t) clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), delay);
    };
}

// User preference helpers for summary tone/length
function getStoredTone() {
    try { return localStorage.getItem('gaps-summary-tone') || null; } catch { return null; }
}
function getStoredLength() {
    try { return localStorage.getItem('gaps-summary-length') || null; } catch { return null; }
}
function setStoredTone(val) {
    try { localStorage.setItem('gaps-summary-tone', val); } catch {}
}
function setStoredLength(val) {
    try { localStorage.setItem('gaps-summary-length', val); } catch {}
}

/**
 * Rename a board (DB-backed). Enforces unique name per user server-side
 * @param {string|number} boardId
 * @param {string} newName
 */
async function renameBoard(boardId, newName) {
    if (!boardId) throw new Error('boardId required');
    if (!newName || !newName.trim()) throw new Error('newName required');
    return await postJSON('/rename_board', { board_id: boardId, name: newName.trim() });
}

// Make functions available globally
window.refreshQuadrants = refreshQuadrants;
window.updateQuadrantInBackground = updateQuadrantInBackground;
window.dlog = dlog;
window.dwarn = dwarn;
window.derror = derror;
window.fetchBoardSummary = fetchBoardSummary;
window.fetchBoardAISummary = fetchBoardAISummary;
window.fetchBoardAlignment = fetchBoardAlignment;
window.renameBoard = renameBoard;
window.debounce = debounce;
window.getStoredTone = getStoredTone;
window.getStoredLength = getStoredLength;
window.setStoredTone = setStoredTone;
window.setStoredLength = setStoredLength;

// Initialize utilities when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeBoardId();
});
