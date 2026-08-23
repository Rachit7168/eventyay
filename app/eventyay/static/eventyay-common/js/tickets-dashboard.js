/**
 * Tickets dashboard: check-in KPI card list selector.
 */

const STORAGE_PREFIX = 'eventyay-checkin-kpi:';

function formatPercentage(option) {
    if (!option.position_count) {
        return '0.0';
    }
    const value = Number(option.percentage);
    return Number.isFinite(value) ? value.toFixed(1) : '0.0';
}

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
    const fillEl = widget.querySelector('[data-checkin-kpi-fill]');
    const pctEl = widget.querySelector('[data-checkin-kpi-pct]');
    const barEl = widget.querySelector('[data-checkin-kpi-bar]');
    const linkEl = widget.querySelector('[data-checkin-kpi-link]');
    const storageKey = `${STORAGE_PREFIX}${window.location.pathname}`;

    function applyOption(option) {
        if (!option) {
            return;
        }

        insideEl.textContent = String(option.inside_count);
        totalEl.textContent = String(option.position_count);
        const percentage = formatPercentage(option);
        fillEl.style.width = `${percentage}%`;
        pctEl.textContent = `${percentage}%`;
        linkEl.href = option.url;

        if (option.position_count > 0) {
            barEl.hidden = false;
        } else {
            barEl.hidden = true;
        }
    }

    const savedId = localStorage.getItem(storageKey);
    if (savedId && optionsById[savedId]) {
        select.value = savedId;
    }

    applyOption(optionsById[select.value]);

    select.addEventListener('change', () => {
        const selected = optionsById[select.value];
        applyOption(selected);
        localStorage.setItem(storageKey, select.value);
    });
}

initCheckinKpiWidget();
