/* ============================================
   The Alignment Puzzle - Main JavaScript
   ============================================ */

// --- Mobile Navigation Toggle ---
document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.querySelector('.menu-toggle');
    const nav = document.getElementById('mainNav');

    if (toggle && nav) {
        toggle.addEventListener('click', function () {
            nav.classList.toggle('open');
        });

        // Close menu when clicking a link
        nav.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                nav.classList.remove('open');
            });
        });
    }

    // --- Author Bio Toggle ---
    document.querySelectorAll('.author-more').forEach(function (link) {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            var bio = this.previousElementSibling;
            if (bio.classList.contains('collapsed')) {
                bio.classList.remove('collapsed');
                bio.classList.add('expanded');
                this.textContent = 'less';
            } else {
                bio.classList.remove('expanded');
                bio.classList.add('collapsed');
                this.textContent = 'more...';
            }
        });
    });

    // --- Contact Form (AJAX) ---
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const msgEl = document.getElementById('formMessage');
            const btn = contactForm.querySelector('button[type="submit"]');
            const originalText = btn.textContent;

            btn.textContent = 'Sending...';
            btn.disabled = true;

            const formData = new FormData(contactForm);
            const data = Object.fromEntries(formData.entries());

            fetch('/api/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
                .then(function (res) { return res.json(); })
                .then(function (result) {
                    if (result.success) {
                        msgEl.innerHTML = '<div class="alert alert-success">Thank you! Your message has been sent successfully.</div>';
                        contactForm.reset();
                    } else {
                        msgEl.innerHTML = '<div class="alert alert-error">Something went wrong. Please try again or email us directly.</div>';
                    }
                })
                .catch(function () {
                    msgEl.innerHTML = '<div class="alert alert-error">Could not send message. Please try again later.</div>';
                })
                .finally(function () {
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        });
    }

    // --- Order Form (redirect to Mollie) ---
    const orderForm = document.getElementById('orderForm');
    if (orderForm) {
        orderForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const msgEl = document.getElementById('orderMessage');
            const btn = orderForm.querySelector('button[type="submit"]');
            const originalText = btn.textContent;

            btn.textContent = 'Processing...';
            btn.disabled = true;

            const formData = new FormData(orderForm);
            const data = Object.fromEntries(formData.entries());

            fetch('/api/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
                .then(function (res) { return res.json(); })
                .then(function (result) {
                    if (result.checkout_url) {
                        // Redirect to Mollie payment page
                        window.location.href = result.checkout_url;
                    } else {
                        msgEl.innerHTML = '<div class="alert alert-error">' + (result.detail || 'Something went wrong. Please try again.') + '</div>';
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }
                })
                .catch(function () {
                    msgEl.innerHTML = '<div class="alert alert-error">Could not process order. Please try again later.</div>';
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        });
    }
});
