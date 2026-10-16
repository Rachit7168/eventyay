/**
 * Shared entry point for proposal edit form session video rows.
 * Re-exports and delegates to the unified session video controller.
 */

export function initSessionVideoLinks(root = document) {
    if (typeof window !== 'undefined' && typeof window.initSubmissionVideoFormset === 'function') {
        return window.initSubmissionVideoFormset(root)
    }
}

export default initSessionVideoLinks
