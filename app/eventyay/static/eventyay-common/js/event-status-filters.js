/**
 * Toggle Live / Draft / Past filter buttons without jQuery.
 */
function setStatusButtonState(button, checked) {
    button.classList.toggle('active', checked);
}

function initEventStatusFilters(root) {
    const buttons = root.querySelectorAll('[data-event-status-chip]');
    for (const button of buttons) {
        if (button.dataset.eventStatusChipBound === '1') {
            continue;
        }
        button.dataset.eventStatusChipBound = '1';

        const input = button.querySelector('input[type="checkbox"]');
        if (!input) {
            continue;
        }

        setStatusButtonState(button, input.checked);

        button.addEventListener('click', (event) => {
            if (event.target === input) {
                setStatusButtonState(button, input.checked);
                return;
            }
            event.preventDefault();
            input.checked = !input.checked;
            setStatusButtonState(button, input.checked);
        });

        button.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                input.checked = !input.checked;
                setStatusButtonState(button, input.checked);
            }
        });
    }
}

function initAllEventStatusFilters(root = document) {
    const containers = root.querySelectorAll('[data-event-status-filters]');
    for (const container of containers) {
        initEventStatusFilters(container);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initAllEventStatusFilters());
} else {
    initAllEventStatusFilters();
}
