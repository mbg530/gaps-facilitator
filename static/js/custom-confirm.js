/**
 * Custom confirmation modal system
 * Replaces browser's native confirm() to avoid permission blocking issues
 */

class CustomConfirm {
    constructor() {
        this.modalId = 'custom-confirm-modal';
        this.createModal();
    }

    createModal() {
        // Remove existing modal if it exists
        const existing = document.getElementById(this.modalId);
        if (existing) {
            existing.remove();
        }

        // Create modal HTML
        const modal = document.createElement('div');
        modal.id = this.modalId;
        modal.innerHTML = `
            <div class="modal-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                z-index: 10000;
                justify-content: center;
                align-items: center;
            ">
                <div class="modal-content" style="
                    background: white;
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                    max-width: 400px;
                    width: 90%;
                    text-align: center;
                ">
                    <div class="modal-message" style="
                        margin-bottom: 1.5rem;
                        font-size: 1.1rem;
                        color: #333;
                    "></div>
                    <div class="modal-checkbox" style="
                        margin-bottom: 1.5rem;
                        text-align: left;
                        display: none;
                    ">
                        <label style="
                            display: flex;
                            align-items: center;
                            font-size: 0.9rem;
                            color: #666;
                            cursor: pointer;
                        ">
                            <input type="checkbox" id="dont-ask-again" style="
                                margin-right: 0.5rem;
                            ">
                            Don't ask again for deletions
                        </label>
                    </div>
                    <div class="modal-buttons">
                        <button id="confirm-cancel" style="
                            background: #6c757d;
                            color: white;
                            border: none;
                            padding: 0.75rem 1.5rem;
                            border-radius: 5px;
                            font-size: 1rem;
                            margin-right: 1rem;
                            cursor: pointer;
                        ">Cancel</button>
                        <button id="confirm-ok" style="
                            background: #dc3545;
                            color: white;
                            border: none;
                            padding: 0.75rem 1.5rem;
                            border-radius: 5px;
                            font-size: 1rem;
                            cursor: pointer;
                        ">Delete</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    show(message, showCheckbox = true) {
        return new Promise((resolve) => {
            // Check if user has opted out of confirmations
            if (localStorage.getItem('gaps-skip-delete-confirm') === 'true') {
                resolve(true);
                return;
            }

            const modal = document.getElementById(this.modalId);
            const overlay = modal.querySelector('.modal-overlay');
            const messageEl = modal.querySelector('.modal-message');
            const checkboxDiv = modal.querySelector('.modal-checkbox');
            const checkbox = modal.querySelector('#dont-ask-again');
            const okBtn = modal.querySelector('#confirm-ok');
            const cancelBtn = modal.querySelector('#confirm-cancel');

            // Set message
            messageEl.textContent = message;

            // Show/hide checkbox
            if (showCheckbox) {
                checkboxDiv.style.display = 'block';
                checkbox.checked = false;
            } else {
                checkboxDiv.style.display = 'none';
            }

            // Show modal
            overlay.style.display = 'flex';

            // Handle button clicks
            const handleOk = () => {
                // Save checkbox preference if checked
                if (showCheckbox && checkbox.checked) {
                    localStorage.setItem('gaps-skip-delete-confirm', 'true');
                    console.log('[CONFIRM] User opted out of future delete confirmations');
                }
                
                overlay.style.display = 'none';
                okBtn.removeEventListener('click', handleOk);
                cancelBtn.removeEventListener('click', handleCancel);
                resolve(true);
            };

            const handleCancel = () => {
                overlay.style.display = 'none';
                okBtn.removeEventListener('click', handleOk);
                cancelBtn.removeEventListener('click', handleCancel);
                resolve(false);
            };

            okBtn.addEventListener('click', handleOk);
            cancelBtn.addEventListener('click', handleCancel);

            // Handle escape key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    handleCancel();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);

            // Handle click outside modal
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    handleCancel();
                }
            });
        });
    }
}

// Create global instance
window.customConfirm = new CustomConfirm();

// Convenience function to replace confirm()
window.showConfirm = function(message, showCheckbox = true) {
    return window.customConfirm.show(message, showCheckbox);
};

// Utility functions for managing delete confirmation preferences
window.resetDeleteConfirmations = function() {
    localStorage.removeItem('gaps-skip-delete-confirm');
    console.log('[CONFIRM] Delete confirmation preference reset - confirmations will now show');
};

window.isDeleteConfirmationSkipped = function() {
    return localStorage.getItem('gaps-skip-delete-confirm') === 'true';
};
