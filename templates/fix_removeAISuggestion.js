// Place this script at the very top or bottom of your index.html, outside of any DOMContentLoaded or function blocks.
window.removeAISuggestion = function(idx) {
    const sugLi = document.getElementById(`ai-suggestion-li-${idx}`);
    let deleted = false;
    if (sugLi) {
        // Get the text to match (trim whitespace)
        const textToDelete = sugLi.querySelector('.thought-content').textContent.trim();
        // Try to remove from all quadrants
        const quadrantLists = document.querySelectorAll('.thought-list');
        quadrantLists.forEach(ul => {
            const lis = ul.querySelectorAll('li');
            lis.forEach(li => {
                const span = li.querySelector('.thought-content');
                if (span && span.textContent.trim() === textToDelete) {
                    li.remove();
                    deleted = true;
                }
            });
        });
        // Remove from suggestions list
        const ul = sugLi.parentElement;
        sugLi.remove();
        if (ul && ul.children.length === 0) {
            ul.innerHTML = '<li style="color:#888;font-style:italic;">No more suggestions.</li>';
        }
        if (!deleted) {
            // Optionally show a notification
            if (window.showNotification) {
                showNotification('Only removed from suggestions. No matching thought found in quadrants.');
            } else {
                alert('Only removed from suggestions. No matching thought found in quadrants.');
            }
        }
    }
};
