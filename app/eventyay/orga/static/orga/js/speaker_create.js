export function initSpeakerCreate() {
    const addSessionCheckbox = document.getElementById("id_add_session");
    const sessionSection = document.getElementById("session_section");
    
    function toggleSessionSection() {
        if (addSessionCheckbox && sessionSection) {
            const inputs = sessionSection.querySelectorAll('input, select, textarea');
            if (addSessionCheckbox.checked) {
                sessionSection.classList.remove("d-none");
                for (let i = 0; i < inputs.length; i++) {
                    inputs[i].disabled = false;
                }
            } else {
                sessionSection.classList.add("d-none");
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
                if (formGroup) formGroup.classList.add('d-none');
                if (asterisk) asterisk.classList.add('d-none');
            } else {
                emailInput.required = true;
                if (formGroup) formGroup.classList.remove('d-none');
                if (asterisk) asterisk.classList.remove('d-none');
            }
        }
    }
    
    if (noEmailCheckbox) {
        noEmailCheckbox.addEventListener("change", toggleEmailRequired);
        toggleEmailRequired();
    }
}

document.addEventListener("DOMContentLoaded", initSpeakerCreate);
