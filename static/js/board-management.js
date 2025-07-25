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
function handleDeleteBoard(e) {
    e.preventDefault();
    console.log('[MENU] Delete Board clicked');
    
    if (!window.boardId) {
        alert('Please select a board first.');
        return;
    }
    
    if (confirm('Are you sure you want to delete this board? This action cannot be undone.')) {
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
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const resp = await fetch('/import_board', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            body: formData
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
    const createBtn = document.getElementById('modal-create-board-btn');
    const createBoardModal = document.getElementById('create-board-modal');
    
    if (createBtn) {
        createBtn.disabled = true;
        createBtn.textContent = 'Creating...';
    }

    try {
        const resp = await fetch('/create_board', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ name: boardName })
        });

        const result = await resp.json();

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
                console.log('[DEBUG] New board ID saved to localStorage:', result.board_id);
            }
            
            // Switch to the new board immediately
            setTimeout(() => {
                window.location.href = '/facilitator?board_id=' + result.board_id;
            }, 1000);
        } else {
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
