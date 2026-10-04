/**
 * Client-side required check for Tiptap rich-text fields.
 * Empty HTML such as <p></p> must not pass when the textarea is required.
 */

const INVISIBLE_CHARS_RE = /[\u200b\u200c\u200d\u2060\ufeff\u00ad]/g

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

function ensureErrorElement(wrapper, message) {
  let error = wrapper.querySelector('[data-richtext-required-error]')
  if (!error) {
    error = document.createElement('div')
    error.className = 'invalid-feedback d-block'
    error.setAttribute('data-richtext-required-error', 'true')
    wrapper.appendChild(error)
  }
  error.textContent = message
  return error
}

function clearError(wrapper) {
  wrapper.querySelector('[data-richtext-required-error]')?.remove()
  wrapper.classList.remove('is-invalid')
}

function syncAndValidateTextarea(textarea) {
  const editor = textarea.__eventyayTiptapEditor
  if (editor) {
    textarea.value = editor.getHTML()
  }
  const wrapper = textarea.closest('[data-tiptap-wrapper]')
  if (!textarea.required) {
    if (wrapper) clearError(wrapper)
    textarea.setCustomValidity('')
    return true
  }
  const message =
    textarea.dataset.requiredMessage ||
    textarea.getAttribute('data-required-message') ||
    'This field is required.'
  if (isEmptyRichText(textarea.value)) {
    textarea.setCustomValidity(message)
    if (wrapper) {
      wrapper.classList.add('is-invalid')
      ensureErrorElement(wrapper, message)
      editor?.commands?.focus?.()
    }
    return false
  }
  textarea.setCustomValidity('')
  if (wrapper) clearError(wrapper)
  return true
}

function bindLiveValidation(textarea) {
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
  const textareas = form.querySelectorAll('textarea[data-tiptap-profile][required]')
  if (!textareas.length) return

  let valid = true
  textareas.forEach((textarea) => {
    bindLiveValidation(textarea)
    if (!syncAndValidateTextarea(textarea)) valid = false
  })
  if (!valid) {
    event.preventDefault()
    event.stopPropagation()
  }
}

function init() {
  document.querySelectorAll('textarea[data-tiptap-profile][required]').forEach((textarea) => {
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
