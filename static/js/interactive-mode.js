/* GAPS Facilitator - Interactive Mode Module */

let interactiveGapsHistory = [];
let suggestionRenderCount = 0;

/**
 * Save current board ID to localStorage
 */
function saveCurrentBoard() {
    if (window.boardId) {
        localStorage.setItem('gaps-current-board-id', window.boardId);
        console.log('[DEBUG] Current board ID saved to localStorage:', window.boardId);
    }
}

/**
 * Restore board selection from localStorage
 */
function restoreCurrentBoard() {
    const savedBoardId = localStorage.getItem('gaps-current-board-id');
    if (savedBoardId && savedBoardId !== window.boardId) {
        console.log('[DEBUG] Restoring board from localStorage:', savedBoardId, 'current:', window.boardId);
        // Navigate to the saved board
        window.location.href = `/facilitator?board_id=${savedBoardId}`;
        return true;
    }
    return false;
}

/**
 * Save conversation content to localStorage
 */
function saveConversationContent() {
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    if (interactiveGapsChat) {
        const boardId = window.boardId || 'default';
        const conversationData = {
            chatContent: interactiveGapsChat.innerHTML,
            history: interactiveGapsHistory,
            suggestionCount: suggestionRenderCount,
            timestamp: Date.now()
        };
        localStorage.setItem(`interactive-gaps-conversation-${boardId}`, JSON.stringify(conversationData));
        console.log('[DEBUG] Conversation content saved to localStorage');
    }
}

/**
 * Restore conversation content from localStorage
 */
function restoreConversationContent() {
    const boardId = window.boardId || 'default';
    const savedData = localStorage.getItem(`interactive-gaps-conversation-${boardId}`);
    
    if (savedData) {
        try {
            const conversationData = JSON.parse(savedData);
            const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
            
            if (interactiveGapsChat && conversationData.chatContent) {
                interactiveGapsChat.innerHTML = conversationData.chatContent;
                interactiveGapsHistory = conversationData.history || [];
                suggestionRenderCount = conversationData.suggestionCount || 0;
                
                // Scroll to bottom
                interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
                
                // Re-attach event listeners to suggestion buttons
                reattachSuggestionListeners();
                
                console.log('[DEBUG] Conversation content restored from localStorage');
                return true;
            }
        } catch (error) {
            console.error('[DEBUG] Error restoring conversation content:', error);
        }
    }
    return false;
}

/**
 * Re-attach event listeners to suggestion buttons after restoration
 */
function reattachSuggestionListeners() {
    const suggestionButtons = document.querySelectorAll('[id^="add-to-quadrant-btn-"]');
    suggestionButtons.forEach(button => {
        if (!button.hasAttribute('data-listener-attached')) {
            // Extract thought and quadrant from button attributes or nearby elements
            const thoughtText = button.getAttribute('data-thought');
            const quadrant = button.getAttribute('data-quadrant');
            
            if (thoughtText && quadrant) {
                button.addEventListener('click', async function() {
                    await addSuggestedThought(thoughtText, quadrant, button);
                });
                button.setAttribute('data-listener-attached', 'true');
            }
        }
    });
}

/**
 * Initialize Interactive Mode functionality
 */
function initializeInteractiveMode() {
    // RESTORE BOARD SELECTION FROM STORAGE FIRST
    // This must happen before any other initialization
    if (restoreCurrentBoard()) {
        // If board restoration triggered a navigation, stop here
        return;
    }
    
    // Save current board to localStorage for future restoration
    saveCurrentBoard();
    
    const interactiveGapsModal = document.getElementById('interactive-gaps-modal');
    const interactiveGapsInput = document.getElementById('interactive-gaps-input');
    const interactiveGapsSend = document.getElementById('interactive-gaps-send');
    const interactiveGapsClose = document.getElementById('interactive-gaps-close');
    const interactiveGapsLink = document.getElementById('interactive-gaps-link');
    const minimizedIcon = document.getElementById('interactive-gaps-minimized-icon');
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');

    console.log('[DEBUG] interactiveGapsModal found:', !!interactiveGapsModal);
    console.log('[DEBUG] minimizedIcon found:', !!minimizedIcon);
    console.log('[DEBUG] interactiveGapsLink found:', !!interactiveGapsLink);

    // RESTORE MINIMIZED STATE FROM STORAGE
    if (minimizedIcon) {
        const isMinimized = localStorage.getItem('interactive-gaps-minimized') === 'true';
        if (isMinimized) {
            // Restore minimized state
            minimizedIcon.style.display = 'flex';
            console.log('[DEBUG] Restored minimized state from storage');
        } else {
            // Default to hidden
            minimizedIcon.style.display = 'none';
            console.log('[DEBUG] Interactive Mode not minimized, hiding restore icon');
        }
    }
    
    // Close modal functionality
    const closeModal = () => {
        interactiveGapsModal.style.display = 'none';
        document.body.classList.remove('interactive-mode-active');
        saveConversationContent();
    };
    
    // Close button event listener
    if (interactiveGapsClose) {
        interactiveGapsClose.addEventListener('click', closeModal);
    }
    
    // RESTORE CONVERSATION CONTENT FROM STORAGE
    // Wait a bit for the DOM to be fully ready, then restore conversation
    setTimeout(() => {
        if (window.boardId) {
            const restored = restoreConversationContent();
            if (restored) {
                console.log('[DEBUG] Conversation content restored on page load');
            }
        }
    }, 100);
    
    // Setup info dropdown functionality
    const infoButton = document.getElementById('interactive-gaps-info');
    const infoDropdown = document.getElementById('interactive-gaps-info-dropdown');
    const resetConversationLink = document.getElementById('reset-conversation');
    
    if (infoButton && infoDropdown) {
        // Toggle dropdown on info button click
        infoButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const isVisible = infoDropdown.style.display === 'block';
            infoDropdown.style.display = isVisible ? 'none' : 'block';
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!infoButton.contains(e.target) && !infoDropdown.contains(e.target)) {
                infoDropdown.style.display = 'none';
            }
        });
    }
    
    if (resetConversationLink) {
        resetConversationLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Clear the chat display
            const chatDiv = document.getElementById('interactive-gaps-chat');
            if (chatDiv) {
                chatDiv.innerHTML = '';
            }
            
            // Clear the input field
            const inputField = document.getElementById('interactive-gaps-input');
            if (inputField) {
                inputField.value = '';
            }
            
            // Reset conversation state in session storage if needed
            if (typeof(Storage) !== "undefined") {
                sessionStorage.removeItem('interactive_gaps_conversation');
            }
            
            // Hide the dropdown
            if (infoDropdown) {
                infoDropdown.style.display = 'none';
            }
            
            // Show confirmation message
            const chatDiv2 = document.getElementById('interactive-gaps-chat');
            if (chatDiv2) {
                chatDiv2.innerHTML = '<div style="color:#666;font-style:italic;text-align:center;padding:2em;">Conversation has been reset. Start a new conversation by typing below.</div>';
            }
            
            console.log('[DEBUG] Conversation reset completed');
        });
    }
    
    // Setup main page Reset Conversation functionality
    const resetConversationMain = document.getElementById('reset-conversation-main');
    if (resetConversationMain) {
        resetConversationMain.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get current board ID
            const boardId = window.boardId || null;
            if (!boardId) {
                console.error('[DEBUG] No board ID found for reset conversation');
                return;
            }
            
            // Call backend to clear conversation history from database
            fetch('/reset_conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    board_id: boardId
                })
            })
            .then(response => response.json())
            .then(result => {
                console.log('[DEBUG] Reset conversation result:', result);
                if (result.success) {
                    console.log('[DEBUG] Conversation history cleared from database');
                } else {
                    console.error('[DEBUG] Failed to clear conversation history:', result.error);
                }
            })
            .catch(error => {
                console.error('[DEBUG] Error calling reset conversation API:', error);
            });
            
            // Clear the Interactive Mode chat if it exists
            const chatDiv = document.getElementById('interactive-gaps-chat');
            if (chatDiv) {
                chatDiv.innerHTML = '<div style="color:#666;font-style:italic;text-align:center;padding:2em;">Conversation has been reset. Start a new conversation by typing below.</div>';
                
                // Clear conversation history
                interactiveGapsHistory = [];
                suggestionRenderCount = 0;
                
                // Clear saved conversation content from localStorage
                const boardId = window.boardId || 'default';
                localStorage.removeItem(`interactive-gaps-conversation-${boardId}`);
                console.log('[DEBUG] Conversation content cleared from localStorage');
                
                console.log('[DEBUG] Interactive Mode conversation cleared');
            }
            
            // Reset conversation state in session storage
            if (typeof(Storage) !== "undefined") {
                sessionStorage.removeItem('interactive_gaps_conversation');
            }
            
            // Hide the main dropdown menu
            const mainDropdown = document.getElementById('board-menu-dropdown');
            if (mainDropdown) {
                mainDropdown.style.display = 'none';
            }
            
            // Show notification
            showNotification('Interactive conversation has been reset', 'success');
            
            console.log('[DEBUG] Main page conversation reset completed');
        });
    }

    if (!interactiveGapsLink) {
        console.log('[DEBUG] interactiveGapsLink NOT found at DOMContentLoaded');
        return;
    }

    console.log('[DEBUG] interactiveGapsLink found at DOMContentLoaded');

    // Open or restore Interactive Mode
    interactiveGapsLink.addEventListener('click', function(e) {
        console.log('[DEBUG] Interactive mode link clicked');
        console.log('[DEBUG] Current modal display style:', interactiveGapsModal ? interactiveGapsModal.style.display : 'modal is null');
        e.preventDefault();
        
        if (!interactiveGapsModal) {
            console.log('[DEBUG] interactiveGapsModal is null!');
            return;
        }
        
        // Check if modal is already visible (not minimized)
        const isCurrentlyVisible = interactiveGapsModal.style.display === 'flex';
        console.log('[DEBUG] Modal current state - display:', interactiveGapsModal.style.display, 'visible:', isCurrentlyVisible);
        
        if (isCurrentlyVisible) {
            console.log('[DEBUG] Modal already visible, ignoring click');
            return;
        }
        
        console.log('[DEBUG] Modal is minimized or closed, restoring...');
        
        // Hide minimized icon if it's showing
        minimizedIcon.style.display = 'none';
        
        // Show the modal with complete reset
        console.log('[DEBUG] About to show modal - current display:', interactiveGapsModal.style.display);
        
        // Force complete modal reset with EXTREME visual debugging
        interactiveGapsModal.style.display = 'block';
        document.body.classList.add('interactive-mode-active');
        interactiveGapsModal.style.visibility = 'visible';
        interactiveGapsModal.style.opacity = '1';
        interactiveGapsModal.style.position = 'fixed';
        interactiveGapsModal.style.zIndex = '9999';
        interactiveGapsModal.style.left = '0';
        interactiveGapsModal.style.top = '0';
        interactiveGapsModal.style.width = '100vw';
        interactiveGapsModal.style.height = '100vh';
        interactiveGapsModal.style.alignItems = 'center';
        interactiveGapsModal.style.justifyContent = 'center';
        
        // Restore normal modal styling
        interactiveGapsModal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)'; // Semi-transparent background
        interactiveGapsModal.style.border = 'none'; // No border
        interactiveGapsModal.style.boxShadow = 'none'; // No glow
        
        // Ensure modal content is properly styled
        const modalContent = interactiveGapsModal.querySelector('#interactive-gaps-modal-content');
        if (modalContent) {
            modalContent.style.backgroundColor = '#fff';
            modalContent.style.border = 'none';
            modalContent.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
            modalContent.style.borderRadius = '10px';
            modalContent.style.zIndex = '10000';
        }
        
        console.log('[DEBUG] Modal completely reset and positioned');
        
        // Force a reflow to ensure styles are applied
        interactiveGapsModal.offsetHeight;
        console.log('[DEBUG] Forced reflow completed');
        
        // Debug: Check actual computed styles
        const computedStyle = window.getComputedStyle(interactiveGapsModal);
        console.log('[DEBUG] Modal computed styles after reset:');
        console.log('  display:', computedStyle.display);
        console.log('  visibility:', computedStyle.visibility);
        console.log('  opacity:', computedStyle.opacity);
        console.log('  position:', computedStyle.position);
        console.log('  z-index:', computedStyle.zIndex);
        console.log('  left:', computedStyle.left);
        console.log('  top:', computedStyle.top);
        console.log('  width:', computedStyle.width);
        console.log('  height:', computedStyle.height);
        
        // Check if modal is actually visible in viewport
        const rect = interactiveGapsModal.getBoundingClientRect();
        console.log('[DEBUG] Modal bounding rect:', rect);
        console.log('[DEBUG] Modal is in viewport:', rect.width > 0 && rect.height > 0);
        
        // Only initialize conversation if chat is completely empty (first time opening)
        const chatContent = document.getElementById('interactive-gaps-chat');
        const chatHTML = chatContent ? chatContent.innerHTML.trim() : '';
        
        // Check if chat has real conversation content (not just reset message)
        const isResetMessage = chatHTML.includes('Conversation has been reset') || chatHTML.includes('Start a new conversation');
        const hasRealChat = chatHTML !== '' && !isResetMessage;
        
        if (!hasRealChat) {
            console.log('[DEBUG] No existing conversation - initializing with current quadrant thoughts');
            suggestionRenderCount = 0;

            // Gather current quadrants
            const statusList = getQuadrantListById('status-list');
            const goalList = getQuadrantListById('goal-list');
            const analysisList = getQuadrantListById('analysis-list');
            const planList = getQuadrantListById('plan-list');

            const quadrants = {
                status: statusList,
                goal: goalList,
                analysis: analysisList,
                plan: planList
            };

            console.log('[DEBUG] Quadrants on modal open:', quadrants);
            initializeConversation(quadrants);
        } else {
            console.log('[DEBUG] Existing conversation found - restoring modal without reinitializing');
        }
        
        // Always focus input when modal opens/restores
        if (interactiveGapsInput) {
            interactiveGapsInput.focus();
        }
    });

    // Close Interactive Mode
    if (interactiveGapsClose) {
        interactiveGapsClose.addEventListener('click', function() {
            interactiveGapsModal.style.display = 'none';
            minimizedIcon.style.display = 'none';
        });
    }
    
    // Restore from minimized icon
    if (minimizedIcon) {
        minimizedIcon.addEventListener('click', function() {
            console.log('[DEBUG] Minimized icon clicked, restoring modal');
            minimizedIcon.style.display = 'none';
            
            // Clear minimized state from localStorage
            localStorage.removeItem('interactive-gaps-minimized');
            
            // Use the same restore logic as the Interactive Mode button
            // Force complete modal reset with EXTREME visual debugging
            interactiveGapsModal.style.display = 'block';
            document.body.classList.add('interactive-mode-active');
            interactiveGapsModal.style.visibility = 'visible';
            interactiveGapsModal.style.opacity = '1';
            interactiveGapsModal.style.position = 'fixed';
            interactiveGapsModal.style.zIndex = '9999';
            interactiveGapsModal.style.left = '0';
            interactiveGapsModal.style.top = '0';
            interactiveGapsModal.style.width = '100vw';
            interactiveGapsModal.style.height = '100vh';
            interactiveGapsModal.style.alignItems = 'center';
            interactiveGapsModal.style.justifyContent = 'center';
            
            // Restore normal modal styling
            interactiveGapsModal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            interactiveGapsModal.style.border = 'none';
            interactiveGapsModal.style.boxShadow = 'none';
            
            // Ensure modal content is properly styled
            const modalContent = interactiveGapsModal.querySelector('#interactive-gaps-modal-content');
            if (modalContent) {
                modalContent.style.backgroundColor = '#fff';
                modalContent.style.border = 'none';
                modalContent.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
                modalContent.style.borderRadius = '10px';
                modalContent.style.zIndex = '10000';
            }
            
            console.log('[DEBUG] Modal restored from minimized icon');
            
            // Focus input
            if (interactiveGapsInput) {
                interactiveGapsInput.focus();
            }
        });
    }

    // Send message
    if (interactiveGapsSend) {
        interactiveGapsSend.addEventListener('click', function() {
            sendInteractiveMessage();
        });
    }

    // Enter key to send
    if (interactiveGapsInput) {
        interactiveGapsInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                interactiveGapsSend.click();
            }
        });
    }

    // Setup draggable functionality
    setupDraggableModal(interactiveGapsModal);
}

/**
 * Initialize conversation with AI
 */
function initializeConversation(quadrants) {
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    const boardId = window.boardId || null;

    if (!boardId) {
        interactiveGapsChat.innerHTML = "<div style='color:#c00;'>No board selected. Please select a board first.</div>";
        return;
    }

    console.log('[DEBUG] About to fetch /interactive_gaps', { board_id: boardId, user_input: "", quadrants: quadrants });

    fetch('/interactive_gaps', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            board_id: boardId,
            user_input: "",
            quadrants: quadrants
        })
    })
    .then(response => {
        console.log('[DEBUG] Response status:', response.status);
        if (!response.ok) {
            console.log('[DEBUG] Response not ok, status:', response.status);
            return response.json().then(errorData => {
                throw new Error(`Server error ${response.status}: ${errorData.error || errorData.message || 'Unknown error'}`);
            });
        }
        return response.json();
    })
    .then(result => {
        console.log('[DEBUG] Backend result:', result);
        
        console.log('[DEBUG] Interactive Mode initial response:', result);
        if (result.reply) {
            displayAIMessage(result.reply);
            interactiveGapsHistory.push({ role: 'assistant', content: result.reply });
            
            // Handle suggestions if present and not empty (same as user message handling)
            if (result.suggestions && Array.isArray(result.suggestions.add_to_quadrant) && result.suggestions.add_to_quadrant.length > 0) {
                displaySuggestions(result.suggestions.add_to_quadrant);
            }
        } else if (result.suggestions && Array.isArray(result.suggestions.add_to_quadrant) && result.suggestions.add_to_quadrant.length > 0) {
            // Handle case where backend only returns suggestions (smart categorization without reply text)
            console.log('[DEBUG] Backend returned suggestions without reply text - processing categorization');
            displaySuggestions(result.suggestions.add_to_quadrant);
            displayAIMessage("I've categorized your input. What would you like to explore next?");
        } else if (result.error) {
            interactiveGapsChat.innerHTML = `<div style='color:#c00;'>Error: ${result.error}</div>`;
        } else {
            console.log('[DEBUG] No result.reply or suggestions found in response:', result);
            interactiveGapsChat.innerHTML = "<div style='color:#c00;'>No response from AI.</div>";
        }
    })
    .catch(err => {
        console.error('[DEBUG] Error:', err);
        interactiveGapsChat.innerHTML = "<div style='color:#c00;'>Error contacting AI. Please try again.</div>";
    });
}

/**
 * Send user message to AI
 */
function sendInteractiveMessage() {
    const interactiveGapsInput = document.getElementById('interactive-gaps-input');
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    const boardId = window.boardId || null;

    if (!interactiveGapsInput || !boardId) return;

    const userInput = interactiveGapsInput.value.trim();
    if (!userInput) return;

    // Display user message
    interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#333;'><b>You:</b> ${userInput}</div>`;
    interactiveGapsHistory.push({ role: 'user', content: userInput });
    
    // Save conversation content after adding user message
    saveConversationContent();

    // Gather current quadrants
    const quadrants = {
        status: getQuadrantListById('status-list'),
        goal: getQuadrantListById('goal-list'),
        analysis: getQuadrantListById('analysis-list'),
        plan: getQuadrantListById('plan-list')
    };

    // Send to backend
    fetch('/interactive_gaps', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            board_id: boardId,
            user_input: userInput,
            quadrants: quadrants,
            history: interactiveGapsHistory
        })
    })
    .then(response => response.json())
    .then(result => {
        console.log('[DEBUG] Backend result:', result);
        
        console.log('[DEBUG] Interactive Mode user message response:', result);
        if (result.reply) {
            displayAIMessage(result.reply);
            interactiveGapsHistory.push({ role: 'assistant', content: result.reply });
            
            // Store the last user input for context in move detection
            window.lastUserInput = userInput;
            
            // Handle suggestions if present and not empty
            if (result.suggestions && Array.isArray(result.suggestions.add_to_quadrant) && result.suggestions.add_to_quadrant.length > 0) {
                // Auto-add suggestions directly to quadrants instead of showing buttons
                autoAddSuggestions(result.suggestions.add_to_quadrant).then(() => {
                    // Parse AI response for direct move commands AFTER auto-addition completes
                    setTimeout(() => {
                        parseAndExecuteDirectMoves(result.reply);
                        parseAndExecuteDirectMoves(userInput);
                    }, 200); // Small delay to ensure DOM updates are complete
                });
            } else {
                // No auto-addition needed, parse moves immediately
                setTimeout(() => {
                    parseAndExecuteDirectMoves(result.reply);
                    parseAndExecuteDirectMoves(userInput);
                }, 100);
            }
        } else if (result.error) {
            interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#c00;'><b>GAPS:</b> Error: ${result.error}</div>`;
        } else {
            console.log('[DEBUG] No result.reply found in user message response:', result);
            interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#c00;'><b>GAPS:</b> No response from AI.</div>`;
        }
        
        interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
    })
    .catch(err => {
        console.error('[DEBUG] Error:', err);
        interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#c00;'><b>GAPS:</b> Error contacting AI. Please try again.</div>`;
        interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
    });

    interactiveGapsInput.value = '';
    interactiveGapsInput.focus();
}

/**
 * Display AI message with proper formatting
 */
function displayAIMessage(message) {
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    const formattedMessage = message.replace(/\n/g, '<br>');
    
    // Check if chat only contains reset message - if so, replace it instead of appending
    const currentContent = interactiveGapsChat.innerHTML.trim();
    const isResetMessage = currentContent.includes('Conversation has been reset') || currentContent.includes('Start a new conversation');
    
    if (isResetMessage) {
        // Replace reset message with AI response
        interactiveGapsChat.innerHTML = `<div style='margin-top:0.7em;color:#007bff;'><b>GAPS:</b> <span style='color:#444;'>${formattedMessage}</span></div>`;
    } else {
        // Append to existing conversation
        interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#007bff;'><b>GAPS:</b> <span style='color:#444;'>${formattedMessage}</span></div>`;
    }
    
    interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
    
    // Save conversation content to localStorage
    saveConversationContent();
}

/**
 * Automatically add suggestions directly to quadrants (no manual clicking required)
 */
async function autoAddSuggestions(suggestions) {
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    const boardId = window.boardId || null;
    
    if (!boardId) {
        console.error('No board selected for auto-adding suggestions');
        return;
    }
    
    let addedItems = [];
    let failedItems = [];
    
    // Add a status message to chat
    interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#007bff;font-style:italic;'><b>Adding items to quadrants...</b></div>`;
    interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
    
    // Process each suggestion
    for (const item of suggestions) {
        if (item.quadrant && item.thought) {
            try {
                const resp = await fetch('/add_thought', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({
                        content: item.thought,
                        quadrant: item.quadrant,
                        board_id: boardId
                    })
                });
                
                const result = await resp.json();
                
                if (result.success) {
                    // Update quadrants in background
                    const thoughtId = result.thought && result.thought.id ? result.thought.id : null;
                    
                    if (typeof window.updateQuadrantInBackground === 'function') {
                        window.updateQuadrantInBackground(item.quadrant, item.thought, thoughtId);
                    } else if (typeof window.refreshQuadrants === 'function') {
                        window.refreshQuadrants();
                    }
                    
                    addedItems.push(`${item.quadrant}: ${item.thought}`);
                    console.log(`[DEBUG] Auto-added: ${item.thought} to ${item.quadrant}`);
                } else {
                    failedItems.push(`${item.quadrant}: ${item.thought}`);
                    console.error(`Failed to auto-add: ${item.thought} to ${item.quadrant}:`, result.error);
                }
            } catch (error) {
                failedItems.push(`${item.quadrant}: ${item.thought}`);
                console.error(`Error auto-adding: ${item.thought} to ${item.quadrant}:`, error);
            }
            
            // Small delay to avoid overwhelming the server
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }
    
    // Show completion status
    if (addedItems.length > 0) {
        const itemsList = addedItems.map(item => `• ${item}`).join('<br>');
        interactiveGapsChat.innerHTML += `<div style='margin-top:0.5em;color:#28a745;font-size:0.9em;'><b>✓ Added ${addedItems.length} items:</b><br>${itemsList}</div>`;
    }
    
    if (failedItems.length > 0) {
        const failedList = failedItems.map(item => `• ${item}`).join('<br>');
        interactiveGapsChat.innerHTML += `<div style='margin-top:0.5em;color:#dc3545;font-size:0.9em;'><b>✗ Failed to add ${failedItems.length} items:</b><br>${failedList}</div>`;
    }
    
    interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
    
    // Save conversation content
    saveConversationContent();
}

/**
 * Display AI suggestions with action buttons (legacy function - now replaced by autoAddSuggestions)
 */
function displaySuggestions(suggestions) {
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    
    let sugHtml = `<div class='ai-suggest-label' style='margin:0.7em 0 0.2em 0;font-weight:bold;color:#007bff;'>GAPS suggests adding the following:</div>`;
    
    suggestions.forEach(function(item, idx) {
        if (item.quadrant && item.thought) {
            const btnId = `add-to-quadrant-btn-${suggestionRenderCount}-${idx}`;
            sugHtml += `
                <div style='margin-bottom:0.3em;padding:0.3em 0.5em;background:#f5faff;border-radius:6px;'>
                    <span style='color:#007bff;font-weight:bold;'>${item.quadrant.charAt(0).toUpperCase() + item.quadrant.slice(1)}:</span>
                    <span class='ai-suggested-thought'>${item.thought}</span>
                    <button id='${btnId}' data-thought='${item.thought.replace(/'/g, '&apos;')}' data-quadrant='${item.quadrant}' style='margin-left:0.7em;font-size:0.95em;padding:0.2em 0.7em;background:#007bff;color:#fff;border:none;border-radius:4px;cursor:pointer;'>Add to Quadrant</button>
                </div>`;
            
            // Add event listener for the button
            setTimeout(() => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', async function() {
                        await addSuggestedThought(item.thought, item.quadrant, btn);
                    });
                    btn.setAttribute('data-listener-attached', 'true');
                }
            }, 0);
        }
    });
    
    interactiveGapsChat.innerHTML += `<div id="ai-suggestion-box">${sugHtml}</div>`;
    suggestionRenderCount++;
    
    // Save conversation content after adding suggestions
    saveConversationContent();
}

/**
 * Move existing thought to different quadrant directly
 */
async function moveThoughtDirectly(thoughtId, fromQuadrant, toQuadrant, thoughtContent) {
    const boardId = window.boardId || null;
    
    if (!boardId) {
        console.error('No board selected for direct move');
        return false;
    }
    
    try {
        const resp = await fetch('/move_thought', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                thought_id: thoughtId,
                new_quadrant: toQuadrant,
                board_id: boardId
            })
        });
        
        const result = await resp.json();
        
        if (result.success) {
            // Update quadrants in background
            if (window.updateQuadrantInBackground) {
                window.updateQuadrantInBackground(fromQuadrant, result.quadrants[fromQuadrant] || []);
                window.updateQuadrantInBackground(toQuadrant, result.quadrants[toQuadrant] || []);
            }
            
            // Add confirmation message to chat
            const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
            if (interactiveGapsChat) {
                interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#28a745;font-style:italic;'><b>✓ Moved:</b> "${thoughtContent}" from ${fromQuadrant} to ${toQuadrant}</div>`;
                interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
            }
            
            console.log(`[DEBUG] Successfully moved thought from ${fromQuadrant} to ${toQuadrant}`);
            return true;
        } else {
            console.error('Failed to move thought:', result.error);
            return false;
        }
    } catch (error) {
        console.error('Error moving thought directly:', error);
        return false;
    }
}

// Store pending move suggestions for when user agrees
let pendingMovesSuggestions = [];

/**
 * Parse AI response for direct move suggestions and execute them
 */
function parseAndExecuteDirectMoves(aiResponse) {
    console.log('[DEBUG] Parsing AI response for moves:', aiResponse);
    
    // Pattern 1: Direct move commands like "Let me move [item] from [quadrant] to [quadrant]"
    const directMovePattern = /(?:let me move|moving|move)\s+["']([^"']+)["']\s+from\s+(\w+)\s+to\s+(\w+)/gi;
    const directMatches = [...aiResponse.matchAll(directMovePattern)];
    
    console.log('[DEBUG] Direct move matches:', directMatches);
    directMatches.forEach(match => {
        const [, thoughtContent, fromQuadrant, toQuadrant] = match;
        console.log(`[DEBUG] Executing direct move: "${thoughtContent}" from ${fromQuadrant} to ${toQuadrant}`);
        executeMove(thoughtContent, fromQuadrant, toQuadrant);
    });
    
    // Pattern 2: Past tense confirmations like "I've moved [item] to the [quadrant] quadrant"
    const pastTensePattern = /(?:i've moved|i moved|moved)\s+["']([^"']+)["']\s+(?:exclusively\s+)?to\s+the\s+(\w+)\s+quadrant/gi;
    const pastTenseMatches = [...aiResponse.matchAll(pastTensePattern)];
    
    console.log('[DEBUG] Past tense matches:', pastTenseMatches);
    pastTenseMatches.forEach(match => {
        const [, thoughtContent, toQuadrant] = match;
        const fromQuadrant = findThoughtCurrentQuadrant(thoughtContent);
        console.log(`[DEBUG] Past tense move - thought: "${thoughtContent}", from: ${fromQuadrant}, to: ${toQuadrant}`);
        if (fromQuadrant && fromQuadrant !== toQuadrant.toLowerCase()) {
            console.log(`[DEBUG] AI confirmed move: "${thoughtContent}" to ${toQuadrant}`);
            executeMove(thoughtContent, fromQuadrant, toQuadrant);
        }
    });
    
    // Pattern 2b: Generic adjustment confirmations like "I've made that adjustment"
    const adjustmentPattern = /(?:i've made that adjustment|i've made the adjustment|made that adjustment)/gi;
    if (adjustmentPattern.test(aiResponse) && pendingMovesSuggestions.length > 0) {
        console.log(`[DEBUG] AI confirmed adjustment, executing ${pendingMovesSuggestions.length} pending moves`);
        pendingMovesSuggestions.forEach(move => {
            executeMove(move.thoughtContent, move.fromQuadrant, move.toQuadrant);
        });
        pendingMovesSuggestions = []; // Clear after execution
    }
    
    // Pattern 3: Suggestion patterns like "I'd suggest moving [item] to the [quadrant] quadrant"
    const suggestionPattern = /(?:i'd suggest|i suggest|suggest|i'd recommend|i recommend|recommend)\s+(?:moving|adding|placing)\s+["']([^"']+)["']\s+(?:in|to)\s+the\s+(\w+)\s+quadrant/gi;
    const suggestionMatches = [...aiResponse.matchAll(suggestionPattern)];
    
    console.log('[DEBUG] Suggestion matches:', suggestionMatches);
    if (suggestionMatches.length > 0) {
        // Store pending moves for when user agrees
        pendingMovesSuggestions = [];
        suggestionMatches.forEach(match => {
            const [, thoughtContent, toQuadrant] = match;
            const fromQuadrant = findThoughtCurrentQuadrant(thoughtContent);
            console.log(`[DEBUG] Suggestion - thought: "${thoughtContent}", from: ${fromQuadrant}, to: ${toQuadrant}`);
            if (fromQuadrant) {
                pendingMovesSuggestions.push({
                    thoughtContent: thoughtContent.trim(),
                    fromQuadrant: fromQuadrant,
                    toQuadrant: toQuadrant.toLowerCase()
                });
                console.log(`[DEBUG] Stored pending move: "${thoughtContent}" from ${fromQuadrant} to ${toQuadrant}`);
            }
        });
    }
    
    // Pattern 4: User agreement - look for "I agree", "yes", "okay", etc.
    const agreementPattern = /\b(?:i agree|yes|okay|ok|sure|that's right|correct|move it)\b/gi;
    const agreementMatch = agreementPattern.test(aiResponse);
    console.log(`[DEBUG] Agreement test - pattern match: ${agreementMatch}, pending moves: ${pendingMovesSuggestions.length}`);
    console.log(`[DEBUG] Current pending moves:`, pendingMovesSuggestions);
    
    if (agreementMatch && pendingMovesSuggestions.length > 0) {
        console.log(`[DEBUG] User agreed, executing ${pendingMovesSuggestions.length} pending moves`);
        pendingMovesSuggestions.forEach(move => {
            executeMove(move.thoughtContent, move.fromQuadrant, move.toQuadrant);
        });
        pendingMovesSuggestions = []; // Clear after execution
    }
}

/**
 * Find which quadrant currently contains a thought
 */
function findThoughtCurrentQuadrant(thoughtContent) {
    const quadrants = ['goals', 'analysis', 'plans', 'status'];
    console.log(`[DEBUG] Looking for thought: "${thoughtContent}" in quadrants`);
    
    for (const quadrant of quadrants) {
        const list = document.getElementById(`${quadrant}-list`);
        if (list) {
            const thoughtItems = list.querySelectorAll('.thought-item');
            console.log(`[DEBUG] Checking ${quadrant} quadrant with ${thoughtItems.length} items`);
            for (const item of thoughtItems) {
                const content = item.querySelector('.thought-content')?.textContent?.trim();
                console.log(`[DEBUG] Comparing "${content}" with "${thoughtContent.trim()}"`);
                if (content && content.toLowerCase().includes(thoughtContent.trim().toLowerCase())) {
                    console.log(`[DEBUG] Found thought in ${quadrant} quadrant`);
                    return quadrant;
                }
            }
        }
    }
    console.log(`[DEBUG] Thought not found in any quadrant`);
    return null;
}

/**
 * Execute a move operation
 */
function executeMove(thoughtContent, fromQuadrant, toQuadrant) {
    const fromList = document.getElementById(`${fromQuadrant.toLowerCase()}-list`);
    if (fromList) {
        const thoughtItems = fromList.querySelectorAll('.thought-item');
        for (const item of thoughtItems) {
            const content = item.querySelector('.thought-content')?.textContent?.trim();
            if (content && content.includes(thoughtContent.trim())) {
                const thoughtId = item.getAttribute('data-thought-id');
                if (thoughtId) {
                    console.log(`[DEBUG] Executing move: "${thoughtContent}" from ${fromQuadrant} to ${toQuadrant}`);
                    moveThoughtDirectly(thoughtId, fromQuadrant.toLowerCase(), toQuadrant.toLowerCase(), content);
                    break;
                }
            }
        }
    }
}

/**
 * Add suggested thought to quadrant
 */
async function addSuggestedThought(thought, quadrant, button) {
    const boardId = window.boardId || null;
    
    if (!boardId) {
        alert('No board selected.');
        return;
    }
    
    try {
        const resp = await fetch('/add_thought', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                content: thought,
                quadrant: quadrant,
                board_id: boardId
            })
        });
        
        const result = await resp.json();
        
        if (result.success) {
            // Update quadrants in background without refreshing page (to keep modal open)
            // Pass the returned thought_id so delete buttons work properly
            const thoughtId = result.thought && result.thought.id ? result.thought.id : null;
            console.log('[DEBUG] Received thought_id from backend:', thoughtId);
            
            if (typeof window.updateQuadrantInBackground === 'function') {
                window.updateQuadrantInBackground(quadrant, thought, thoughtId);
            } else if (typeof window.refreshQuadrants === 'function') {
                // Fallback: only refresh if background update not available
                console.log('[DEBUG] Background update not available, using full refresh');
                window.refreshQuadrants();
            }
            
            button.disabled = true;
            button.textContent = 'Added!';
            button.style.background = '#5cb85c';
            button.style.color = '#fff';
            
            if (typeof showNotification === 'function') {
                showNotification('Thought added to ' + quadrant + '!', false);
            }
        } else {
            alert('Failed to save thought: ' + (result.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Error saving thought: ' + err.message);
    }
}

/**
 * Setup draggable functionality for the modal
 */
function setupDraggableModal(interactiveGapsModal) {
    if (!interactiveGapsModal) {
        console.log('[DRAG DEBUG] interactiveGapsModal not found');
        return;
    }

    console.log('[DRAG DEBUG] Checking for interactiveGapsModal:', interactiveGapsModal);
    
    const modalContent = interactiveGapsModal.querySelector('#interactive-gaps-modal-content');
    console.log('[DRAG DEBUG] modalContent found:', modalContent);
    
    const header = modalContent ? modalContent.querySelector('div:first-child') : null;
    console.log('[DRAG DEBUG] header found:', header);
    
    let isDragging = false, offsetX = 0, offsetY = 0;
    
    if (header && modalContent) {
        console.log('[DRAG DEBUG] Setting up draggable functionality');
        header.style.cursor = 'move';
        header.style.backgroundColor = '#e6f3ff'; // Visual indicator
        
        header.addEventListener('mousedown', function(e) {
            console.log('[DRAG DEBUG] Mousedown on header, target:', e.target.id);
            
            // Don't drag if clicking on the minimize button - minimize modal instead
            if (e.target.id === 'interactive-gaps-minimize') {
                console.log('[DRAG DEBUG] Clicked minimize button, minimizing modal');
                interactiveGapsModal.style.display = 'none';
                
                try {
                    // Get the minimized icon element directly (scope fix)
                    const minimizedIcon = document.getElementById('interactive-gaps-minimized-icon');
                    console.log('[DEBUG] minimizedIcon element (from DOM):', minimizedIcon);
                    
                    if (!minimizedIcon) {
                        console.error('[ERROR] minimizedIcon is null! Cannot show restore icon.');
                        return;
                    }
                    
                    console.log('[DEBUG] Setting minimizedIcon display to flex');
                    minimizedIcon.style.display = 'flex';
                    
                    // Save minimized state to localStorage
                    localStorage.setItem('interactive-gaps-minimized', 'true');
                    
                    // Check if it was set properly
                    console.log('[DEBUG] minimizedIcon display after setting:', minimizedIcon.style.display);
                    console.log('[DEBUG] minimizedIcon computed style:', window.getComputedStyle(minimizedIcon).display);
                    console.log('[DEBUG] minimizedIcon position:', window.getComputedStyle(minimizedIcon).position);
                    console.log('[DEBUG] minimizedIcon bottom:', window.getComputedStyle(minimizedIcon).bottom);
                    console.log('[DEBUG] minimizedIcon left:', window.getComputedStyle(minimizedIcon).left);
                    console.log('[DEBUG] minimizedIcon z-index:', window.getComputedStyle(minimizedIcon).zIndex);
                    
                    console.log('[DEBUG] Modal minimized, showing restore icon, state saved to localStorage');
                } catch (error) {
                    console.error('[ERROR] Failed to show minimized icon:', error);
                }
                
                return;
            }
            
            console.log('[DRAG DEBUG] Starting drag');
            isDragging = true;
            const rect = modalContent.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            document.body.style.userSelect = 'none';
            
            // Change modal positioning to allow dragging
            interactiveGapsModal.style.alignItems = 'flex-start';
            interactiveGapsModal.style.justifyContent = 'flex-start';
            modalContent.style.margin = '0';
            modalContent.style.position = 'relative';
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            const newLeft = e.clientX - offsetX;
            const newTop = e.clientY - offsetY;
            
            // Keep modal within viewport bounds
            const maxLeft = window.innerWidth - modalContent.offsetWidth;
            const maxTop = window.innerHeight - modalContent.offsetHeight;
            
            const finalLeft = Math.max(0, Math.min(newLeft, maxLeft));
            const finalTop = Math.max(0, Math.min(newTop, maxTop));
            
            modalContent.style.left = finalLeft + 'px';
            modalContent.style.top = finalTop + 'px';
            console.log('[DRAG DEBUG] Moving to:', finalLeft, finalTop);
        });
        
        document.addEventListener('mouseup', function() {
            if (isDragging) {
                console.log('[DRAG DEBUG] Ending drag');
            }
            isDragging = false;
            document.body.style.userSelect = '';
        });
    } else {
        console.log('[DRAG DEBUG] Header or modalContent not found - header:', !!header, 'modalContent:', !!modalContent);
    }
}

// Manual test function for debugging moves
window.testMove = function(thoughtText, toQuadrant) {
    console.log(`[TEST] Testing move of "${thoughtText}" to ${toQuadrant}`);
    const fromQuadrant = findThoughtCurrentQuadrant(thoughtText);
    console.log(`[TEST] Found in quadrant: ${fromQuadrant}`);
    
    if (fromQuadrant) {
        const fromList = document.getElementById(`${fromQuadrant}-list`);
        if (fromList) {
            const thoughtItems = fromList.querySelectorAll('.thought-item');
            for (const item of thoughtItems) {
                const content = item.querySelector('.thought-content')?.textContent?.trim();
                if (content && content.toLowerCase().includes(thoughtText.toLowerCase())) {
                    const thoughtId = item.getAttribute('data-thought-id');
                    console.log(`[TEST] Found thought ID: ${thoughtId}`);
                    if (thoughtId) {
                        moveThoughtDirectly(thoughtId, fromQuadrant, toQuadrant, content);
                        return;
                    }
                }
            }
        }
    }
    console.log(`[TEST] Could not find or move thought`);
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeInteractiveMode();
});
