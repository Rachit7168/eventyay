function getCsrfToken(container) {
  const input = (container || document).querySelector('input[name="csrfmiddlewaretoken"]')
  return input ? input.value : ''
}

function showPreviewError(target) {
  target.textContent = typeof window.gettext === 'function' ? window.gettext('Preview could not be loaded.') : 'Preview could not be loaded.'
}

function replaceHtml(target, html) {
  const parsed = new DOMParser().parseFromString(html || '', 'text/html')
  target.replaceChildren(...parsed.body.childNodes)
}

function isLocaleFieldVisible(fieldEl) {
  const container = fieldEl?.closest?.('.tiptap-wrapper') || fieldEl
  if (!container) return false
  if (container.hidden) return false
  return container.style.display !== 'none'
}

function getPreviewTextareas(wrapper) {
  return Array.from(wrapper.querySelectorAll('textarea[data-tiptap-profile], textarea[lang], textarea')).filter(
    (textarea) => isLocaleFieldVisible(textarea),
  )
}

function buildPreviewBlocks(wrapper, textareas) {
  const previewList = wrapper.querySelector('[data-richtext-preview-list]')
  if (!previewList) {
    const singleBlock = wrapper.querySelector('.richtext-preview')
    return singleBlock ? [singleBlock] : []
  }

  previewList.replaceChildren()
  const blocks = []

  textareas.forEach((textarea) => {
    const block = document.createElement('div')
    block.className = 'richtext-preview well'
    const lang = textarea.getAttribute('lang')
    if (lang) block.setAttribute('lang', lang)
    previewList.appendChild(block)
    blocks.push(block)
  })

  return blocks
}

async function loadRichTextPreview(wrapper) {
  const previewUrl = wrapper.getAttribute('data-richtext-preview-url')
  if (!previewUrl) return

  const form = wrapper.closest('form')
  const textareas = getPreviewTextareas(wrapper)
  const previewBlocks = buildPreviewBlocks(wrapper, textareas)
  if (!previewBlocks.length) return

  const params = new URLSearchParams()
  const localizedBlocks = previewBlocks.filter((block) => block.getAttribute('lang'))

  if (localizedBlocks.length) {
    textareas.forEach((textarea) => {
      const lang = textarea.getAttribute('lang')
      if (lang) params.append(`content_${lang}`, textarea.value)
    })
  } else if (textareas[0]) {
    params.append('content', textareas[0].value)
  }

  try {
    const response = await fetch(previewUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(form),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      credentials: 'same-origin',
      body: params,
    })
    if (!response.ok) throw new Error(`Preview request failed: ${response.status}`)
    const data = await response.json()

    if (data.previews) {
      localizedBlocks.forEach((block) => {
        replaceHtml(block, data.previews[block.getAttribute('lang')] || '')
      })
      return
    }

    if (previewBlocks[0]) {
      replaceHtml(previewBlocks[0], data.html || '')
    }
  } catch (err) {
    console.error('Rich text preview failed:', err)
    previewBlocks.forEach((block) => showPreviewError(block))
  }
}

function initRichTextPreviewTabs() {
  document.querySelectorAll('[data-richtext-preview-tab]').forEach((tab) => {
    if (tab.dataset.richtextPreviewBound === 'true') return
    tab.dataset.richtextPreviewBound = 'true'

    const wrapper = tab.closest('[data-richtext-preview-wrapper]')
    if (!wrapper) return

    tab.addEventListener('click', () => {
      loadRichTextPreview(wrapper)
    })
  })
}

function initEmailPreviewTabs() {
  document.querySelectorAll('[data-email-preview-tab]').forEach((tab) => {
    const wrapper = tab.closest('[data-email-preview-wrapper]')
    if (!wrapper) return

    const previewUrl = wrapper.getAttribute('data-email-preview-url')
    const blocks = wrapper.querySelectorAll('.mail-preview')
    if (!previewUrl || !blocks.length) return

    const form = wrapper.closest('form')

    tab.addEventListener('click', async () => {
      const params = new URLSearchParams()
      const textareas = wrapper.querySelectorAll('textarea')
      textareas.forEach((textarea) => {
        const lang = textarea.getAttribute('lang')
        params.append(lang ? `body_${lang}` : 'body', textarea.value)
      })

      try {
        const response = await fetch(previewUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(form),
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          credentials: 'same-origin',
          body: params,
        })
        if (!response.ok) throw new Error(`Preview request failed: ${response.status}`)
        const data = await response.json()
        const previews = data.previews || {}
        blocks.forEach((block) => {
          replaceHtml(block, previews[block.getAttribute('lang')])
        })
      } catch (err) {
        console.error('Email preview failed:', err)
        blocks.forEach((block) => showPreviewError(block))
      }
    })
  })
}

function init() {
  initRichTextPreviewTabs()
  initEmailPreviewTabs()
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true })
} else {
  init()
}

window.addEventListener('eventyay:tiptap-ready', () => {
  initRichTextPreviewTabs()
})
