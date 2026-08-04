with open('app/eventyay/static/pretixbase/js/asynctask.js', 'r') as f:
    content = f.read()

# Replace the specific try/catch block for print
content = content.replace(
'''            $iframe.off("load").on("load", function() {
                try {
                    this.contentWindow.print();
                } catch(e) {
                    console.log("Could not auto-print: ", e);
                }
            });''',
'''            $iframe.off("load");'''
)

with open('app/eventyay/static/pretixbase/js/asynctask.js', 'w') as f:
    f.write(content)
