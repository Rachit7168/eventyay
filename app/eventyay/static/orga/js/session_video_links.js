/**
 * Add and remove session-video URL rows on the proposal edit form.
 * Rows are cloned from a <template> so new inputs are not built with innerHTML.
 */

function bindSessionVideoRow(row, onRemove) {
    const removeButton = row.querySelector('[data-session-video-remove]')
    if (!removeButton || removeButton.dataset.sessionVideoBound === 'true') return
    removeButton.dataset.sessionVideoBound = 'true'
    removeButton.addEventListener('click', () => {
        row.remove()
        onRemove()
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

    const maxRows = Number.parseInt(formset.dataset.maxRows || '', 10)
    const atRowLimit = () => Number.isFinite(maxRows)
        && rows.querySelectorAll('[data-session-video-row]').length >= maxRows

    const syncAddButton = () => {
        addButton.disabled = atRowLimit()
    }

    const onRemove = () => {
        syncAddButton()
    }

    rows.querySelectorAll('[data-session-video-row]').forEach((row) => {
        bindSessionVideoRow(row, onRemove)
    })
    syncAddButton()

    addButton.addEventListener('click', () => {
        if (atRowLimit()) return
        const newRow = emptyRow.content.querySelector('[data-session-video-row]')
        if (!newRow) return
        const row = newRow.cloneNode(true)
        rows.appendChild(row)
        bindSessionVideoRow(row, onRemove)
        syncAddButton()
        const input = row.querySelector('input')
        if (input) input.focus()
    })
}

initSessionVideoLinks()
