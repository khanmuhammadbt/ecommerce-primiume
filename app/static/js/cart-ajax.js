// Cart AJAX functionality
// This file handles adding products to cart via AJAX instead of form submission

/**
 * Add product to cart using AJAX
 * @param {Event} event - The form submission event
 * @param {string} productId - The product ID to add to cart
 * @returns {boolean} - Returns false to prevent default form submission
 */
function addToCartAjax(event, productId) {
    event.preventDefault();

    const form = event.target;
    const csrfInput = form.querySelector('input[name="csrf_token"]');
    const metaCsrf = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = (csrfInput && csrfInput.value) || (metaCsrf && metaCsrf.getAttribute('content')) || '';

    const button = form.querySelector('button[type="submit"]');
    const originalText = button ? button.textContent : 'Add to cart';

    if (button) {
        button.textContent = 'Adding...';
        button.disabled = true;
    }

    fetch('/add_to_cart', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            product_id: productId
        })
    })
    .then(response => {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return response.json().then(data => ({ ok: response.ok, data }));
        }

        return response.text().then(text => ({
            ok: response.ok,
            data: {
                success: false,
                message: text && text.includes('CSRF') ? 'Security token validation failed. Please refresh and try again.' : 'An error occurred while adding to cart'
            }
        }));
    })
    .then(result => {
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }

        const data = result && result.data ? result.data : {};

        if (result && result.ok && data.success) {
            showNotification(data.message, 'success');
            if (data.cart_count !== undefined) {
                updateCartCount(data.cart_count);
            }
        } else {
            showNotification(data.message || 'Error adding to cart', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
        showNotification('An error occurred while adding to cart', 'error');
    });

    return false;
}

/**
 * Show notification/toast message to user
 * @param {string} message - The message to display
 * @param {string} type - The type of notification ('success' or 'error')
 */
function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 9999;
        animation: slideIn 0.3s ease-in-out;
        font-weight: 500;
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in-out';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

/**
 * Update cart count in the header/navbar
 * @param {number} count - The new cart count
 */
function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('[data-cart-count]');
    cartCountElements.forEach(element => {
        element.textContent = count;
        element.style.display = count > 0 ? 'inline' : 'none';
    });
}

// Add animation styles to the document
document.addEventListener('DOMContentLoaded', function() {
    // Check if animations are already added
    if (!document.querySelector('#cart-ajax-animations')) {
        const style = document.createElement('style');
        style.id = 'cart-ajax-animations';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
});
