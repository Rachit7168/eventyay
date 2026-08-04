with open('app/eventyay/control/templates/pretixcontrol/order/index.html', 'r') as f:
    content = f.read()

content = content.replace('{% include "pretixcontrol/includes/preview_modal.html" %}', '')

content = content.replace(
'''    </div>
{% endblock %}''',
'''    </div>
    {% include "pretixcontrol/includes/preview_modal.html" %}
{% endblock %}'''
)

with open('app/eventyay/control/templates/pretixcontrol/order/index.html', 'w') as f:
    f.write(content)
