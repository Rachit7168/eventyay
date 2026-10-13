/**
 * submission_create_speaker.js
 *
 * Manages the speaker section on the "Create proposal" page:
 *  - Toggles the new-speaker form on/off via the "Add new speaker" checkbox.
 *  - Disables the "Link existing speaker" select while the toggle is on.
 *  - Binds the no_email checkbox to show/hide the email field row.
 */

function applyAddNewSpeakerState({ addSpeakerCheckbox, newSpeakerSection, existingSpeakerSection }) {
  const addChecked = Boolean(addSpeakerCheckbox?.checked)

  if (newSpeakerSection) {
    newSpeakerSection.classList.toggle('d-none', !addChecked)
    // Enable/disable all form elements inside so they don't submit when hidden.
    newSpeakerSection.querySelectorAll('input, select, textarea').forEach((el) => {
      el.disabled = !addChecked
    })
  }

  if (existingSpeakerSection) {
    existingSpeakerSection.classList.toggle('is-disabled', addChecked)
    existingSpeakerSection.querySelectorAll('select, button').forEach((el) => {
      el.disabled = addChecked
    })
  }
}

function applyNoEmailState({ noEmailCheckbox, emailField, emailWrapper }) {
  if (!noEmailCheckbox || !emailField) return
  const noEmail = noEmailCheckbox.checked
  if (emailWrapper) {
    emailWrapper.classList.toggle('d-none', noEmail)
  }
  emailField.disabled = noEmail
  emailField.required = !noEmail
}

function bindNoEmailToggle(form) {
  if (!form) return

  const applyFromCheckbox = (checkbox) => {
    // The no_email field name is e.g. "speaker-no_email"; derive the email field name.
    const emailName = checkbox.name.replace(/no_email$/, 'email')
    const emailField = form.querySelector(`[name="${CSS.escape(emailName)}"]`)
    applyNoEmailState({
      noEmailCheckbox: checkbox,
      emailField,
      emailWrapper: emailField ? emailField.closest('.form-group') : null,
    })
  }

  form.addEventListener('change', (event) => {
    const el = event.target
    if (!(el instanceof HTMLInputElement) || !el.name?.endsWith('no_email')) return
    applyFromCheckbox(el)
  })

  // Apply initial state on page load.
  form.querySelectorAll('input[name$="no_email"]').forEach(applyFromCheckbox)
}

function initSubmissionCreateSpeaker() {
  const form = document.querySelector('form[enctype="multipart/form-data"]')
  const addSpeakerCheckbox = document.getElementById('id_add_new_speaker')
  const newSpeakerSection = document.getElementById('new_speaker_section')
  const existingSpeakerSection = document.getElementById('existing_speaker_section')

  if (addSpeakerCheckbox) {
    addSpeakerCheckbox.addEventListener('change', () => {
      applyAddNewSpeakerState({ addSpeakerCheckbox, newSpeakerSection, existingSpeakerSection })
    })
    // Apply on page load (handles back-button / failed POST with toggle on).
    applyAddNewSpeakerState({ addSpeakerCheckbox, newSpeakerSection, existingSpeakerSection })
  }

  bindNoEmailToggle(form)
}

initSubmissionCreateSpeaker()
