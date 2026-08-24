document.addEventListener('DOMContentLoaded', function() {
    var dialogTriggers = document.querySelectorAll('[data-toggle="dialog"]');
    for (var i = 0; i < dialogTriggers.length; i++) {
        dialogTriggers[i].addEventListener('click', function(e) {
            e.preventDefault();
            var targetId = this.getAttribute('data-target') || this.getAttribute('data-dialog-target');
            if (targetId) {
                var dialog = document.querySelector(targetId);
                if (dialog && typeof dialog.showModal === 'function') {
                    dialog.showModal();
                } else if (dialog) {
                    dialog.setAttribute('open', '');
                }
            }
        });
    }

    // Handle closing the dialog gracefully if fallback was used
    var dialogForms = document.querySelectorAll('dialog form[method="dialog"]');
    for (var j = 0; j < dialogForms.length; j++) {
        dialogForms[j].addEventListener('submit', function(e) {
            var parentDialog = this.closest('dialog');
            if (parentDialog && typeof parentDialog.close !== 'function') {
                e.preventDefault();
                parentDialog.removeAttribute('open');
            }
        });
    }
});
