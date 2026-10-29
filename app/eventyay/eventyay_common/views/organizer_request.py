import hashlib

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET
from django.views.generic import FormView, TemplateView

from eventyay.base.forms.organizer_request import OrganizerRequestForm, validate_request_slug
from eventyay.base.models import OrganizerRequest
from eventyay.base.services.organizer_requests import notify_submission


class OrganizerRequestCreate(FormView):
    form_class = OrganizerRequestForm
    template_name = 'eventyay_common/organizer_request/form.html'
    success_url = reverse_lazy('organizer_request.success')

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'request': self.request}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'site_url': settings.SITE_URL.rstrip('/')}

    def post(self, request, *args, **kwargs):
        key = 'organizer_request:' + hashlib.sha256((request.META.get('REMOTE_ADDR') or 'unknown').encode()).hexdigest()
        if cache.add(key, 1, timeout=3600):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                cache.add(key, 1, timeout=3600)
                count = 1
        if count > 10:
            response = HttpResponse(_('Too many requests. Please try again in an hour.'), status=429)
            response['Retry-After'] = '3600'
            return response
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                application = form.save()
                transaction.on_commit(lambda: notify_submission(application))
        except IntegrityError:
            collision = False
            for field in ('email', 'slug'):
                if OrganizerRequest.objects.filter(
                    **{f'{field}__iexact': form.cleaned_data[field]}, status='pending'
                ).exists():
                    form.add_error(field, _('There is already a pending request with this value.'))
                    collision = True
            if not collision:
                raise
            return self.form_invalid(form)
        return super().form_valid(form)


class OrganizerRequestSuccess(TemplateView):
    template_name = 'eventyay_common/organizer_request/success.html'


@require_GET
def slug_available(request):
    try:
        validate_request_slug(request.GET.get('slug', ''))
    except ValidationError as exc:
        return JsonResponse({'available': False, 'message': ' '.join(exc.messages)})
    return JsonResponse({'available': True, 'message': _('This short form is available.')})
