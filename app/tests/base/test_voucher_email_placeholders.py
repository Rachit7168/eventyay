"""Voucher bulk-email placeholders."""

from types import SimpleNamespace

from eventyay.base.email import voucher_redemption_urls
from eventyay.common.forms.widgets import EmailEditorWidget
from eventyay.control.forms.vouchers import VoucherBulkForm


def test_voucher_redemption_urls_link_each_code(monkeypatch):
    def fake_uri(event, urlname, kwargs=None):
        assert urlname == 'presale:event.redeem'
        return 'https://shop.example/ccc/30c3/redeem/'

    monkeypatch.setattr('eventyay.multidomain.urlreverse.build_absolute_uri', fake_uri)

    rendered = voucher_redemption_urls(SimpleNamespace(), ['ABCDE', 'A B&C'])

    assert rendered == (
        '<a href="https://shop.example/ccc/30c3/redeem/?voucher=ABCDE">'
        'https://shop.example/ccc/30c3/redeem/?voucher=ABCDE</a>'
        '<br>'
        '<a href="https://shop.example/ccc/30c3/redeem/?voucher=A%20B%26C">'
        'https://shop.example/ccc/30c3/redeem/?voucher=A%20B%26C</a>'
    )


def test_bulk_voucher_email_uses_tiptap_editor():
    field = VoucherBulkForm.base_fields['send_message']
    assert isinstance(field.widget, EmailEditorWidget)
    assert field.widget.attrs['data-tiptap-profile'] == 'email'
    assert '{voucher_url_list}' in field.initial
