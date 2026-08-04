with open('app/eventyay/static/pretixbase/js/asynctask.js', 'r') as f:
    content = f.read()

# Add global var
content = content.replace(
    'var async_task_is_download = false;',
    'var async_task_is_download = false;\nvar async_task_is_print = false;'
)

# Parse it from form
content = content.replace(
    'async_task_is_download = $form.is("[data-asynctask-download]");',
    'async_task_is_download = $form.is("[data-asynctask-download]");\n        async_task_is_print = $form.is("[data-asynctask-print]");'
)

# Handle in check callback
content = content.replace(
'''    if (data.ready && data.redirect) {
        waitingDialog.hide();
        ajaxErrDialog.hide();
        if (async_task_is_download && data.success) {
            _restore_async_old_url_once();
        }
        location.href = data.redirect;
        return;
    }''',
'''    if (data.ready && data.redirect) {
        waitingDialog.hide();
        ajaxErrDialog.hide();
        if (async_task_is_download && data.success) {
            _restore_async_old_url_once();
        }
        if (async_task_is_print && data.success) {
            _restore_async_old_url_once();
            var $iframe = $("#preview-iframe");
            $iframe.off("load").on("load", function() {
                try {
                    this.contentWindow.print();
                } catch(e) {
                    console.log("Could not auto-print: ", e);
                }
            });
            $iframe.attr("src", data.redirect);
            $("#preview-modal").modal("show");
            return;
        }
        location.href = data.redirect;
        return;
    }'''
)

# Handle in initial callback (if it returns instantly)
content = content.replace(
'''    if (data.redirect) {
        waitingDialog.hide();
        if (async_task_is_download && data.success) {
            _restore_async_old_url_once();
        }
        // If we pushed a waiting state earlier, restore the original
        // URL before navigating to the redirect target so the browser's
        // back/forward history behaves as expected.
        if (location.href.indexOf("async_id") !== -1) {
            history.replaceState({}, "pretix", async_task_old_url);
        }
        location.href = data.redirect;
        return;
    }''',
'''    if (data.redirect) {
        waitingDialog.hide();
        if (async_task_is_download && data.success) {
            _restore_async_old_url_once();
        }
        // If we pushed a waiting state earlier, restore the original
        // URL before navigating to the redirect target so the browser's
        // back/forward history behaves as expected.
        if (location.href.indexOf("async_id") !== -1) {
            history.replaceState({}, "pretix", async_task_old_url);
        }
        if (async_task_is_print && data.success) {
            var $iframe = $("#preview-iframe");
            $iframe.off("load").on("load", function() {
                try {
                    this.contentWindow.print();
                } catch(e) {
                    console.log("Could not auto-print: ", e);
                }
            });
            $iframe.attr("src", data.redirect);
            $("#preview-modal").modal("show");
            return;
        }
        location.href = data.redirect;
        return;
    }'''
)

with open('app/eventyay/static/pretixbase/js/asynctask.js', 'w') as f:
    f.write(content)
