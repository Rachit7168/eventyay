from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from unittest.mock import patch
from django.utils.timezone import now
from django_scopes import scope
from pypdf import PdfReader

from eventyay.base.models import (
    Event,
    Product as Item,
    ProductVariation as ItemVariation,
    Order,
    OrderPosition,
    Organizer,
)
from eventyay.plugins.ticketoutputpdf.ticketoutput import PdfTicketOutput


@pytest.fixture
def env0():
    o = Organizer.objects.create(name='Dummy', slug='dummy')
    event = Event.objects.create(organizer=o, name='Dummy', slug='dummy', date_from=now(), live=True)
    o1 = Order.objects.create(
        code='FOOBAR',
        event=event,
        email='dummy@dummy.test',
        status=Order.STATUS_PENDING,
        datetime=now(),
        expires=now() + timedelta(days=10),
        total=Decimal('13.37'),
    )
    shirt = Item.objects.create(event=event, name='T-Shirt', default_price=12)
    shirt_red = ItemVariation.objects.create(item=shirt, default_price=14, value='Red')
    OrderPosition.objects.create(
        order=o1,
        item=shirt,
        variation=shirt_red,
        price=12,
        attendee_name_parts={},
        secret='1234',
    )
    OrderPosition.objects.create(
        order=o1,
        item=shirt,
        variation=shirt_red,
        price=12,
        attendee_name_parts={},
        secret='5678',
    )
    return event, o1


@pytest.mark.django_db
def test_generate_pdf(env0):
    event, order = env0
    with scope(organizer=event.organizer, event=event):
        event.settings.set('ticketoutput_pdf_code_x', 30)
        event.settings.set('ticketoutput_pdf_code_y', 50)
        event.settings.set('ticketoutput_pdf_code_s', 2)
        o = PdfTicketOutput(event)
        fname, ftype, buf = o.generate(order.positions.first())
        assert ftype == 'application/pdf'
        pdf = PdfReader(BytesIO(buf))
        assert len(pdf.pages) == 1


@pytest.mark.django_db
def test_generate_pdf_currency_symbol_fallback(env0):
    event, order = env0
    event.currency = 'INR'
    event.save()
    with scope(organizer=event.organizer, event=event):
        event.settings.set('ticketoutput_pdf_code_x', 30)
        event.settings.set('ticketoutput_pdf_code_y', 50)
        event.settings.set('ticketoutput_pdf_code_s', 2)
        
        o = PdfTicketOutput(event)
        # Force a font that lacks the currency symbol
        o.override_layout = [
            {
                'type': 'textarea',
                'left': '10.00',
                'bottom': '10.00',
                'fontsize': '16.0',
                'color': [0, 0, 0, 1],
                'fontfamily': 'Open Sans',
                'bold': False,
                'italic': False,
                'width': '100.00',
                'content': 'price',
                'text': '',
                'align': 'left',
            }
        ]
        
        # Test font fallback (it should still output the symbol because Open Sans doesn't support ₹, but wait, we are removing the fallback font logic!
        # If Open Sans doesn't support ₹, and we removed the fallback font logic, then it should ALWAYS substitute it with the ISO code!)
        # So we just test that the ISO code fallback works when the primary font doesn't support the symbol.
        with patch('eventyay.base.pdf.font_supports_text', return_value=False):
            fname, ftype, buf = o.generate(order.positions.first())
            assert ftype == 'application/pdf'
            pdf = PdfReader(BytesIO(buf))
            assert len(pdf.pages) == 1
            
            text = ''
            for page in pdf.pages:
                text += page.extract_text()
                
            # Verify the fallback regex substitutes the ISO code
            assert 'INR' in text
            # Ensure the symbol does not appear in the PDF bytes when ISO code is used
            assert b'\xe2\x82\xb9' not in buf
