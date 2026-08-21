/**
 * Report mode toggle for the order overview page.
 */
function initOrderOverviewReport(root = document) {
    const toggleRoot = root.querySelector('[data-order-overview-report]');
    if (!toggleRoot) {
        return;
    }

    const buttons = toggleRoot.querySelectorAll('[data-report-mode]');
    const table = toggleRoot.querySelector('.table-product-overview');
    if (!buttons.length || !table) {
        return;
    }

    const setMode = (target) => {
        toggleRoot.dataset.reportMode = target;
        buttons.forEach((button) => {
            const isActive = button.dataset.reportMode === target;
            button.classList.toggle('active', isActive);
            button.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        const heading = toggleRoot.querySelector('[data-report-table-heading]');
        if (heading) {
            const labels = {
                '.count': heading.dataset.headingSales,
                '.sum-gross': heading.dataset.headingGross,
                '.sum-net': heading.dataset.headingNet,
            };
            heading.textContent = labels[target] || labels['.count'];
        }
    };

    buttons.forEach((button) => {
        button.addEventListener('click', () => {
            setMode(button.dataset.reportMode);
        });
    });

    const activeButton = toggleRoot.querySelector('[data-report-mode].active') || buttons[0];
    if (activeButton) {
        setMode(activeButton.dataset.reportMode);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initOrderOverviewReport();
});

export { initOrderOverviewReport };
