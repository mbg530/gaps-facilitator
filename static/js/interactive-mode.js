/* GAPS Facilitator - Interactive Mode Module - Side-by-Side Layout */

let interactiveGapsHistory = [];

/**
 * Get current quadrant thoughts for AI initialization
 */
function getCurrentQuadrantThoughts() {
    const getQuadrantThoughts = (quadrantId) => {
        const quadrant = document.getElementById(quadrantId + '-list');
        if (!quadrant) return [];
        
        const thoughts = [];
        const thoughtItems = quadrant.querySelectorAll('.thought-item .thought-content');
        thoughtItems.forEach(item => {
            const text = item.textContent.trim();
            if (text) thoughts.push(text);
        });
        return thoughts;
    };
    
    return {
        status: getQuadrantThoughts('status'),
        goal: getQuadrantThoughts('goal'),
        analysis: getQuadrantThoughts('analysis'),
        plan: getQuadrantThoughts('plan')
    };
}

/**
 * Extract and apply JSON directives embedded in the AI reply text.
 * Supports blocks like:
 *   {"add_to_quadrant":[{"quadrant":"analysis","thought":"..."}]}
 * Also tolerates code fences and trailing commentary.
 */
function extractAndApplyJsonDirectivesFromReply(replyText) {
    if (!replyText || typeof replyText !== 'string') return;
    dlog('[DEBUG] Scanning AI reply for embedded JSON directives');

    // Remove code fences if present
    let text = replyText.replace(/```json\s*([\s\S]*?)\s*```/gi, '$1');

    // Try to find JSON object containing add_to_quadrant using a balanced-brace scan
    const idx = text.indexOf('"add_to_quadrant"');
    if (idx === -1) return; // nothing to do

    // Walk backwards to find the opening '{' and forwards to find the matching '}'
    let start = idx;
    while (start > 0 && text[start] !== '{') start--;
    if (text[start] !== '{') return;

    // Simple brace matching
    let depth = 0;
    let end = start;
    while (end < text.length) {
        const ch = text[end];
        if (ch === '{') depth++;
        if (ch === '}') {
            depth--;
            if (depth === 0) break;
        }
        end++;
    }
    if (depth !== 0) return; // unbalanced

    const candidate = text.slice(start, end + 1).trim();
    dlog('[DEBUG] Found embedded JSON candidate:', candidate);
    try {
        const obj = JSON.parse(candidate);
        if (obj && obj.add_to_quadrant) {
            addSuggestionsToQuadrants(obj);
        }
    } catch (e) {
        derror('[DEBUG] JSON.parse failed for embedded directives:', e);
    }
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

    dlog('[DEBUG] About to call postJSON(/interactive_gaps)', { board_id: boardId, user_input: "", quadrants: quadrants });

    postJSON('/interactive_gaps', {
        board_id: boardId,
        user_input: "",
        quadrants: quadrants
    })
    .then(result => {
        dlog('[DEBUG] Backend result:', result);
        
        if (result.reply) {
            // Handle suggestions FIRST (show added items before AI response)
            if (result.suggestions) {
                dlog('[DEBUG] Processing suggestions:', result.suggestions);
                addSuggestionsToQuadrants(result.suggestions);
            }
            // Also parse any JSON directives embedded in the reply text
            try {
                extractAndApplyJsonDirectivesFromReply(result.reply);
            } catch (e) {
                derror('[DEBUG] Failed to parse embedded JSON directives:', e);
            }
            
            // Check for move commands in AI response (minimal implementation)
            try {
                detectAndExecuteSimpleMoves(result.reply);
            } catch (error) {
                derror('[MOVE DEBUG] Error in move detection:', error);
                // Fail silently - don't break the conversation
            }
            
            // Then display AI message
            displayAIMessage(result.reply);
            interactiveGapsHistory.push({ role: 'assistant', content: result.reply });
        } else if (result.error) {
            interactiveGapsChat.innerHTML = `<div style='color:#c00;'>Error: ${result.error}</div>`;
        } else {
            interactiveGapsChat.innerHTML = "<div style='color:#c00;'>No response from AI.</div>";
        }
    })
    .catch(err => {
        if (err && err.status === 429) {
            displayAIMessage('The AI service is currently unavailable due to quota limits. Please try again later or set a valid API key in settings.');
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        derror('[DEBUG] Error:', err);
        interactiveGapsChat.innerHTML = `<div style='color:#c00;'>Error: ${err.message || 'Unknown error'}</div>`;
    });
}

/**
 * Open Interactive Mode
 */
function openInteractiveMode() {
    // Hide the toggle button and show the IM panel
    document.getElementById('interactive-mode-toggle').style.display = 'none';
    document.getElementById('im-panel').style.display = 'flex';
    document.getElementById('im-minimize-icon').style.display = 'flex';
    
    // Reset conversation on open
    resetConversation();
    
    // Initialize conversation
    const quadrants = getCurrentQuadrantThoughts();
    initializeConversation(quadrants);
}

/**
 * Send user message to AI
 */
function sendInteractiveMessage() {
    const input = document.getElementById('interactive-gaps-input');
    const chat = document.getElementById('interactive-gaps-chat');
    const userMessage = input.value.trim();
    
    if (!userMessage) return;
    
    // Add user message to chat
    const userDiv = document.createElement('div');
    userDiv.style.cssText = 'margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 5px;';
    userDiv.innerHTML = `<strong>You:</strong> ${userMessage}`;
    chat.appendChild(userDiv);
    
    // Clear input
    input.value = '';
    
    // Add to history
    interactiveGapsHistory.push({ role: 'user', content: userMessage });
    
    // Send to server via centralized API helper
    postJSON('/interactive_gaps', {
        board_id: window.boardId,
        user_input: userMessage,
        quadrants: getCurrentQuadrantThoughts()
    })
    .then(result => {
        if (result.reply) {
            // Handle suggestions FIRST (show added items before AI response)
            if (result.suggestions) {
                dlog('[DEBUG] Processing suggestions:', result.suggestions);
                addSuggestionsToQuadrants(result.suggestions);
            }
            
            // Check for move commands in AI response (minimal implementation)
            try {
                detectAndExecuteSimpleMoves(result.reply);
            } catch (error) {
                derror('[MOVE DEBUG] Error in move detection:', error);
                // Fail silently - don't break the conversation
            }
            
            // Then display AI message
            displayAIMessage(result.reply);
            interactiveGapsHistory.push({ role: 'assistant', content: result.reply });
        }
    })
    .catch(err => {
        if (err && err.status === 429) {
            displayAIMessage('The AI service is currently unavailable due to quota limits. Please try again later or set a valid API key in settings.');
            showNotification('AI quota exceeded (429). Try again later.', true);
        }
        derror('Error:', err);
        displayAIMessage(err && err.message ? `Error: ${err.message}` : 'Error communicating with AI.');
    });
    
    // Scroll to bottom
    chat.scrollTop = chat.scrollHeight;
}

/**
 * Display AI message in chat
 */
function displayAIMessage(message) {
    const chat = document.getElementById('interactive-gaps-chat');
    const aiDiv = document.createElement('div');
    aiDiv.style.cssText = 'margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px;';
    aiDiv.innerHTML = `<strong>AI:</strong> ${message}`;
    chat.appendChild(aiDiv);
    chat.scrollTop = chat.scrollHeight;
}

/**
 * Simple move detection - looks for "move X to Y" patterns in AI responses
 */
function detectAndExecuteSimpleMoves(aiResponse) {
    dlog('[MOVE DEBUG] Checking AI response for move and delete commands:', aiResponse);
    dlog('[MOVE DEBUG] About to call detectAndExecuteDeletes...');
    
    // First check for delete patterns
    detectAndExecuteDeletes(aiResponse);
    
    dlog('[MOVE DEBUG] Finished calling detectAndExecuteDeletes, now checking move patterns...');
    
    // Pattern 1: "move [item] to [quadrant]"
    const movePattern1 = /move\s+["']([^"']+)["']\s+to\s+(goal|status|analysis|plan)/gi;
    
    // Pattern 2: "I've moved [item] to the [quadrant] quadrant" (common AI phrasing)
    const movePattern2 = /I've\s+moved\s+["']([^"']+)["']\s+to\s+the\s+(goal|status|analysis|plan)\s+quadrant/gi;
    
    // Pattern 3: "I've moved [item] to [quadrant]" (shorter AI phrasing)
    const movePattern3 = /I've\s+moved\s+["']([^"']+)["']\s+to\s+(goal|status|analysis|plan)/gi;
    
    // Pattern 4: "moved [item] to [quadrant]" (even shorter)
    const movePattern4 = /moved\s+["']([^"']+)["']\s+to\s+(goal|status|analysis|plan)/gi;
    
    // Pattern 5: "I've suggested moving [item] to [quadrant]" (AI asking for permission)
    const movePattern5 = /I've\s+suggested\s+moving\s+["']([^"']+)["']\s+to\s+the\s+(goal|status|analysis|plan)\s+quadrant/gi;
    
    const matches1 = [...aiResponse.matchAll(movePattern1)];
    const matches2 = [...aiResponse.matchAll(movePattern2)];
    const matches3 = [...aiResponse.matchAll(movePattern3)];
    const matches4 = [...aiResponse.matchAll(movePattern4)];
    const matches5 = [...aiResponse.matchAll(movePattern5)];
    const matches = [...matches1, ...matches2, ...matches3, ...matches4, ...matches5];
    
    dlog('[MOVE DEBUG] Found move patterns:', matches.length);
    
    matches.forEach((match, index) => {
        const [fullMatch, itemText, targetQuadrant] = match;
        dlog(`[MOVE DEBUG] Match ${index + 1}:`, { fullMatch, itemText, targetQuadrant });
        
        // Find the thought ID for this item text
        const thoughtId = findThoughtIdByText(itemText.trim());
        
        if (thoughtId) {
            dlog(`[MOVE DEBUG] Found thought ID ${thoughtId} for "${itemText}"`);
            dlog(`[MOVE DEBUG] Attempting to move to ${targetQuadrant}`);
            
            // Ensure target quadrant is lowercase (server expects lowercase)
            const normalizedQuadrant = targetQuadrant.toLowerCase();
            dlog(`[MOVE DEBUG] Normalized quadrant: ${normalizedQuadrant}`);
            
            // Use custom move function that doesn't reload the page
            dlog(`[MOVE DEBUG] Calling moveThoughtWithoutReload(${thoughtId}, ${normalizedQuadrant})`);
            moveThoughtWithoutReload(thoughtId, normalizedQuadrant);
        } else {
            dlog(`[MOVE DEBUG] Could not find thought ID for "${itemText}"`);
        }
    });
}

/**
 * Helper function to find thought ID by matching text content
 */
function findThoughtIdByText(searchText) {
    dlog('[MOVE DEBUG] Searching for thought with text:', searchText);
    
    // Search through all quadrants for matching thought text
    const quadrants = ['goal', 'status', 'analysis', 'plan'];
    
    for (const quadrant of quadrants) {
        const listId = `${quadrant}-list`;
        const list = document.getElementById(listId);
        
        if (list) {
            const thoughtItems = list.querySelectorAll('.thought-item');
            dlog(`[MOVE DEBUG] Checking ${thoughtItems.length} items in ${quadrant} quadrant`);
            
            for (const item of thoughtItems) {
                const thoughtContent = item.querySelector('.thought-content');
                if (thoughtContent) {
                    const itemText = thoughtContent.textContent.trim();
                    dlog(`[MOVE DEBUG] Comparing "${itemText}" with "${searchText}"`);
                    
                    // Simple text matching (case-insensitive)
                    if (itemText.toLowerCase() === searchText.toLowerCase()) {
                        const thoughtId = item.getAttribute('data-thought-id');
                        dlog(`[MOVE DEBUG] Found matching thought with ID: ${thoughtId}`);
                        return thoughtId;
                    }
                }
            }
        }
    }
    
    dlog('[MOVE DEBUG] No matching thought found');
    return null;
}

/**
 * Move thought without page reload (for Interactive Mode)
 */
async function moveThoughtWithoutReload(thoughtId, newQuadrant) {
    try {
        dlog(`[MOVE DEBUG] Starting move: thought ${thoughtId} to ${newQuadrant}`);
        
        const resp = await fetch('/move_thought', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ 
                thought_id: thoughtId, 
                quadrant: newQuadrant,
                board_id: getCurrentBoardId()
            })
        });

        const result = await resp.json();
        dlog(`[MOVE DEBUG] Server response:`, result);

        if (result.success) {
            dlog(`[MOVE DEBUG] Move successful, updating UI without reload`);
            
            // Show success notification
            showNotification(`Thought moved to ${newQuadrant}!`);
            
            // Update the UI by moving the DOM element
            updateThoughtLocationInDOM(thoughtId, newQuadrant);
            
        } else {
            derror(`[MOVE DEBUG] Move failed:`, result.error);
            showNotification('Failed to move thought: ' + (result.error || 'Unknown error'), true);
        }
    } catch (error) {
        derror('[MOVE DEBUG] Error in moveThoughtWithoutReload:', error);
        showNotification('Error moving thought. Please try again.', true);
    }
}

/**
 * Update thought location in DOM without page reload
 */
function updateThoughtLocationInDOM(thoughtId, newQuadrant) {
    dlog(`[MOVE DEBUG] Updating DOM: moving thought ${thoughtId} to ${newQuadrant}`);
    
    // Find the thought element
    const thoughtElement = document.querySelector(`[data-thought-id="${thoughtId}"]`);
    if (!thoughtElement) {
        derror(`[MOVE DEBUG] Could not find thought element with ID ${thoughtId}`);
        return;
    }
    
    // Find the target quadrant list
    const targetList = document.getElementById(`${newQuadrant}-list`);
    if (!targetList) {
        derror(`[MOVE DEBUG] Could not find target list for quadrant ${newQuadrant}`);
        return;
    }
    
    // Move the element to the new quadrant
    targetList.appendChild(thoughtElement);
    dlog(`[MOVE DEBUG] Successfully moved thought element to ${newQuadrant} quadrant`);
}


/**
 * Helper function to find thought ID by matching text content
 */
// (duplicate implementation removed)

/**
 * Move thought without page reload (for Interactive Mode)
 */
// (duplicate implementation removed)

/**
 * Update thought location in DOM without page reload
 */
// (duplicate implementation removed)

/**
 * Add AI suggestions to quadrants automatically
 */
function addSuggestionsToQuadrants(suggestions) {
    dlog('[DEBUG] Adding suggestions to quadrants:', suggestions);
    
    if (!suggestions || typeof suggestions !== 'object') {
        dlog('[DEBUG] No valid suggestions to add');
        return;
    }
    
    const chat = document.getElementById('interactive-gaps-chat');
    let addedItems = [];
    
    // Handle the add_to_quadrant array format
    if (suggestions.add_to_quadrant && Array.isArray(suggestions.add_to_quadrant)) {
        dlog('[DEBUG] Processing add_to_quadrant array:', suggestions.add_to_quadrant);
        
        suggestions.add_to_quadrant.forEach(item => {
            if (item && typeof item === 'object' && item.quadrant && item.thought) {
                dlog(`[DEBUG] Adding "${item.thought}" to ${item.quadrant} quadrant`);
                updateQuadrantInBackground(item.quadrant, item.thought.trim());
                addedItems.push({ quadrant: item.quadrant, thought: item.thought.trim() });
            } else {
                dlog('[DEBUG] Invalid item structure:', item);
            }
        });
    } else {
        // Fallback: Handle separate quadrant properties (original format)
        ['goal', 'status', 'analysis', 'plan'].forEach(quadrant => {
            if (suggestions[quadrant] && Array.isArray(suggestions[quadrant])) {
                suggestions[quadrant].forEach(thought => {
                    if (thought && thought.trim()) {
                        dlog(`[DEBUG] Adding "${thought}" to ${quadrant} quadrant`);
                        updateQuadrantInBackground(quadrant, thought.trim());
                        addedItems.push({ quadrant: quadrant, thought: thought.trim() });
                    }
                });
            }
        });
    }
    
    // Display added items in chat (one per line)
    if (addedItems.length > 0 && chat) {
        const itemsDiv = document.createElement('div');
        itemsDiv.style.cssText = 'margin: 10px 0; padding: 10px; background: #e8f5e8; border-radius: 5px; border-left: 4px solid #4caf50;';
        
        let itemsHtml = '<strong>Added to diagram:</strong><br>';
        addedItems.forEach(item => {
            const quadrantName = item.quadrant.charAt(0).toUpperCase() + item.quadrant.slice(1);
            itemsHtml += `• <strong>${quadrantName}:</strong> ${item.thought}<br>`;
        });
        
        itemsDiv.innerHTML = itemsHtml;
        chat.appendChild(itemsDiv);
        chat.scrollTop = chat.scrollHeight;
    }
    
    dlog('[DEBUG] Finished adding suggestions to quadrants');
}

/**
 * Reset conversation
 */
function resetConversation() {
    dlog('[DEBUG] Resetting conversation');
    
    // Clear history
    interactiveGapsHistory = [];
    
    // Clear chat display
    const chat = document.getElementById('interactive-gaps-chat');
    if (chat) {
        chat.innerHTML = "<div style='color: #666; text-align: center; padding: 2rem;'>Conversation reset. Click to start a new conversation...</div>";
    }
    
    // Clear any stored conversation data
    const boardId = window.boardId || 'default';
    localStorage.removeItem(`interactive-gaps-conversation-${boardId}`);
    
    dlog('[DEBUG] Conversation reset completed');
}

/**
 * Initialize Interactive Mode functionality
 */
function initializeInteractiveMode() {
    dlog('[DEBUG] Initializing Interactive Mode');
    
    // Find panel elements
    const interactiveModePanel = document.getElementById('interactive-mode-panel');
    const interactiveGapsLink = document.getElementById('interactive-gaps-link');
    const closeInteractivePanel = document.getElementById('close-interactive-panel');
    const sendMessageBtn = document.getElementById('send-interactive-message');
    const interactiveGapsInput = document.getElementById('interactive-gaps-input');
    const resetConversationBtn = document.getElementById('reset-conversation');
    const resetConversationMainBtn = document.getElementById('reset-conversation-main');
    const minimizeBtn = document.getElementById('interactive-gaps-minimize');
    const minimizedIcon = document.getElementById('interactive-gaps-minimized-icon');
    
    dlog('[DEBUG] Elements found:', {
        panel: !!interactiveModePanel,
        link: !!interactiveGapsLink,
        close: !!closeInteractivePanel,
        send: !!sendMessageBtn,
        input: !!interactiveGapsInput,
        reset: !!resetConversationBtn,
        resetMain: !!resetConversationMainBtn,
        minimize: !!minimizeBtn,
        minimizedIcon: !!minimizedIcon
    });
    
    // Setup Interactive Mode link click handler
    if (interactiveGapsLink) {
        interactiveGapsLink.addEventListener('click', function(e) {
            e.preventDefault();
            dlog('[DEBUG] Interactive mode link clicked');
            
            if (!interactiveModePanel) {
                derror('[ERROR] Interactive Mode panel not found!');
                return;
            }
            
            // Check current panel state
            const isPanelVisible = interactiveModePanel.style.display === 'flex' || 
                                 window.getComputedStyle(interactiveModePanel).display === 'flex';
            
            dlog('[DEBUG] Panel visible:', isPanelVisible);
            
            if (isPanelVisible) {
                // Panel is open - close it (minimize)
                dlog('[DEBUG] Minimizing panel');
                interactiveModePanel.style.display = 'none';
            } else {
                // Panel is closed - open it (restore)
                dlog('[DEBUG] Restoring panel');
                interactiveModePanel.style.display = 'flex';
                
                // Only initialize conversation if no existing conversation
                if (interactiveGapsHistory.length === 0) {
                    dlog('[DEBUG] No existing conversation - initializing fresh');
                    
                    // Clear chat display first
                    const chat = document.getElementById('interactive-gaps-chat');
                    if (chat) {
                        chat.innerHTML = "<div style='color: #666; text-align: center; padding: 2rem;'>Starting conversation...</div>";
                    }
                    
                    // Reset server-side conversation first, then initialize fresh
                    fetch('/reset_conversation', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({
                            board_id: window.boardId
                        })
                    })
                    .then(response => response.json())
                    .then(result => {
                        dlog('[DEBUG] Server-side conversation reset completed');
                        // Now initialize fresh conversation
                        const quadrants = getCurrentQuadrantThoughts();
                        initializeConversation(quadrants);
                    })
                    .catch(err => {
                        derror('[DEBUG] Error resetting server conversation:', err);
                        // Still try to initialize even if reset failed
                        const quadrants = getCurrentQuadrantThoughts();
                        initializeConversation(quadrants);
                    });
                } else {
                    dlog('[DEBUG] Existing conversation found - restoring previous state');
                }
            }
        });
    }
    
    // Setup close button
    if (closeInteractivePanel) {
        closeInteractivePanel.addEventListener('click', function(e) {
            e.preventDefault();
            dlog('[DEBUG] Close button clicked');
            if (interactiveModePanel) {
                interactiveModePanel.style.display = 'none';
            }
        });
    }
    
    // Setup send message functionality
    if (sendMessageBtn && interactiveGapsInput) {
        sendMessageBtn.addEventListener('click', sendInteractiveMessage);
        
        interactiveGapsInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendInteractiveMessage();
            }
        });
    }
    
    // Setup reset conversation functionality for both buttons
    if (resetConversationBtn) {
        resetConversationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            dlog('[DEBUG] Reset conversation button (modal) clicked');
            resetConversation();
        });
    }
    
    if (resetConversationMainBtn) {
        resetConversationMainBtn.addEventListener('click', function(e) {
            e.preventDefault();
            dlog('[DEBUG] Reset conversation button (main menu) clicked');
            resetConversation();
        });
    }
    
    // Setup minimize button functionality
    if (minimizeBtn) {
        minimizeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            dlog('[DEBUG] Minimize button clicked');
            if (interactiveModePanel) {
                interactiveModePanel.style.display = 'none';
                if (minimizedIcon) {
                    minimizedIcon.style.display = 'flex';
                    dlog('[DEBUG] Showing minimized icon');
                } else {
                    derror('[DEBUG] Minimized icon not found');
                }
            }
        });
    }
    
    // Setup minimized icon (restore) functionality
    if (minimizedIcon) {
        minimizedIcon.addEventListener('click', function(e) {
            e.preventDefault();
            dlog('[DEBUG] Minimized icon clicked - restoring panel');
            if (interactiveModePanel) {
                interactiveModePanel.style.display = 'flex';
                minimizedIcon.style.display = 'none';
                dlog('[DEBUG] Hiding minimized icon');
            }
        });
    } else {
        derror('[DEBUG] Minimized icon element not found during initialization');
    }
}

/**
 * Delete detection - looks for "remove X", "delete X" patterns in AI responses
 */
function findMostRecentlyAddedItem() {
    // Look through the conversation history to find the most recently added item
    const chatMessages = document.querySelectorAll('#im-conversation .message');
    
    // Look for the most recent "Added to diagram:" message
    for (let i = chatMessages.length - 1; i >= 0; i--) {
        const message = chatMessages[i];
        const messageText = message.textContent || message.innerText;
        
        if (messageText.includes('Added to diagram:')) {
            // Extract the item text from "Added to diagram: • Status: Our backlog of problems is growing"
            const match = messageText.match(/Added to diagram:\s*•\s*\w+:\s*(.+)/);
            if (match) {
                const itemText = match[1].trim();
                console.log(`[DELETE DEBUG] Found most recent item from conversation: "${itemText}"`);
                return itemText;
            }
        }
    }
    
    console.log('[DELETE DEBUG] Could not find most recent item in conversation');
    return null;
}

function detectAndExecuteDeletes(aiResponse) {
    dlog('[DELETE DEBUG] Checking AI response for delete commands:', aiResponse);
    dlog('[DELETE DEBUG] Response contains curly quotes:', aiResponse.includes('\u2018') || aiResponse.includes('\u2019'));
    
    // Pattern 1: "remove [item]" or "Remove [item]" (handles all quote types)
    const deletePattern1 = /(?:remove|delete)\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 2: "Let's remove [item]" or "Let's delete [item]"
    const deletePattern2 = /Let's\s+(?:remove|delete)\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 3: "I won't add [item]" or "I understand. I won't add [item]"
    const deletePattern3 = /I\s+(?:won't|will\s+not)\s+add\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 4: "I'll remove [item]" or "I'll delete [item]" (with optional text after)
    const deletePattern4 = /I'll\s+(?:remove|delete)\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D](?:\s+from\s+the\s+\w+\s+quadrant)?/gi;
    
    // Pattern 4b: "I'll remove the item [item]" (more flexible, with optional text after)
    const deletePattern4b = /I'll\s+(?:remove|delete)\s+(?:the\s+item\s+)?["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D](?:\s+from\s+the\s+\w+\s+quadrant)?/gi;
    
    // Pattern 5: "Take out [item]" or "Get rid of [item]"
    const deletePattern5 = /(?:take\s+out|get\s+rid\s+of)\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 6: "I've removed [item]" (past tense confirmation)
    const deletePattern6 = /I've\s+removed\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 7: "I've noted your request to remove [item]" (acknowledgment phrasing)
    const deletePattern7 = /I've\s+noted\s+your\s+request\s+to\s+remove\s+(?:the\s+item\s+)?["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 8: "I'll make a note not to include [item]" (flexible without quotes)
    const deletePattern8 = /I'll\s+make\s+a\s+note\s+not\s+to\s+include\s+["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 9: Fallback - any delete-related keywords with quoted item name
    const deletePattern9 = /(?:remove|delete|noted.*remove|noted.*delete|won't.*include|will.*not.*include)[^"]*["\u2018\u2019\u201C\u201D]([^"\u2018\u2019\u201C\u201D]+)["\u2018\u2019\u201C\u201D]/gi;
    
    // Pattern 10: "remove the last item" or similar references (without quotes)
    const deletePattern10 = /(?:remove|delete)\s+(?:the\s+)?(?:last\s+item|that\s+item|that\s+last\s+item)(?:\s+about\s+(.+?))?/gi;
    
    // Pattern 11: "remove the thought about X" or "Let's remove the thought" (vague references)
    const deletePattern11 = /(?:let's\s+)?(?:remove|delete)\s+(?:the\s+)?thought(?:\s+about\s+(?:the\s+)?(.+?))?(?:\s+from\s+the\s+\w+\s+quadrant)?/gi;
    
    // Pattern 12: Simple straight single quotes - "I'll remove 'item'" 
    const deletePattern12 = /I'll\s+(?:remove|delete)\s+'([^']+)'(?:\s+from\s+the\s+\w+\s+quadrant)?/gi;
    
    // Pattern 13: Bulk delete commands - "delete everything", "remove all entries"
    const deletePattern13 = /(?:I'll\s+)?(?:remove|delete|clear)\s+(?:all|everything|all\s+entries)(?:\s+(?:from|in)\s+(?:the\s+)?quadrants?)?/gi;
    
    const matches1 = [...aiResponse.matchAll(deletePattern1)];
    const matches2 = [...aiResponse.matchAll(deletePattern2)];
    const matches3 = [...aiResponse.matchAll(deletePattern3)];
    const matches4 = [...aiResponse.matchAll(deletePattern4)];
    const matches4b = [...aiResponse.matchAll(deletePattern4b)];
    const matches5 = [...aiResponse.matchAll(deletePattern5)];
    const matches6 = [...aiResponse.matchAll(deletePattern6)];
    const matches7 = [...aiResponse.matchAll(deletePattern7)];
    const matches8 = [...aiResponse.matchAll(deletePattern8)];
    const matches9 = [...aiResponse.matchAll(deletePattern9)];
    const matches10 = [...aiResponse.matchAll(deletePattern10)];
    const matches11 = [...aiResponse.matchAll(deletePattern11)];
    const matches12 = [...aiResponse.matchAll(deletePattern12)];
    const matches13 = [...aiResponse.matchAll(deletePattern13)];
    const matches = [...matches1, ...matches2, ...matches3, ...matches4, ...matches4b, ...matches5, ...matches6, ...matches7, ...matches8, ...matches9, ...matches10, ...matches11, ...matches12, ...matches13];
    
    console.log('[DELETE DEBUG] Found delete patterns:', matches.length);
    
    // Track already processed items to prevent duplicates
    const processedItems = new Set();
    
    matches.forEach((match, index) => {
        const [fullMatch, itemText] = match;
        console.log(`[DELETE DEBUG] Match ${index + 1}:`, { fullMatch, itemText });
        
        let targetItemText = itemText;
        
        // Special handling for "last item" pattern (Pattern 10) and vague references (Pattern 11)
        if (fullMatch.includes('last item') || fullMatch.includes('that item') || 
            fullMatch.includes('the thought') || fullMatch.includes('thought about')) {
            console.log('[DELETE DEBUG] Detected vague reference, finding most recent item');
            // Find the most recently added item in the conversation
            targetItemText = findMostRecentlyAddedItem();
            console.log(`[DELETE DEBUG] Most recent item: "${targetItemText}"`);
        }
        
        // Special handling for bulk delete (Pattern 13)
        if (!itemText && (fullMatch.includes('remove all') || fullMatch.includes('delete everything') || 
            fullMatch.includes('clear all') || fullMatch.includes('all entries'))) {
            console.log('[DELETE DEBUG] Detected bulk delete command, deleting all items');
            executeBulkDelete();
            return; // Skip individual item processing for bulk delete
        }
        
        // Skip if we've already processed this item
        if (processedItems.has(targetItemText)) {
            console.log(`[DELETE DEBUG] Skipping duplicate delete for "${targetItemText}"`);
            return;
        }
        
        // Find the thought with matching text
        const thoughtId = findThoughtIdByText(targetItemText);
        console.log(`[DELETE DEBUG] Found thought ID ${thoughtId} for "${targetItemText}"`);
        
        if (thoughtId) {
            console.log('[DELETE DEBUG] Attempting to delete');
            console.log(`[DELETE DEBUG] Calling deleteThoughtWithoutReload(${thoughtId})`);
            processedItems.add(targetItemText); // Mark as processed
            deleteThoughtWithoutReload(thoughtId);
        } else {
            console.log(`[DELETE DEBUG] Could not find thought ID for "${targetItemText}"`);
        }
    });
}

/**
 * Delete thought without page reload (for Interactive Mode)
 */
async function deleteThoughtWithoutReload(thoughtId) {
    try {
        console.log(`[DELETE DEBUG] Starting delete: thought ${thoughtId}`);
        
        const resp = await fetch('/delete_thought', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ 
                thought_id: thoughtId,
                board_id: getCurrentBoardId()
            })
        });

        const result = await resp.json();
        console.log(`[DELETE DEBUG] Server response:`, result);

        if (result.success) {
            console.log(`[DELETE DEBUG] Delete successful, updating UI without reload`);
            
            // Show success notification
            showNotification(`Thought deleted!`);
            
            // Update the UI by removing the DOM element
            removeThoughtFromDOM(thoughtId);
            
        } else {
            console.error(`[DELETE DEBUG] Delete failed:`, result.error);
            showNotification('Failed to delete thought: ' + (result.error || 'Unknown error'), true);
        }
    } catch (error) {
        console.error('[DELETE DEBUG] Error in deleteThoughtWithoutReload:', error);
        showNotification('Error deleting thought. Please try again.', true);
    }
}

/**
 * Remove thought from DOM without page reload
 */
function removeThoughtFromDOM(thoughtId) {
    console.log(`[DELETE DEBUG] Removing thought ${thoughtId} from DOM`);
    
    // Find the thought element
    const thoughtElement = document.querySelector(`[data-thought-id="${thoughtId}"]`);
    if (!thoughtElement) {
        console.error(`[DELETE DEBUG] Could not find thought element with ID ${thoughtId}`);
        return;
    }
    
    // Remove the element from the DOM
    thoughtElement.remove();
    console.log(`[DELETE DEBUG] Successfully removed thought element from DOM`);
}

/**
 * Execute bulk delete - remove all items from all quadrants
 */
async function executeBulkDelete() {
    console.log('[DELETE DEBUG] Starting bulk delete of all quadrant items');
    
    // Find all thought elements in all quadrants
    const allThoughts = document.querySelectorAll('[data-thought-id]');
    console.log(`[DELETE DEBUG] Found ${allThoughts.length} thoughts to delete`);
    
    if (allThoughts.length === 0) {
        console.log('[DELETE DEBUG] No thoughts found to delete');
        showNotification('No items to delete - quadrants are already empty');
        return;
    }
    
    let deletedCount = 0;
    let failedCount = 0;
    
    // Delete each thought
    for (const thoughtElement of allThoughts) {
        const thoughtId = thoughtElement.getAttribute('data-thought-id');
        console.log(`[DELETE DEBUG] Bulk deleting thought ID: ${thoughtId}`);
        
        try {
            const resp = await fetch('/delete_thought', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ 
                    thought_id: thoughtId,
                    board_id: getCurrentBoardId()
                })
            });

            const result = await resp.json();
            
            if (result.success) {
                // Remove from DOM immediately
                thoughtElement.remove();
                deletedCount++;
                console.log(`[DELETE DEBUG] Successfully deleted thought ${thoughtId}`);
            } else {
                failedCount++;
                console.error(`[DELETE DEBUG] Failed to delete thought ${thoughtId}:`, result.error);
            }
        } catch (error) {
            failedCount++;
            console.error(`[DELETE DEBUG] Error deleting thought ${thoughtId}:`, error);
        }
    }
    
    // Show completion notification
    if (deletedCount > 0) {
        showNotification(`Bulk delete complete: ${deletedCount} items deleted${failedCount > 0 ? `, ${failedCount} failed` : ''}`);
        console.log(`[DELETE DEBUG] Bulk delete complete: ${deletedCount} deleted, ${failedCount} failed`);
    } else {
        showNotification('Bulk delete failed - no items were deleted', true);
        console.error(`[DELETE DEBUG] Bulk delete failed: ${failedCount} failures`);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOM loaded, initializing Interactive Mode');
    initializeInteractiveMode();
});
