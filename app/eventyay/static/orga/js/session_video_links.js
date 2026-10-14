/**
 * Add and remove session-video URL rows on the proposal edit form.
 * Rows are cloned from a <template> so new inputs are not built with innerHTML.
 */

function bindSessionVideoRow(row) {
    const removeButton = row.querySelector('[data-session-video-remove]')
    if (!removeButton || removeButton.dataset.sessionVideoBound === 'true') return
    removeButton.dataset.sessionVideoBound = 'true'
    removeButton.addEventListener('click', () => {
        row.remove()
    })
}

export function initSessionVideoLinks(root = document) {
    const formset = root.matches?.('[data-session-video-formset]')
        ? root
        : root.querySelector?.('[data-session-video-formset]')
    if (!formset || formset.dataset.sessionVideoReady === 'true') return
    formset.dataset.sessionVideoReady = 'true'

    const rows = formset.querySelector('[data-session-video-rows]')
    const emptyRow = formset.querySelector('[data-session-video-empty-row]')
    const addButton = formset.querySelector('[data-session-video-add]')
    if (!rows || !(emptyRow instanceof HTMLTemplateElement) || !addButton) return

    rows.querySelectorAll('[data-session-video-row]').forEach(bindSessionVideoRow)

    addButton.addEventListener('click', () => {
        const newRow = emptyRow.content.querySelector('[data-session-video-row]')
        if (!newRow) return
        const row = newRow.cloneNode(true)
        rows.appendChild(row)
        bindSessionVideoRow(row)
        const input = row.querySelector('input')
        if (input) input.focus()
    })
}

initSessionVideoLinks()
