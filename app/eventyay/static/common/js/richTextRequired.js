/**
 * Client-side required check for Tiptap rich-text fields.
 * Empty HTML such as <p></p> must not pass when the field is required.
 *
 * Native HTML5 `required` on a display:none textarea is removed: the browser
 * would block submit without showing a message. Validation is handled here.
 */

const INVISIBLE_CHARS_RE = /[\u200b\u200c\u200d\u2060\ufeff\u00ad]/g
const REQUIRED_SELECTOR = 'textarea[data-tiptap-profile][data-richtext-required="true"]'

function decodeBasicEntities(text) {
  return String(text)
    .replace(/&nbsp;/gi, ' ')
    .replace(/&#160;/g, ' ')
    .replace(/&#x0*a0;/gi, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

function isEmptyRichText(html) {
  if (!html) return true
  // Strip tags without assigning to innerHTML (avoids XSS sink / scanner findings).
  const text = decodeBasicEntities(String(html).replace(/<[^>]*>/g, ''))
    .replace(INVISIBLE_CHARS_RE, '')
    .replace(/\u00a0/g, ' ')
    .trim()
  return !text
}

function ensureErrorElement(anchor, message) {
  let error = anchor.querySelector('[data-richtext-required-error]')
  if (!error) {
    error = document.createElement('div')
    error.className = 'invalid-feedback d-block'
    error.setAttribute('data-richtext-required-error', 'true')
    const wrapper = anchor.querySelector('[data-tiptap-wrapper]')
    if (wrapper) {
      wrapper.insertAdjacentElement('afterend', error)
    } else {
      anchor.appendChild(error)
    }
  }
  error.textContent = message
  return error
}

function clearError(anchor) {
  anchor?.querySelector?.('[data-richtext-required-error]')?.remove()
  anchor?.classList?.remove('is-invalid')
  const wrapper = anchor?.querySelector?.('[data-tiptap-wrapper]')
  wrapper?.classList?.remove('is-invalid')
}

function fieldAnchor(textarea) {
  return (
    textarea.closest('.form-group') ||
    textarea.closest('[data-tiptap-wrapper]') ||
    textarea
  )
}

function revealInvalidField(textarea) {
  const editor = textarea.__eventyayTiptapEditor
  const anchor = fieldAnchor(textarea)
  anchor.scrollIntoView({ behavior: 'smooth', block: 'center' })
  if (editor?.commands?.focus) {
    editor.commands.focus('end')
  } else {
    try {
      textarea.focus({ preventScroll: true })
    } catch {
      textarea.focus()
    }
  }
}

function isMarkedRequired(textarea) {
  return textarea.dataset.richtextRequired === 'true'
}

/**
 * Move native required onto a data attribute so the hidden textarea cannot
 * silently block form submit via HTML5 constraint validation.
 */
function adoptNativeRequired(textarea) {
  if (textarea.required || textarea.hasAttribute('required')) {
    textarea.dataset.richtextRequired = 'true'
    if (!textarea.dataset.requiredMessage && !textarea.getAttribute('data-required-message')) {
      textarea.dataset.requiredMessage = 'This field is required.'
    }
    textarea.required = false
    textarea.removeAttribute('required')
  }
}

function syncAndValidateTextarea(textarea) {
  const editor = textarea.__eventyayTiptapEditor
  if (editor) {
    textarea.value = editor.getHTML()
  }
  const anchor = fieldAnchor(textarea)
  const wrapper = textarea.closest('[data-tiptap-wrapper]')
  if (!isMarkedRequired(textarea)) {
    clearError(anchor)
    textarea.setCustomValidity('')
    return true
  }
  const message =
    textarea.dataset.requiredMessage ||
    textarea.getAttribute('data-required-message') ||
    'This field is required.'
  if (isEmptyRichText(textarea.value)) {
    textarea.setCustomValidity(message)
    anchor.classList.add('is-invalid')
    wrapper?.classList?.add('is-invalid')
    ensureErrorElement(anchor, message)
    return false
  }
  textarea.setCustomValidity('')
  clearError(anchor)
  return true
}

function bindLiveValidation(textarea) {
  adoptNativeRequired(textarea)
  if (!isMarkedRequired(textarea)) return

  const revalidate = () => {
    syncAndValidateTextarea(textarea)
  }

  if (!textarea.dataset.richtextRequiredBound) {
    textarea.dataset.richtextRequiredBound = 'true'
    textarea.addEventListener('input', revalidate)
  }

  const editor = textarea.__eventyayTiptapEditor
  if (editor?.on && !textarea.dataset.richtextEditorBound) {
    textarea.dataset.richtextEditorBound = 'true'
    editor.on('update', revalidate)
  }
}

function onSubmit(event) {
  const form = event.target
  if (!(form instanceof HTMLFormElement)) return

  // Adopt required attrs before querying, including late-rendered fields.
  form.querySelectorAll('textarea[data-tiptap-profile]').forEach(adoptNativeRequired)

  const textareas = form.querySelectorAll(REQUIRED_SELECTOR)
  if (!textareas.length) return

  let firstInvalid = null
  textareas.forEach((textarea) => {
    bindLiveValidation(textarea)
    if (!syncAndValidateTextarea(textarea) && !firstInvalid) {
      firstInvalid = textarea
    }
  })
  if (firstInvalid) {
    event.preventDefault()
    event.stopPropagation()
    revealInvalidField(firstInvalid)
  }
}

function init() {
  document.querySelectorAll('textarea[data-tiptap-profile]').forEach((textarea) => {
    bindLiveValidation(textarea)
  })
}

document.addEventListener('submit', onSubmit, true)

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}

// Tiptap mounts asynchronously; bind again when editors are ready.
window.addEventListener('eventyay:tiptap-ready', init)
