document.addEventListener('DOMContentLoaded', function () {
    var timelineSteps = document.querySelectorAll('.dashboard-timeline .timeline-step');
    if (!timelineSteps.length) return;

    var closeTimers = {};

    function closeAllExcept(currentStep) {
        timelineSteps.forEach(function (step) {
            if (step !== currentStep) {
                step.classList.remove('is-open');
                var content = step.querySelector('.timeline-step-content');
                if (content) content.setAttribute('aria-expanded', 'false');
            }
        });
    }

    timelineSteps.forEach(function (step, index) {
        var content = step.querySelector('.timeline-step-content');
        var menu = step.querySelector('.timeline-step-links');
        if (!menu) return;

        // Hover interaction with graceful close delay
        step.addEventListener('mouseenter', function () {
            if (closeTimers[index]) {
                clearTimeout(closeTimers[index]);
                delete closeTimers[index];
            }
        });

        step.addEventListener('mouseleave', function () {
            if (step.classList.contains('is-open')) return;
            closeTimers[index] = setTimeout(function () {
                step.classList.remove('is-open');
                if (content) content.setAttribute('aria-expanded', 'false');
            }, 300);
        });

        // Click interaction: clicking a phase toggles its menu and keeps it open
        if (content) {
            content.addEventListener('click', function (e) {
                if (menu) {
                    e.preventDefault();
                    var isOpen = step.classList.toggle('is-open');
                    content.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
                    if (isOpen) {
                        closeAllExcept(step);
                    }
                }
            });

            // Keyboard navigation
            content.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    step.classList.add('is-open');
                    content.setAttribute('aria-expanded', 'true');
                    closeAllExcept(step);
                    var firstLink = menu.querySelector('a');
                    if (firstLink) firstLink.focus();
                } else if (e.key === 'Escape') {
                    step.classList.remove('is-open');
                    content.setAttribute('aria-expanded', 'false');
                }
            });
        }

        menu.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                step.classList.remove('is-open');
                if (content) {
                    content.setAttribute('aria-expanded', 'false');
                    content.focus();
                }
            }
        });
    });

    // Close open menus when clicking anywhere outside
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.dashboard-timeline')) {
            closeAllExcept(null);
        }
    });
});
