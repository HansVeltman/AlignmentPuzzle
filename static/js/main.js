/* ============================================
   The Alignment Puzzle - Main JavaScript
   ============================================ */

// Texts in the language of the page (set by templates/base.html from backend/i18n.py)
var T = window.I18N || {};

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
                this.textContent = T.less;
            } else {
                bio.classList.remove('expanded');
                bio.classList.add('collapsed');
                this.textContent = T.more;
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

            btn.textContent = T.sending;
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
                        msgEl.innerHTML = '<div class="alert alert-success">' + T.contact_ok + '</div>';
                        contactForm.reset();
                    } else {
                        msgEl.innerHTML = '<div class="alert alert-error">' + T.contact_error + '</div>';
                    }
                })
                .catch(function () {
                    msgEl.innerHTML = '<div class="alert alert-error">' + T.contact_failed + '</div>';
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

            btn.textContent = T.processing;
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
                        msgEl.innerHTML = '<div class="alert alert-error">' + (typeof result.detail === 'string' ? result.detail : T.order_error) + '</div>';
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }
                })
                .catch(function () {
                    msgEl.innerHTML = '<div class="alert alert-error">' + T.order_failed + '</div>';
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        });
    }
});

// --- Movies page: play the chosen video in the big player ---
function playMovie(el) {
    var videoId = el.dataset.video;
    var title = el.dataset.title;
    var wrapper = document.getElementById('movieWrapper');
    var placeholder = document.getElementById('moviePlaceholder');
    if (placeholder) placeholder.remove();
    var existing = document.getElementById('moviePlayer');
    if (!existing) {
        var iframe = document.createElement('iframe');
        iframe.id = 'moviePlayer';
        iframe.allowFullscreen = true;
        iframe.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;border:none;';
        wrapper.appendChild(iframe);
    }
    document.getElementById('moviePlayer').src = 'https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1';
    document.getElementById('movieTitle').textContent = title;
    document.querySelectorAll('.movie-thumb').forEach(function(t) { t.classList.remove('active'); });
    el.classList.add('active');
    document.querySelector('.movie-player').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
