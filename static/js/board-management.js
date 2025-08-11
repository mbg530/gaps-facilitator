/* GAPS Facilitator - Board Management Module */

/**
 * Initialize board management functionality
 */
function initializeBoardManagement() {
    const menuIcon = document.getElementById('board-menu-icon');
    const dropdown = document.getElementById('board-menu-dropdown');
    const openBoardModal = document.getElementById('open-board-modal');
    const boardList = document.getElementById('board-list');
    const closeBoardModal = document.getElementById('close-board-modal');

    // Board menu functionality
    if (dropdown) {
        dropdown.addEventListener('click', function (e) {
            e.stopPropagation();
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
}

/**
 * Handle opening board selection modal
 */
async function handleOpenBoard(e) {
    e.preventDefault();
    console.log('[MENU] Open Board clicked');
    
    const openBoardModal = document.getElementById('open-board-modal');
    const boardList = document.getElementById('board-list');
    
    if (openBoardModal) {
        openBoardModal.style.display = 'flex';
        
        if (boardList) {
            boardList.innerHTML = '<div style="padding:1em; color:#888;">Loading boards...</div>';
            
            try {
                const resp = await fetch('/list_boards');
                if (!resp.ok) throw new Error('Failed to fetch boards: ' + resp.status + ' ' + resp.statusText);
                
                const data = await resp.json();
                console.log('[DEBUG] /list_boards response:', data);
                
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
                                console.warn('Invalid date for board:', board.created_at);
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
                console.error('[ERROR] Failed to load boards:', error);
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
    console.log('[MENU] Create Board clicked');
    
    const createBoardModal = document.getElementById('create-board-modal');
    console.log('[DEBUG] Create board modal found:', !!createBoardModal);
    
    if (createBoardModal) {
        console.log('[DEBUG] Opening create board modal');
        createBoardModal.style.display = 'flex';
        
        // Clear the input field
        const newBoardNameInput = document.getElementById('new-board-name');
        console.log('[DEBUG] Board name input found:', !!newBoardNameInput);
        if (newBoardNameInput) {
            newBoardNameInput.value = '';
            newBoardNameInput.focus();
        }
    } else {
        console.error('[ERROR] Create board modal not found in DOM');
        // Fallback: prompt for board name
        const boardName = prompt('Enter board name:');
        if (boardName && boardName.trim()) {
            createNewBoard(boardName.trim());
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
    window.location.href = '/facilitator?board_id=' + boardId;
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
    console.log('[MENU] Delete Board clicked');
    
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
    console.log('[MENU] Help clicked');
    
    const helpOverlay = document.getElementById('help-overlay');
    if (helpOverlay) {
        helpOverlay.style.display = 'block';
    }
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
        
        const resp = await fetch('/import_board', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(boardData)
        });
        
        const result = await resp.json();
        
        if (result.success) {
            showNotification('Board imported successfully!');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            alert('Failed to import board: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('[ERROR] Failed to import board:', error);
        alert('Error importing board. Please try again.');
    }
}

/**
 * Delete board by ID
 */
async function deleteBoardById(boardId) {
    try {
        const resp = await fetch('/delete_board', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ board_id: boardId })
        });
        
        const result = await resp.json();
        
        if (result.success) {
            showNotification('Board deleted successfully!');
            window.boardId = null;
            
            // Clear board ID from localStorage since board was deleted
            localStorage.removeItem('gaps-current-board-id');
            console.log('[DEBUG] Board ID cleared from localStorage after deletion');
            
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            alert('Failed to delete board: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('[ERROR] Failed to delete board:', error);
        alert('Error deleting board. Please try again.');
    }
}

/**
 * Create a new board
 */
async function createNewBoard(boardName) {
    console.log('[DEBUG] Creating new board:', boardName);
    console.log('[DEBUG] About to find modal elements...');
    
    const createBtn = document.getElementById('modal-create-board-btn');
    const createBoardModal = document.getElementById('create-board-modal');
    
    if (createBtn) {
        createBtn.disabled = true;
        createBtn.textContent = 'Creating...';
    }

    console.log('[DEBUG] About to start try block...');
    try {
        console.log('[DEBUG] Sending create board request to server');
        console.log('[DEBUG] About to call getCsrfToken()...');
        
        let csrfToken;
        try {
            // Direct CSRF token extraction to bypass cache issues
            const meta = document.querySelector('meta[name=csrf-token]');
            csrfToken = meta ? meta.getAttribute('content') : '';
            console.log('[DEBUG] Direct CSRF token extraction:', csrfToken ? 'SUCCESS' : 'FAILED');
            console.log('[DEBUG] CSRF token length:', csrfToken.length);
        } catch (error) {
            console.error('[ERROR] Direct CSRF token extraction failed:', error);
            csrfToken = '';
        }
        console.log('[DEBUG] Using CSRF token for request:', csrfToken || '(empty)');
        
        const requestData = { name: boardName };
        console.log('[DEBUG] Request data:', requestData);
        
        const resp = await fetch('/create_board', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(requestData)
        });

        console.log('[DEBUG] Server response status:', resp.status);
        console.log('[DEBUG] Server response ok:', resp.ok);
        
        if (!resp.ok) {
            const errorText = await resp.text();
            console.error('[ERROR] Server returned error:', resp.status, errorText);
            console.error('[ERROR] Response headers:', [...resp.headers.entries()]);
            console.error('[ERROR] Request details - URL:', '/create_board');
            console.error('[ERROR] Request details - Method:', 'POST');
            console.error('[ERROR] Request details - Headers:', {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            });
            console.error('[ERROR] Request details - Body:', JSON.stringify(requestData));
            throw new Error(`Server error: ${resp.status} - ${errorText}`);
        }
        
        const result = await resp.json();
        console.log('[DEBUG] Server response data:', result);

        if (result.success) {
            console.log('[DEBUG] Processing successful board creation...');
            
            try {
                console.log('[DEBUG] Showing notification...');
                showNotification('Board created successfully!');
                console.log('[DEBUG] Notification shown');
            } catch (error) {
                console.error('[ERROR] Failed to show notification:', error);
            }
            
            // Close modal
            console.log('[DEBUG] Closing modal...');
            if (createBoardModal) {
                createBoardModal.style.display = 'none';
                console.log('[DEBUG] Modal closed');
            } else {
                console.log('[DEBUG] No modal to close');
            }
            
            // Set the new board as active
            console.log('[DEBUG] Setting new board as active...');
            if (result.board_id) {
                window.boardId = result.board_id;
                // Save board ID to localStorage for persistence
                localStorage.setItem('gaps-current-board-id', result.board_id);
                console.log('[DEBUG] New board ID saved to localStorage:', result.board_id);
            } else {
                console.log('[ERROR] No board_id in result:', result);
            }
            
            // Switch to the new board immediately
            console.log('[DEBUG] Preparing to redirect to new board...');
            setTimeout(() => {
                const redirectUrl = '/facilitator?board_id=' + result.board_id;
                console.log('[DEBUG] Redirecting to:', redirectUrl);
                window.location.href = redirectUrl;
            }, 1000);
            console.log('[DEBUG] Redirect scheduled for 1 second');
        } else {
            console.log('[ERROR] Server returned success=false:', result);
            alert('Failed to create board: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('[ERROR] Failed to create board:', error);
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
