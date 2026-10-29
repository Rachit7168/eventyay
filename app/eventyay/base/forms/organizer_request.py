from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, RegexValidator
from django.utils.translation import gettext_lazy as _

from eventyay.base.models import Organizer, OrganizerRequest
from eventyay.base.services.turnstile import TurnstileValidationMixin


def validate_request_slug(slug: str, *, exclude_request_id: int | None = None) -> str:
    RegexValidator(
        r'^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z',
        _('Use lowercase letters, numbers, dots and dashes, starting and ending with a letter or number.'),
    )(slug)
    Organizer._meta.get_field('slug').clean(slug, None)
    if Organizer.objects.filter(slug__iexact=slug).exists():
        raise ValidationError(_('This short form is already taken.'))
    pending = OrganizerRequest.objects.filter(slug__iexact=slug, status=OrganizerRequest.Status.PENDING)
    if exclude_request_id is not None:
        pending = pending.exclude(pk=exclude_request_id)
    if pending.exists():
        raise ValidationError(_('This short form is reserved by a pending request.'))
    return slug


class OrganizerRequestReviewForm(forms.ModelForm):
    class Meta:
        model = OrganizerRequest
        fields = ('organizer_name', 'slug')
        labels = {'organizer_name': _('Organiser name on Eventyay'), 'slug': _('Short form')}

    def clean_slug(self):
        return validate_request_slug(self.cleaned_data['slug'], exclude_request_id=self.instance.pk)


class OrganizerRequestForm(TurnstileValidationMixin, OrganizerRequestReviewForm):
    turnstile_action = 'organizer_create'
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta(OrganizerRequestReviewForm.Meta):
        fields = ('name', 'email', 'affiliation', 'events', 'organizer_name', 'slug')
        labels = {
            **OrganizerRequestReviewForm.Meta.labels,
            'name': _('Your name'),
            'email': _('Email'),
            'affiliation': _('Affiliation'),
            'events': _('Events you have organised or want to organise'),
        }
        help_texts = {
            'email': _(
                "We'll send updates about your request here. If approved, this email gets access to "
                'the organiser account. If you already have an Eventyay account, use the same email.'
            ),
            'affiliation': _("The organisation, community, company or university you're organising events for."),
            'events': _(
                'Tell us about your events, e.g. name, type (conference, meetup, workshop) and a link if you have one.'
            ),
            'organizer_name': _(
                'The name shown publicly on your event pages, e.g. "FOSSASIA", you can change it later.'
            ),
            'slug': _(
                'A short name used in all your web addresses. Use lowercase letters, numbers, dots and'
                " dashes only. This can't be changed later, so choose carefully."
            ),
        }

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        self.fields['events'].validators.append(MaxLengthValidator(10000))
        self.fields['events'].widget.attrs['maxlength'] = 10000
        self.fields['slug'].widget.attrs['aria-describedby'] = 'id_slug_helptext slug-preview slug-status'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if OrganizerRequest.objects.filter(email__iexact=email, status=OrganizerRequest.Status.PENDING).exists():
            raise ValidationError(_('There is already a pending request for this email address.'))
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('website'):
            raise ValidationError(_('Unable to submit this request.'))
        self.clean_turnstile()
        return cleaned


class OrganizerRequestRejectForm(forms.Form):
    reason = forms.CharField(label=_('Reason (optional)'), required=False, max_length=10000, widget=forms.Textarea)
