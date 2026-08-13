import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventyay.config.settings')
django.setup()

from eventyay.base.models import Event
e = Event.objects.first()
print("hasattr before delete:", hasattr(e, 'cfp'))
if hasattr(e, 'cfp'):
    e.cfp.delete()
print("hasattr after delete:", hasattr(e, 'cfp'))
