/**
 * Client-side required check for Tiptap rich-text fields.
 * Empty HTML such as <p></p> must not pass when the textarea is required.
 */

function isEmptyRichText(html) {
  if (!html) return true
  const tmp = document.createElement('div')
  tmp.innerHTML = String(html)
  return !(tmp.textContent || '').replace(/\u00a0/g, ' ').trim()
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

function onSubmit(event) {
  const form = event.target
  if (!(form instanceof HTMLFormElement)) return
  const textareas = form.querySelectorAll('textarea[data-tiptap-profile][required]')
  if (!textareas.length) return

  let valid = true
  textareas.forEach((textarea) => {
    if (!syncAndValidateTextarea(textarea)) valid = false
  })
  if (!valid) {
    event.preventDefault()
    event.stopPropagation()
  }
}

document.addEventListener('submit', onSubmit, true)
