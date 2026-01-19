/**
 * Robust Notification System
 * A global class to handle stackable, animated notifications with progress bars.
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create container if it doesn't exist
        if (!document.querySelector('.notification-container')) {
            this.container = document.createElement('div');
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.querySelector('.notification-container');
        }
    }

    /**
     * Show a notification
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {string} title - Main title
     * @param {string} message - Detail message
     * @param {number} duration - ms to stay visible (default 5000)
     */
    show(type, title, message, duration = 5000) {
        // Icons based on type
        const icons = {
            success: 'ph-check-circle',
            error: 'ph-warning-circle',
            warning: 'ph-warning',
            info: 'ph-info'
        };

        const iconClass = icons[type] || 'ph-bell';
        const id = 'toast-' + Date.now() + Math.random().toString(36).substr(2, 9);

        // Create Toast Element
        const toast = document.createElement('div');
        toast.className = `notification-toast ${type}`;
        toast.id = id;

        toast.innerHTML = `
            <div class="notif-icon-box">
                <i class="ph-fill ${iconClass}"></i>
            </div>
            <div class="notif-content">
                <div class="notif-title">${title}</div>
                <div class="notif-message">${message}</div>
            </div>
            <button class="notif-close" onclick="Notifier.dismiss('${id}')">
                <i class="ph-bold ph-x"></i>
            </button>
            <div class="notif-progress">
                <div class="notif-progress-bar"></div>
            </div>
        `;

        // Prepend to show newest at top
        this.container.prepend(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Setup Progress Bar animation
        const progressBar = toast.querySelector('.notif-progress-bar');
        progressBar.style.transition = `transform ${duration}ms linear`;

        // Force reflow
        void progressBar.offsetWidth;

        // Start progress
        requestAnimationFrame(() => {
            progressBar.style.transform = 'scaleX(0)';
        });

        // Auto Dismiss
        setTimeout(() => {
            this.dismiss(id);
        }, duration);
    }

    dismiss(id) {
        const toast = document.getElementById(id);
        if (toast) {
            toast.classList.remove('show');
            toast.classList.add('hide');

            // Remove from DOM after animation
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 400); // Matches CSS transition time
        }
    }

    // Convenience methods
    success(title, message, duration) {
        this.show('success', title, message, duration);
    }

    error(title, message, duration) {
        this.show('error', title, message, duration);
    }

    warning(title, message, duration) {
        this.show('warning', title, message, duration);
    }

    info(title, message, duration) {
        this.show('info', title, message, duration);
    }
}

// Global Instance
window.Notifier = new NotificationSystem();
