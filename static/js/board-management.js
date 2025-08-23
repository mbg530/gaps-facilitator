/* GAPS Facilitator - Board Management Module */

// Inline AI Board Summary rendering below the board title (top-level)
function renderInlineSummary(text, isError = false) {
    const el = document.getElementById('board-inline-summary');
    if (!el) return;
    el.innerHTML = '';
    // Summary block
    const summaryEl = document.createElement('div');
    summaryEl.textContent = text;
    el.appendChild(summaryEl);
    el.style.display = 'block';
    el.style.borderLeftColor = isError ? '#e74c3c' : '#007bff';
}

// Render or update the inline Goals↔Status alignment bar below the summary
function renderAlignmentBar(score, rationale = '') {
    const container = document.getElementById('board-inline-summary');
    if (!container) return;

    // Remove existing alignment block if any
    let alignBlock = container.querySelector('#inline-alignment');
    if (alignBlock) {
        alignBlock.remove();
    }
    // Remove any existing hint
    let hint = container.querySelector('#inline-alignment-hint');
    if (hint) {
        hint.remove();
    }

    // Hide alignment bar when either Goals or Status list is empty
    try {
        const goals = (typeof getQuadrantListById === 'function') ? getQuadrantListById('goal-list') : [];
        const statuses = (typeof getQuadrantListById === 'function') ? getQuadrantListById('status-list') : [];
        if (!goals || goals.length === 0 || !statuses || statuses.length === 0) {
            // Nothing to align yet — show subtle hint instead of bar
            hint = document.createElement('div');
            hint.id = 'inline-alignment-hint';
            hint.style.cssText = 'margin-top:8px;padding-top:6px;border-top:1px dashed #e2e8f0;color:#6b7280;font-size:12px;';
            hint.textContent = 'Add at least one Goal and one Status to see alignment.';
            container.appendChild(hint);
            return;
        }
    } catch (e) {
        // If DOM inspection fails, continue gracefully
    }

    // If score is null/undefined, do not render the bar
    if (score === null || score === undefined) return;

    // Clamp and format values
    const pct = Math.max(0, Math.min(100, Number(score) || 0));
    const title = `${pct}% alignment` + (rationale ? ` • ${rationale}` : '');

    alignBlock = document.createElement('div');
    alignBlock.id = 'inline-alignment';
    alignBlock.style.cssText = 'margin-top:8px;padding-top:6px;border-top:1px dashed #e2e8f0;';
    alignBlock.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin:4px 0 6px 0;color:#475569;font-size:12px;">
            <span>Status</span>
            <span style="font-weight:600;color:#111827;">Goals ↔ Status Alignment</span>
            <span>Goals</span>
        </div>
        <div title="${title.replace(/&/g,'&amp;').replace(/"/g,'&quot;')}" style="position:relative;height:10px;background:#e5f6ee;border-radius:999px;overflow:hidden;">
            <div style="position:absolute;left:0;top:0;bottom:0;width:${pct}%;background:linear-gradient(90deg,#10b981,#22c55e);border-radius:999px;transition:width .35s ease;"></div>
        </div>
        <div style="margin-top:6px;color:#6b7280;font-size:12px;">${pct}% aligned</div>
    `;
    container.appendChild(alignBlock);
}

async function loadInlineBoardSummary() {
    const el = document.getElementById('board-inline-summary');
    if (!el) return;
    if (!window.boardId) {
        renderInlineSummary('Select a board to see its AI summary.');
        return;
    }
    renderInlineSummary('Summarizing board…');
    try {
        const res = await fetchBoardAISummary(window.boardId);
        dlog('[AI] Inline summary response:', res);
        if (res && res.success) {
            const txt = (res.summary || '').trim();
            renderInlineSummary(txt || 'No summary available yet. Try adding thoughts or click Board Summary to refresh.');
            // Fetch and render alignment after summary
            try {
                const alignRes = await fetchBoardAlignment(window.boardId);
                if (alignRes && alignRes.success && alignRes.alignment) {
                    const { score = 0, rationale = '' } = alignRes.alignment;
                    renderAlignmentBar(score, rationale);
                } else {
                    renderAlignmentBar(null, (alignRes && (alignRes.error || alignRes.message)) || '');
                }
            } catch (ae) {
                derror('[AI] Alignment fetch failed:', ae);
                renderAlignmentBar(null, (ae && ae.message) || '');
            }
        } else {
            renderInlineSummary((res && (res.error || res.message)) || 'Unable to generate summary.', true);
            renderAlignmentBar(null, '');
        }
    } catch (e) {
        renderInlineSummary((e && e.message) || 'Unable to generate summary.', true);
        renderAlignmentBar(null, '');
    }
}

// Expose for manual refresh if needed elsewhere
window.loadInlineBoardSummary = loadInlineBoardSummary;

/**
 * Initialize board management functionality
 */
function initializeBoardManagement() {
    const menuIcon = document.getElementById('board-menu-icon');
    const dropdown = document.getElementById('board-menu-dropdown');
    const openBoardModal = document.getElementById('open-board-modal');
    const boardList = document.getElementById('board-list');
    const closeBoardModal = document.getElementById('close-board-modal');
    const refreshBtn = document.getElementById('summary-refresh-btn');
    const toneSelect = document.getElementById('summary-tone-select');
    const lengthSelect = document.getElementById('summary-length-select');

    // Board menu functionality
    if (dropdown) {
        dropdown.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }

    // Initialize tone/length selectors from storage
    if (toneSelect) {
        const storedTone = getStoredTone() || 'neutral';
        toneSelect.value = storedTone;
        toneSelect.addEventListener('change', () => {
            setStoredTone(toneSelect.value);
            loadInlineBoardSummary();
        });
    }
    if (lengthSelect) {
        const storedLen = getStoredLength() || 'medium';
        lengthSelect.value = storedLen;
        lengthSelect.addEventListener('change', () => {
            setStoredLength(lengthSelect.value);
            loadInlineBoardSummary();
        });
    }

    // Debounced summary refresh available globally
    window.debouncedSummaryRefresh = debounce(() => {
        loadInlineBoardSummary();
    }, 1500);

    // Populate inline AI summary after boardId is initialized (utils.js)
    setTimeout(loadInlineBoardSummary, 0);

    // Refresh inline summary on-demand via button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async function() {
            try {
                refreshBtn.disabled = true;
                refreshBtn.style.opacity = '0.75';
                refreshBtn.style.cursor = 'wait';
                const oldHTML = refreshBtn.innerHTML;
                // Inline SVG spinner (SMIL animateTransform)
                refreshBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 50 50" aria-hidden="true">\
  <circle cx="25" cy="25" r="20" fill="none" stroke="#007bff" stroke-width="5" stroke-linecap="round" stroke-dasharray="31.4 31.4">\
    <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="0.9s" repeatCount="indefinite"/>\
  </circle>\
</svg>';
                renderInlineSummary('Refreshing summary…');
                await loadInlineBoardSummary();
                refreshBtn.innerHTML = oldHTML || '⟳';
            } finally {
                refreshBtn.disabled = false;
                refreshBtn.style.opacity = '';
                refreshBtn.style.cursor = '';
            }
        });
    }

    if (menuIcon) {
        menuIcon.addEventListener('click', function (e) {
            if (dropdown) {
                dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
            }
            e.stopPropagation();
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', function () {
        if (dropdown) dropdown.style.display = 'none';
    });

    // Close board modal handler
    if (closeBoardModal) {
        closeBoardModal.addEventListener('click', function() {
            if (openBoardModal) {
                openBoardModal.style.display = 'none';
            }
        });
    }

    // Setup board creation modal handlers
    setupBoardCreationModal();

    // Attach handlers for dropdown menu items
    setupMenuHandlers();
}

/**
 * Setup handlers for all menu items
 */
function setupMenuHandlers() {
    const openBoardLink = document.getElementById('open-board');
    const createBoardLink = document.getElementById('create-board');
    const exportDataLink = document.getElementById('export-data');
    const importDataLink = document.getElementById('import-data');
    const deleteBoardLink = document.getElementById('delete-board');
    const helpLink = document.getElementById('help-link');
    const renameBoardLink = document.getElementById('rename-board');
    const boardSummaryLink = document.getElementById('board-summary');

    if (openBoardLink) {
        openBoardLink.addEventListener('click', handleOpenBoard);
    }

    if (createBoardLink) {
        createBoardLink.addEventListener('click', handleCreateBoard);
    }

    if (exportDataLink) {
        exportDataLink.addEventListener('click', handleExportData);
    }

    if (importDataLink) {
        importDataLink.addEventListener('click', handleImportData);
    }

    if (deleteBoardLink) {
        deleteBoardLink.addEventListener('click', handleDeleteBoard);
    }

    if (helpLink) {
        helpLink.addEventListener('click', handleHelp);
    }

    if (renameBoardLink) {
        renameBoardLink.addEventListener('click', handleRenameBoard);
    }

    if (boardSummaryLink) {
        boardSummaryLink.addEventListener('click', handleBoardSummary);
    }
}

/**
 * Handle opening board selection modal
 */
async function handleOpenBoard(e) {
    e.preventDefault();
    dlog('[MENU] Open Board clicked');
    
    const openBoardModal = document.getElementById('open-board-modal');
    const boardList = document.getElementById('board-list');
    
    if (openBoardModal) {
        openBoardModal.style.display = 'flex';
        
        if (boardList) {
            boardList.innerHTML = '<div style="padding:1em; color:#888;">Loading boards...</div>';
            
            try {
                const data = await getJSON('/list_boards');
                dlog('[DEBUG] /list_boards response:', data);
                
                if (data && Array.isArray(data.boards) && data.boards.length > 0) {
                    let boardsHtml = '';
                    data.boards.forEach(board => {
                        const isActive = board.id == window.boardId ? ' (current)' : '';
                        
                        // Handle date formatting safely
                        let dateStr = 'Unknown';
                        if (board.created_at) {
                            try {
                                const date = new Date(board.created_at);
                                if (!isNaN(date.getTime())) {
                                    dateStr = date.toLocaleDateString();
                                }
                            } catch (e) {
                                dwarn('Invalid date for board:', board.created_at);
                            }
                        }
                        
                        boardsHtml += `
                            <div class="board-item" data-board-id="${board.id}" style="padding:0.5em; border:1px solid #ddd; margin:0.3em 0; cursor:pointer; border-radius:4px;">
                                <strong>${board.name}</strong>${isActive}
                                <div style="font-size:0.9em; color:#666;">Created: ${dateStr}</div>
                            </div>`;
                    });
                    boardList.innerHTML = boardsHtml;
                    
                    // Add click handlers for board items
                    boardList.querySelectorAll('.board-item').forEach(item => {
                        item.addEventListener('click', function() {
                            const boardId = this.getAttribute('data-board-id');
                            selectBoard(boardId);
                        });
                    });
                } else {
                    boardList.innerHTML = '<div style="padding:1em; color:#888;">No boards found. Create a new board to get started.</div>';
                }
            } catch (error) {
                derror('[ERROR] Failed to load boards:', error);
                if (error && error.status === 429) {
                    showNotification('AI quota exceeded (429). Try again later.', true);
                }
                boardList.innerHTML = '<div style="padding:1em; color:#c00;">Failed to load boards. Please try again.</div>';
            }
        }
    }
}

/**
 * Handle creating a new board
 */
function handleCreateBoard(e) {
    e.preventDefault();
    dlog('[MENU] Create Board clicked');
    
    const createBoardModal = document.getElementById('create-board-modal');
    if (createBoardModal) {
        createBoardModal.style.display = 'flex';
        
        // Clear the input field
        const newBoardNameInput = document.getElementById('new-board-name');
        if (newBoardNameInput) {
            newBoardNameInput.value = '';
            newBoardNameInput.focus();
        }
    }
}

/**
 * Setup board creation modal event handlers
 */
function setupBoardCreationModal() {
    const createBoardModal = document.getElementById('create-board-modal');
    const newBoardNameInput = document.getElementById('new-board-name');
    const createBtn = document.getElementById('modal-create-board-btn');
    const cancelBtn = document.getElementById('modal-cancel-board-btn');

    // Create board button
    if (createBtn) {
        createBtn.addEventListener('click', async function() {
            const boardName = newBoardNameInput ? newBoardNameInput.value.trim() : '';
            
            if (!boardName) {
                alert('Please enter a board name.');
                return;
            }

            await createNewBoard(boardName);
        });
    }

    // Cancel button
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            if (createBoardModal) {
                createBoardModal.style.display = 'none';
            }
        });
    }

    // Enter key to create board
    if (newBoardNameInput) {
        newBoardNameInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (createBtn) {
                    createBtn.click();
                }
            }
        });
    }

    // Close modal when clicking outside
    if (createBoardModal) {
        createBoardModal.addEventListener('click', function(e) {
            if (e.target === createBoardModal) {
                createBoardModal.style.display = 'none';
            }
        });
    }
}

/**
 * Handle data export
 */
function handleExportData(e) {
    e.preventDefault();
    console.log('[MENU] Export Data clicked');
    
    if (!window.boardId) {
        alert('Please select a board first.');
        return;
    }
    
    // Trigger export
    window.location.href = `/export_board?board_id=${window.boardId}`;
}

/**
 * Select a board and switch to it
 */
function selectBoard(boardId) {
    console.log('[DEBUG] Selecting board:', boardId);
    
    // Save board ID to localStorage for persistence
    localStorage.setItem('gaps-current-board-id', boardId);
    console.log('[DEBUG] Board ID saved to localStorage:', boardId);
    
    // Close the modal first
    const openBoardModal = document.getElementById('open-board-modal');
    if (openBoardModal) {
        openBoardModal.style.display = 'none';
    }
    
    // Show loading notification
    showNotification('Loading board...');
    
    // Set the board ID and redirect
    console.log('[DEBUG] About to redirect to:', '/facilitator?board_id=' + boardId);
    try {
        window.location.href = '/facilitator?board_id=' + boardId;
        console.log('[DEBUG] Redirect initiated successfully');
    } catch (error) {
        console.error('[ERROR] Failed to redirect:', error);
    }
}

/**
 * Handle data import
 */
function handleImportData(e) {
    e.preventDefault();
    console.log('[MENU] Import Data clicked');
    
    // Create file input for import
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            importBoardData(file);
        }
    });
    fileInput.click();
}

/**
 * Handle board deletion
 */
async function handleDeleteBoard(e) {
    e.preventDefault();
    dlog('[MENU] Delete Board clicked');
    
    if (!window.boardId) {
        alert('Please select a board first.');
        return;
    }
    
    const confirmed = await showConfirm('Are you sure you want to delete this board? This action cannot be undone.');
    if (confirmed) {
        deleteBoardById(window.boardId);
    }
}

/**
 * Handle help display
 */
function handleHelp(e) {
    e.preventDefault();
    dlog('[MENU] Help clicked');
    
    const helpOverlay = document.getElementById('help-overlay');
    if (helpOverlay) {
        helpOverlay.style.display = 'block';
    }
}

/**
 * Handle renaming the current board
 */
async function handleRenameBoard(e) {
    e.preventDefault();
    dlog('[MENU] Rename Board clicked');
    if (!window.boardId) {
        alert('Please select a board first.');
        return;
    }
    const currentTitleEl = document.getElementById('board-title-badge');
    const currentTitle = currentTitleEl ? currentTitleEl.textContent.replace(/^📋\s*/, '') : '';
    const newName = prompt('Enter a new board name:', currentTitle || '');
    if (!newName || !newName.trim()) return;
    try {
        const res = await renameBoard(window.boardId, newName.trim());
        if (res && res.success) {
            showNotification('Board renamed successfully');
            // Update header title live without reload
            if (currentTitleEl) {
                currentTitleEl.textContent = '📋 ' + newName.trim();
            }
            if (window.debouncedSummaryRefresh) window.debouncedSummaryRefresh();
        } else {
            alert((res && (res.error || res.message)) || 'Failed to rename board');
        }
    } catch (err) {
        derror('[ERROR] Rename board failed:', err);
        alert(err && err.message ? err.message : 'Rename failed');
    }
}

/**
 * Handle showing a board summary modal
 */
async function handleBoardSummary(e) {
    e.preventDefault();
    dlog('[MENU] Board Summary clicked');
    if (!window.boardId) {
        alert('Please select a board first.');
        return;
    }
    try {
        const target = document.getElementById('board-inline-summary');
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        renderInlineSummary('Summarizing board…');
        const res = await fetchBoardAISummary(window.boardId);
        dlog('[AI] Menu summary response:', res);
        if (!res || !res.success) {
            const msg = (res && (res.error || res.message)) || 'Failed to fetch AI summary';
            renderInlineSummary(msg, true);
            return;
        }
        const text = (res.summary || '').trim();
        renderInlineSummary(text || 'No summary available yet. Try adding thoughts or click Board Summary to refresh.');
        // Fetch and render alignment after summary
        try {
            const alignRes = await fetchBoardAlignment(window.boardId);
            if (alignRes && alignRes.success && alignRes.alignment) {
                const { score = 0, rationale = '' } = alignRes.alignment;
                renderAlignmentBar(score, rationale);
            } else {
                renderAlignmentBar(null, (alignRes && (alignRes.error || alignRes.message)) || '');
            }
        } catch (ae) {
            derror('[AI] Alignment fetch failed:', ae);
            renderAlignmentBar(null, (ae && ae.message) || '');
        }
    } catch (err) {
        derror('[ERROR] Fetch AI board summary failed:', err);
        if (err && err.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        renderInlineSummary((err && err.message) || 'Failed to fetch AI summary', true);
        renderAlignmentBar(null, '');
    }
}

/**
 * Simple modal to display multi-line text summary
 */
function showSummaryModal(text) {
    let modal = document.getElementById('board-summary-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'board-summary-modal';
        modal.style.cssText = 'position:fixed;z-index:5000;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;max-width:560px;width:92%;padding:1.2em 1.2em 1em;border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.18);">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5em;">
                    <h3 style="margin:0;font-size:1.1em;color:#007bff;">Board Summary</h3>
                    <button id="board-summary-close" style="background:none;border:none;font-size:1.2em;cursor:pointer;color:#888;">×</button>
                </div>
                <pre id="board-summary-content" style="white-space:pre-wrap;max-height:60vh;overflow:auto;margin:0;font-family:inherit;line-height:1.4;"></pre>
            </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
        const btn = modal.querySelector('#board-summary-close');
        if (btn) btn.addEventListener('click', () => modal.style.display = 'none');
    }
    const pre = modal.querySelector('#board-summary-content');
    if (pre) pre.textContent = text || '';
    modal.style.display = 'flex';
}

// Duplicate selectBoard function removed - using the simple redirect version above

/**
 * Import board data from file
 */
async function importBoardData(file) {
    try {
        // Read the file content as text
        const fileContent = await file.text();
        // Parse the JSON content
        const boardData = JSON.parse(fileContent);
        
        const result = await postJSON('/import_board', boardData);
        
        if (result.success) {
            showNotification('Board imported successfully!');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            alert('Failed to import board: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        derror('[ERROR] Failed to import board:', error);
        if (error && error.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        alert('Error importing board. Please try again.');
    }
}

/**
 * Delete board by ID
 */
async function deleteBoardById(boardId) {
    try {
        const result = await postJSON('/delete_board', { board_id: boardId });
        
        if (result.success) {
            showNotification('Board deleted successfully!');
            window.boardId = null;
            
            // Clear board ID from localStorage since board was deleted
            localStorage.removeItem('gaps-current-board-id');
            dlog('[DEBUG] Board ID cleared from localStorage after deletion');
            
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            alert('Failed to delete board: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        derror('[ERROR] Failed to delete board:', error);
        if (error && error.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        alert('Error deleting board. Please try again.');
    }
}

/**
 * Create a new board
 */
async function createNewBoard(boardName) {
    const createBtn = document.getElementById('modal-create-board-btn');
    const createBoardModal = document.getElementById('create-board-modal');
    
    if (createBtn) {
        createBtn.disabled = true;
        createBtn.textContent = 'Creating...';
    }

    try {
        const result = await postJSON('/create_board', { name: boardName });

        if (result.success) {
            showNotification('Board created successfully!');
            
            // Close modal
            if (createBoardModal) {
                createBoardModal.style.display = 'none';
            }
            
            // Set the new board as active
            if (result.board_id) {
                window.boardId = result.board_id;
                // Save board ID to localStorage for persistence
                localStorage.setItem('gaps-current-board-id', result.board_id);
                dlog('[DEBUG] New board ID saved to localStorage:', result.board_id);
            }
            
            // Switch to the new board immediately
            setTimeout(() => {
                window.location.href = '/facilitator?board_id=' + result.board_id;
            }, 1000);
        } else {
            alert('Failed to create board: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        derror('[ERROR] Failed to create board:', error);
        if (error && error.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        alert('Error creating board. Please try again.');
    } finally {
        if (createBtn) {
            createBtn.disabled = false;
            createBtn.textContent = 'Create';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeBoardManagement();
});
