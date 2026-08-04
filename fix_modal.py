import re

with open('app/eventyay/control/templates/pretixcontrol/order/index.html', 'r') as f:
    content = f.read()

content = content.replace('{% include "pretixcontrol/includes/preview_modal.html" %}', '')

# Append to the end of {% block content %}
match = re.search(r'{% endblock %}', content)
if match:
    # find the last {% endblock %} which belongs to custom_header. 
    # Actually, we can just replace the first {% endblock %} if we are careful, 
    # but let's find the end of block content.
    pass

# A safer way: just insert right before the last {% endblock %} which might be custom_header.
# Better to find `{% block content %}` and its closing `{% endblock %}`.
