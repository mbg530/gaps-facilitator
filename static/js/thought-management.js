/* GAPS Facilitator - Thought Management Module */

let aiConversationActive = false;
const aiPromptPlaceholder = "What's on your mind? (AI will help organize your thoughts)";

/**
 * Initialize thought management functionality
 */
function initializeThoughtManagement() {
    const addBtn = document.getElementById('add-thought-btn');
    const newThoughtInput = document.getElementById('new-thought-input');
    const newThoughtQuadrant = document.getElementById('new-thought-quadrant');

    if (!addBtn || !newThoughtInput || !newThoughtQuadrant) {
        dlog('[DEBUG] Thought management elements not found');
        return;
    }

    // Set initial placeholder
    newThoughtInput.placeholder = aiPromptPlaceholder;

    // Add thought button click handler
    addBtn.addEventListener('click', async function () {
        const quadrant = newThoughtQuadrant.value;
        
        if (quadrant === 'auto') {
            await handleConversationalAddThought();
        } else {
            await handleManualAddThought();
        }
    });

    // Enter key handler for input
    newThoughtInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            addBtn.click();
        }
    });
}

/**
 * Handle AI-driven conversational thought addition
 */
async function handleConversationalAddThought() {
    const addBtn = document.getElementById('add-thought-btn');
    const newThoughtInput = document.getElementById('new-thought-input');
    const boardId = window.boardId || null;

    const content = newThoughtInput.value.trim();
    
    if (!content || !boardId) {
        showNotification('Thought and board are required!', true);
        return;
    }

    addBtn.disabled = true;
    addBtn.textContent = 'Thinking...';

    try {
        const result = await postJSON('/ai_conversation', { content, board_id: boardId });

        if (result.success && result.thoughts) {
            // AI classified and added thoughts
            aiConversationActive = false;
            newThoughtInput.value = '';
            newThoughtInput.placeholder = aiPromptPlaceholder;
            
            if (result.thoughts && Array.isArray(result.thoughts)) {
                const onboardingOffer = "welcome! i use the gaps model to help clarify and solve problems. would you like a quick intro to how it works, or are you already familiar with gaps?";
                result.thoughts = result.thoughts.filter(t => typeof t !== 'string' || t.trim().toLowerCase() !== onboardingOffer);
            }
            
            showNotification('Thought(s) added!');
            
            // Wait for notification to finish before reloading page
            if (window.notificationTimeout) clearTimeout(window.notificationTimeout);
            window.notificationTimeout = setTimeout(() => {
                location.reload();
            }, 1800);
            
        } else if (result.success && result.followup && (!result.thoughts || result.thoughts.length === 0)) {
            // Only show followup if NO thoughts were added
            aiConversationActive = true;
            newThoughtInput.value = '';
            newThoughtInput.placeholder = result.followup;
            showNotification('AI: ' + result.followup);
            addBtn.textContent = 'Respond';
            
        } else if (result.error) {
            showNotification('AI error: ' + result.error, true);
            addBtn.textContent = 'Add';
            
        } else if (result.success && result.reply) {
            // Show AI reply in chat area below input
            displayAIReply(result.reply);
            newThoughtInput.value = '';
            newThoughtInput.placeholder = aiPromptPlaceholder;
            addBtn.textContent = 'Add';
            
        } else {
            showNotification('Unexpected AI response.', true);
            addBtn.textContent = 'Add';
        }
    } catch (e) {
        if (e && e.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        } else {
            showNotification('Error: ' + e.message, true);
        }
        addBtn.textContent = 'Add';
    } finally {
        addBtn.disabled = false;
    }
}

/**
 * Handle manual thought addition (specific quadrant)
 */
async function handleManualAddThought() {
    const addBtn = document.getElementById('add-thought-btn');
    const newThoughtInput = document.getElementById('new-thought-input');
    const newThoughtQuadrant = document.getElementById('new-thought-quadrant');
    const boardId = window.boardId || null;

    const content = newThoughtInput.value.trim();
    const quadrant = newThoughtQuadrant.value;
    
    if (!content || !boardId) {
        showNotification('Thought and board are required!', true);
        return;
    }

    addBtn.disabled = true;
    addBtn.textContent = 'Adding...';

    try {
        const addResult = await postJSON('/add_thought', {
            content: content,
            quadrant: quadrant,
            board_id: boardId
        });

        if (addResult.success) {
            showNotification('Thought added!');
            newThoughtInput.value = '';
            setTimeout(() => location.reload(), 1200);
        } else {
            showNotification('Failed to add thought: ' + (addResult.error || 'Unknown error'), true);
        }
    } catch (e) {
        showNotification('Error: ' + e.message, true);
    } finally {
        addBtn.disabled = false;
        addBtn.textContent = 'Add';
    }
}

/**
 * Display AI reply in a chat area
 */
function displayAIReply(reply) {
    const newThoughtInput = document.getElementById('new-thought-input');
    
    let chatDiv = document.getElementById('ai-conversation-chat');
    if (!chatDiv) {
        chatDiv = document.createElement('div');
        chatDiv.id = 'ai-conversation-chat';
        chatDiv.style.marginTop = '1em';
        chatDiv.style.background = '#f8fafc';
        chatDiv.style.borderRadius = '8px';
        chatDiv.style.padding = '1em';
        chatDiv.style.fontSize = '1.05em';
        newThoughtInput.parentNode.parentNode.appendChild(chatDiv);
    }
    
    chatDiv.innerHTML += `<div style='margin-bottom:0.5em;color:#007bff;'><b>AI:</b> ${reply.replace(/\n/g, '<br>')}</div>`;
}

/**
 * Delete a thought by ID
 */
async function deleteThought(thoughtId, element) {
    const confirmed = await showConfirm('Are you sure you want to delete this thought?');
    if (!confirmed) {
        return;
    }

    try {
        const resp = await fetch('/delete_thought', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ thought_id: thoughtId })
        });

        const result = await resp.json();

        if (result.success) {
            // Remove the element from DOM
            element.closest('.thought-item').remove();
            showNotification('Thought deleted!');
        } else {
            showNotification('Failed to delete thought: ' + (result.error || 'Unknown error'), true);
        }
    } catch (error) {
        console.error('[ERROR] Failed to delete thought:', error);
        showNotification('Error deleting thought. Please try again.', true);
    }
}

/**
 * Add a thought to a specific quadrant (used by Quick Add Thought modal)
 */
async function addThought(content, quadrant) {
    console.log(`[DEBUG] addThought called with content: "${content}", quadrant: "${quadrant}"`);
    
    if (!content || !content.trim()) {
        showNotification('Please enter a thought', true);
        return;
    }
    
    const boardId = getCurrentBoardId();
    if (!boardId) {
        showNotification('No board selected', true);
        return;
    }
    
    try {
        const targetQuadrant = quadrant === 'auto' ? 'status' : quadrant;
        
        const resp = await fetch('/add_thought', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                content: content.trim(),
                quadrant: targetQuadrant,
                board_id: boardId
            })
        });

        const result = await resp.json();

        if (result.success) {
            showNotification('Thought added!');
            
            // Add thought to DOM without page reload (preserves Interactive Mode)
            const thoughtId = result.thought_id || result.thought?.id;
            if (thoughtId) {
                dlog(`[DEBUG] Quick Add: Adding thought with ID ${thoughtId} to ${targetQuadrant} quadrant`);
                addThoughtToDOM(targetQuadrant, content.trim(), thoughtId);
            } else {
                dlog('[DEBUG] Quick Add: No thought ID returned, will reload page');
                setTimeout(() => location.reload(), 1000);
            }
        } else {
            // Handle duplicate error specifically
            if (result.error && result.error.includes('Duplicate')) {
                showNotification('This thought already exists in the quadrant', true);
            } else {
                showNotification('Failed to add thought: ' + (result.error || 'Unknown error'), true);
            }
        }
    } catch (error) {
        derror('[ERROR] Failed to add thought:', error);
        if (error && error.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        } else {
            showNotification('Error adding thought. Please try again.', true);
        }
    }
}

/**
 * Get current board ID
 */
function getCurrentBoardId() {
    return window.boardId;
}

/**
 * Drag and drop functionality
 */
function dragThought(event, thoughtId) {
    dlog('dragThought called', thoughtId);
    event.dataTransfer.setData('text/plain', thoughtId);
    event.dataTransfer.effectAllowed = 'move';
}

function clearTrashHighlight() {
    // Remove any drag highlighting
    document.querySelectorAll('.quadrant').forEach(q => {
        q.classList.remove('drag-over');
    });
}

function allowDrop(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

function dragEnter(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function dragLeave(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
}

function dropThought(event, targetQuadrant) {
    event.preventDefault();
    const thoughtId = event.dataTransfer.getData('text/plain');
    dlog('dropThought', thoughtId, 'to', targetQuadrant);
    
    // Clear drag highlighting
    clearTrashHighlight();
    
    // Move the thought
    moveThought(thoughtId, targetQuadrant, null);
}

/**
 * Move thought to different quadrant
 */
async function moveThought(thoughtId, newQuadrant, element) {
    try {
        const result = await postJSON('/move_thought', { 
            thought_id: thoughtId, 
            quadrant: newQuadrant,
            board_id: getCurrentBoardId()
        });

        if (result.success) {
            showNotification(`Thought moved to ${newQuadrant}!`);
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Failed to move thought: ' + (result.error || 'Unknown error'), true);
        }
    } catch (error) {
        derror('[ERROR] Failed to move thought:', error);
        if (error && error.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        } else {
            showNotification('Error moving thought. Please try again.', true);
        }
    }
}

/**
 * Edit thought content
 */
async function editThought(thoughtId, currentContent, element) {
    const newContent = prompt('Edit thought:', currentContent);
    
    if (newContent === null || newContent.trim() === currentContent.trim()) {
        return; // User cancelled or no change
    }

    try {
        const result = await postJSON('/edit_thought', { 
            thought_id: thoughtId, 
            content: newContent.trim() 
        });

        if (result.success) {
            // Update the element content
            const contentElement = element.closest('.thought-item').querySelector('.thought-content');
            if (contentElement) {
                contentElement.textContent = newContent.trim();
            }
            showNotification('Thought updated!');
        } else {
            showNotification('Failed to update thought: ' + (result.error || 'Unknown error'), true);
        }
    } catch (error) {
        derror('[ERROR] Failed to edit thought:', error);
        if (error && error.status === 429) {
            showNotification('AI quota exceeded (429). Try again later.', true);
        } else {
            showNotification('Error editing thought. Please try again.', true);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeThoughtManagement();
});
