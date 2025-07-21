/* GAPS Facilitator - Interactive Mode Module */

let interactiveGapsHistory = [];
let suggestionRenderCount = 0;

/**
 * Initialize Interactive Mode functionality
 */
function initializeInteractiveMode() {
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

    // ENSURE ICON IS HIDDEN INITIALLY
    if (minimizedIcon) {
        minimizedIcon.style.display = 'none';
        console.log('[DEBUG] Ensured minimized icon is hidden on page load');
    }
    
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
            }
            
            // Clear the input field
            const inputField = document.getElementById('interactive-gaps-input');
            if (inputField) {
                inputField.value = '';
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
        interactiveGapsModal.style.display = 'flex';
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
            
            // Use the same restore logic as the Interactive Mode button
            // Force complete modal reset with EXTREME visual debugging
            interactiveGapsModal.style.display = 'flex';
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
    .then(response => response.json())
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
            
            // Handle suggestions if present and not empty
            if (result.suggestions && Array.isArray(result.suggestions.add_to_quadrant) && result.suggestions.add_to_quadrant.length > 0) {
                displaySuggestions(result.suggestions.add_to_quadrant);
            }
        } else if (result.error) {
            interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#c00;'><b>AI:</b> Error: ${result.error}</div>`;
        } else {
            console.log('[DEBUG] No result.reply found in user message response:', result);
            interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#c00;'><b>AI:</b> No response from AI.</div>`;
        }
        
        interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
    })
    .catch(err => {
        console.error('[DEBUG] Error:', err);
        interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#c00;'><b>AI:</b> Error contacting AI. Please try again.</div>`;
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
        interactiveGapsChat.innerHTML = `<div style='margin-top:0.7em;color:#007bff;'><b>AI:</b> <span style='color:#444;'>${formattedMessage}</span></div>`;
    } else {
        // Append to existing conversation
        interactiveGapsChat.innerHTML += `<div style='margin-top:0.7em;color:#007bff;'><b>AI:</b> <span style='color:#444;'>${formattedMessage}</span></div>`;
    }
    
    interactiveGapsChat.scrollTop = interactiveGapsChat.scrollHeight;
}

/**
 * Display AI suggestions with action buttons
 */
function displaySuggestions(suggestions) {
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');
    
    let sugHtml = `<div class='ai-suggest-label' style='margin:0.7em 0 0.2em 0;font-weight:bold;color:#007bff;'>AI suggests adding the following:</div>`;
    
    suggestions.forEach(function(item, idx) {
        if (item.quadrant && item.thought) {
            const btnId = `add-to-quadrant-btn-${suggestionRenderCount}-${idx}`;
            sugHtml += `
                <div style='margin-bottom:0.3em;padding:0.3em 0.5em;background:#f5faff;border-radius:6px;'>
                    <span style='color:#007bff;font-weight:bold;'>${item.quadrant.charAt(0).toUpperCase() + item.quadrant.slice(1)}:</span>
                    <span class='ai-suggested-thought'>${item.thought}</span>
                    <button id='${btnId}' style='margin-left:0.7em;font-size:0.95em;padding:0.2em 0.7em;background:#007bff;color:#fff;border:none;border-radius:4px;cursor:pointer;'>Add to Quadrant</button>
                </div>`;
            
            // Add event listener for the button
            setTimeout(() => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', async function() {
                        await addSuggestedThought(item.thought, item.quadrant, btn);
                    });
                }
            }, 0);
        }
    });
    
    interactiveGapsChat.innerHTML += `<div id="ai-suggestion-box">${sugHtml}</div>`;
    suggestionRenderCount++;
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
            if (typeof window.updateQuadrantInBackground === 'function') {
                window.updateQuadrantInBackground(quadrant, thought);
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
                    
                    // Check if it was set properly
                    console.log('[DEBUG] minimizedIcon display after setting:', minimizedIcon.style.display);
                    console.log('[DEBUG] minimizedIcon computed style:', window.getComputedStyle(minimizedIcon).display);
                    console.log('[DEBUG] minimizedIcon position:', window.getComputedStyle(minimizedIcon).position);
                    console.log('[DEBUG] minimizedIcon bottom:', window.getComputedStyle(minimizedIcon).bottom);
                    console.log('[DEBUG] minimizedIcon left:', window.getComputedStyle(minimizedIcon).left);
                    console.log('[DEBUG] minimizedIcon z-index:', window.getComputedStyle(minimizedIcon).zIndex);
                    
                    console.log('[DEBUG] Modal minimized, showing restore icon');
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

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeInteractiveMode();
});
