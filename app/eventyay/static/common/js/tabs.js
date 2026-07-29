const TAB_SELECTOR = "input[role=tab][name=tablist]"

const updateTabPanels = () => {
    const selectedTab = document.querySelector(`${TAB_SELECTOR}:checked`)
    if (!selectedTab) return
    const selectedPanel = document.getElementById(selectedTab.getAttribute("aria-controls"))
    if (!selectedPanel) return
    selectedTab.parentElement.querySelectorAll(`[role=tab][aria-selected=true]`).forEach((element) => {
        element.setAttribute("aria-selected", "false")
    })
    selectedPanel.parentElement.querySelectorAll(":scope > [role=tabpanel]").forEach((element) => {
        element.setAttribute("aria-hidden", "true")
    })
    selectedTab.setAttribute("aria-selected", "true")
    selectedPanel.setAttribute("aria-hidden", "false")
    window.location.hash = selectedTab.id
}

const getTabFromHash = () => {
    const fragment = window.location.hash.substr(1)
    if (fragment) {
        return document.querySelector(`${TAB_SELECTOR}#${fragment}`)
    }
}

const initTabs = () => {
    let selectedTab = null;

    // Prioritize showing validation errors
    const errorElement = document.querySelector('[role=tabpanel] .invalid-feedback, [role=tabpanel] .has-error, [role=tabpanel] .errorlist');
    if (errorElement) {
        const panel = errorElement.closest('[role=tabpanel]');
        if (panel) {
            const tabId = panel.getAttribute('aria-labelledby');
            if (tabId) {
                selectedTab = document.getElementById(tabId);
            }
        }
    }

    if (!selectedTab) { selectedTab = getTabFromHash() }
    if (!selectedTab) { selectedTab = document.querySelector(`${TAB_SELECTOR}:checked`) }
    if (!selectedTab) { selectedTab = document.querySelector(TAB_SELECTOR) }
    if (!selectedTab) return

    selectedTab.checked = true
    updateTabPanels()

    document.querySelectorAll(`${TAB_SELECTOR}`).forEach((element) => {
        element.addEventListener('change', updateTabPanels)
    })

    // If the URL fragment changes, e.g. by navigating backwards, update the tab
    window.addEventListener('hashchange', () => {
        selectedTab = getTabFromHash()
        if (selectedTab) {
            selectedTab.checked = true
            updateTabPanels()
        }
    })
}

if (document.querySelector(TAB_SELECTOR)) {
  initTabs()
}
