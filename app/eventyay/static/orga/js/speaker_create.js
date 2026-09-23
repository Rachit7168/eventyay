/**
 * speaker_create.js
 *
 * ES module for the "Add speaker" creation form.
 * Handles:
 *  - Show/hide the "Create new session" fields based on the add_session checkbox.
 *  - Show/hide the "Link existing session" section based on the link_existing_session checkbox.
 *  - Mutual exclusivity between the two session options.
 *  - Toggling email field required-ness when "no email" is checked.
 */

(function () {
  'use strict';

  function init() {
    const addSessionCheckbox = document.getElementById('id_add_session');
    const linkExistingCheckbox = document.getElementById('id_link_existing_session');
    const noEmailCheckbox = document.getElementById('id_no_email');
    const sessionSection = document.getElementById('session_section');
    const existingSessionSection = document.getElementById('existing_session_section');
    const emailField = document.getElementById('id_email');
    const emailWrapper = emailField ? emailField.closest('.form-group') : null;

    // --- Session section toggling ---

    function applySessionSections() {
      const addChecked = addSessionCheckbox && addSessionCheckbox.checked;
      const linkChecked = linkExistingCheckbox && linkExistingCheckbox.checked;

      if (sessionSection) {
        sessionSection.classList.toggle('d-none', !addChecked);
        // Disable inputs in the hidden new-session section so stale data
        // isn't included in the POST when the section is not visible.
        sessionSection.querySelectorAll('input, select, textarea').forEach(function (el) {
          el.disabled = !addChecked;
        });
      }

      if (existingSessionSection) {
        // For the existing-session section we only toggle visibility.
        // The enhanced select widget can't be re-enabled via .disabled after
        // it has already initialised, so we rely solely on d-none to hide it.
        // The server ignores existing_session_id when link_existing_session is off.
        existingSessionSection.classList.toggle('d-none', !linkChecked);
      }
    }

    if (addSessionCheckbox) {
      addSessionCheckbox.addEventListener('change', function () {
        // Mutual exclusivity: uncheck link_existing when add_session is checked
        if (addSessionCheckbox.checked && linkExistingCheckbox) {
          linkExistingCheckbox.checked = false;
        }
        applySessionSections();
      });
    }

    if (linkExistingCheckbox) {
      linkExistingCheckbox.addEventListener('change', function () {
        // Mutual exclusivity: uncheck add_session when link_existing is checked
        if (linkExistingCheckbox.checked && addSessionCheckbox) {
          addSessionCheckbox.checked = false;
        }
        applySessionSections();
      });
    }

    // --- Email field toggling ---

    function applyEmailState() {
      if (!noEmailCheckbox || !emailField) return;
      const noEmail = noEmailCheckbox.checked;
      if (emailWrapper) {
        emailWrapper.classList.toggle('d-none', noEmail);
      }
      emailField.disabled = noEmail;
    }

    if (noEmailCheckbox) {
      noEmailCheckbox.addEventListener('change', applyEmailState);
    }

    // Apply initial state on page load
    applySessionSections();
    applyEmailState();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
