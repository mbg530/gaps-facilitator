// Interactive GAPS Modal Logic - Always loaded at end of body
// Ensures event handlers attach after DOM is ready

document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] Interactive Mode DOMContentLoaded handler running');
    const interactiveGapsModal = document.getElementById('interactive-gaps-modal');
    const interactiveGapsLink = document.getElementById('interactive-gaps-link');
    const interactiveGapsClose = document.getElementById('interactive-gaps-close');
    const interactiveGapsSend = document.getElementById('interactive-gaps-send');
    const interactiveGapsInput = document.getElementById('interactive-gaps-input');
    const interactiveGapsChat = document.getElementById('interactive-gaps-chat');

    if (interactiveGapsLink) {
        console.log('[DEBUG] interactiveGapsLink found at DOMContentLoaded');
        interactiveGapsLink.addEventListener('click', function(e) {
            console.log('[DEBUG] Interactive mode link clicked');
            e.preventDefault();
            if (!interactiveGapsModal) {
                console.log('[DEBUG] interactiveGapsModal is null!');
            } else {
                interactiveGapsModal.style.display = 'flex';
                console.log('[DEBUG] Modal display set to flex');
            }
            // ... (rest of your modal open logic here, or keep in main file)
        });
    } else {
        console.log('[DEBUG] interactiveGapsLink NOT found at DOMContentLoaded');
    }
});
