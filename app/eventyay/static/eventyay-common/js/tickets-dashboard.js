/**
 * Tickets dashboard: check-in KPI card list selector.
 */

const STORAGE_PREFIX = 'eventyay-checkin-kpi:';

function initCheckinKpiWidget() {
    const widget = document.querySelector('[data-checkin-kpi-widget]');
    const dataElement = document.getElementById('checkin-kpi-data');
    const select = widget?.querySelector('[data-checkin-kpi-select]');

    if (!widget || !dataElement || !select) {
        return;
    }

    let options;
    try {
        options = JSON.parse(dataElement.textContent);
    } catch {
        return;
    }

    const optionsById = Object.fromEntries(options.map((option) => [String(option.id), option]));
    const insideEl = widget.querySelector('[data-checkin-kpi-inside]');
    const totalEl = widget.querySelector('[data-checkin-kpi-total]');
    const linkEl = widget.querySelector('[data-checkin-kpi-link]');
    const storageKey = `${STORAGE_PREFIX}${window.location.pathname}`;

    function applyOption(option) {
        if (!option) {
            return;
        }

        insideEl.textContent = String(option.inside_count);
        totalEl.textContent = String(option.position_count);
        linkEl.href = option.url;
    }

    const savedId = localStorage.getItem(storageKey);
    if (savedId === 'all') {
        localStorage.removeItem(storageKey);
    } else if (savedId && optionsById[savedId]) {
        select.value = savedId;
    } else if (options.length) {
        select.value = String(options[0].id);
    }

    applyOption(optionsById[select.value] || options[0]);

    select.addEventListener('change', () => {
        const selected = optionsById[select.value];
        applyOption(selected);
        localStorage.setItem(storageKey, select.value);
    });
}

function positionQuotaProductsPanel(details) {
    const trigger = details.querySelector('.quota-products-trigger');
    const panel = details.querySelector('.quota-products-panel');
    if (!trigger || !panel) {
        return;
    }

    panel.classList.add('quota-products-panel--floating');

    const margin = 8;
    const gap = 6;
    const triggerRect = trigger.getBoundingClientRect();
    const panelWidth = panel.offsetWidth;
    const panelHeight = panel.offsetHeight;

    let top = triggerRect.bottom + gap;
    if (top + panelHeight > window.innerHeight - margin) {
        top = Math.max(margin, triggerRect.top - panelHeight - gap);
    }

    let left = triggerRect.left;
    if (left + panelWidth > window.innerWidth - margin) {
        left = window.innerWidth - panelWidth - margin;
    }
    left = Math.max(margin, left);

    panel.style.setProperty('--popover-top', `${top}px`);
    panel.style.setProperty('--popover-left', `${left}px`);
}

function resetQuotaProductsPanel(details) {
    const panel = details.querySelector('.quota-products-panel');
    if (!panel) {
        return;
    }

    panel.classList.remove('quota-products-panel--floating');
    panel.style.removeProperty('--popover-top');
    panel.style.removeProperty('--popover-left');
}

function initQuotaProductPopovers() {
    const popovers = document.querySelectorAll('[data-quota-products]');
    if (!popovers.length) {
        return;
    }

    popovers.forEach((details) => {
        let closeOnOutsideClick = null;
        let reposition = null;

        const cleanupListeners = () => {
            if (closeOnOutsideClick) {
                document.removeEventListener('click', closeOnOutsideClick);
                closeOnOutsideClick = null;
            }
            if (reposition) {
                window.removeEventListener('resize', reposition);
                window.removeEventListener('scroll', reposition, true);
                reposition = null;
            }
        };

        details.addEventListener('toggle', () => {
            cleanupListeners();

            if (!details.open) {
                resetQuotaProductsPanel(details);
                return;
            }

            popovers.forEach((other) => {
                if (other !== details) {
                    other.open = false;
                    resetQuotaProductsPanel(other);
                }
            });

            positionQuotaProductsPanel(details);

            reposition = () => {
                if (details.open) {
                    positionQuotaProductsPanel(details);
                }
            };
            window.addEventListener('resize', reposition);
            window.addEventListener('scroll', reposition, true);

            closeOnOutsideClick = (event) => {
                if (!details.contains(event.target)) {
                    details.open = false;
                }
            };

            window.setTimeout(() => {
                document.addEventListener('click', closeOnOutsideClick);
            }, 0);
        });
    });
}

initCheckinKpiWidget();
initQuotaProductPopovers();
