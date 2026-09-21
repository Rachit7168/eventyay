export function initSpeakerCreate() {
    const addSessionCheckbox = document.getElementById("id_add_session");
    const sessionSection = document.getElementById("session_section");
    
    function toggleSessionSection() {
        if (addSessionCheckbox && sessionSection) {
            const inputs = sessionSection.querySelectorAll('input, select, textarea');
            if (addSessionCheckbox.checked) {
                sessionSection.style.display = "block";
                for (let i = 0; i < inputs.length; i++) {
                    inputs[i].disabled = false;
                }
            } else {
                sessionSection.style.display = "none";
                for (let i = 0; i < inputs.length; i++) {
                    inputs[i].disabled = true;
                }
            }
        }
    }
    
    if (addSessionCheckbox) {
        addSessionCheckbox.addEventListener("change", toggleSessionSection);
        toggleSessionSection();
    }

    const noEmailCheckbox = document.getElementById("id_no_email");
    const emailInput = document.getElementById("id_email");
    
    function toggleEmailRequired() {
        if (noEmailCheckbox && emailInput) {
            const formGroup = emailInput.closest('.form-group');
            const asterisk = formGroup ? formGroup.querySelector('label span.text-danger') : null;
            if (noEmailCheckbox.checked) {
                emailInput.required = false;
                if (formGroup) formGroup.style.display = 'none';
                if (asterisk) asterisk.style.display = 'none';
            } else {
                emailInput.required = true;
                if (formGroup) formGroup.style.display = '';
                if (asterisk) asterisk.style.display = 'inline';
            }
        }
    }
    
    if (noEmailCheckbox) {
        noEmailCheckbox.addEventListener("change", toggleEmailRequired);
        toggleEmailRequired();
    }
}

document.addEventListener("DOMContentLoaded", initSpeakerCreate);
