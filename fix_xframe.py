with open('app/eventyay/plugins/badges/views.py', 'r') as f:
    content = f.read()

if 'xframe_options_sameorigin' not in content:
    content = content.replace(
        'from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView',
        'from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView\nfrom django.views.decorators.clickjacking import xframe_options_sameorigin\nfrom django.utils.decorators import method_decorator'
    )

content = content.replace(
    'class BadgeCachedDownloadView(DownloadView):\n    def get(self, request, *args, **kwargs):',
    'class BadgeCachedDownloadView(DownloadView):\n    @method_decorator(xframe_options_sameorigin)\n    def get(self, request, *args, **kwargs):'
)

with open('app/eventyay/plugins/badges/views.py', 'w') as f:
    f.write(content)
