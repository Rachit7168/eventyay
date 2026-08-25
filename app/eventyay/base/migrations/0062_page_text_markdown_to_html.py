# Generated manually

from django.db import migrations
from eventyay.base.templatetags.rich_text import compile_markdown
import copy

def convert_markdown_to_html(apps, schema_editor):
    Page = apps.get_model('base', 'Page')
    for page in Page.objects.all():
        if page.text:
            text_data = page.text.data
            if isinstance(text_data, dict):
                new_data = {}
                changed = False
                for lang, text in text_data.items():
                    if text and not str(text).strip().startswith('<'):
                        new_data[lang] = compile_markdown(str(text))
                        changed = True
                    else:
                        new_data[lang] = text
                if changed:
                    page.text.data = new_data
                    page.save(update_fields=['text'])
            elif isinstance(text_data, str) and text_data and not text_data.strip().startswith('<'):
                page.text.data = compile_markdown(text_data)
                page.save(update_fields=['text'])


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0061_price_max_digits_currency_support'),
    ]

    operations = [
        migrations.RunPython(
            convert_markdown_to_html,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
