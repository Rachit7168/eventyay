# Generated manually

from django.db import migrations
import markdown
import re

def is_tiptap_html(text):
    if not text:
        return False
    text_str = str(text).strip()
    return bool(re.match(r'^\s*<(p|ul|ol|blockquote|h[1-6])(\s|>)', text_str, re.IGNORECASE))

def convert_markdown_to_html(apps, schema_editor):
    Page = apps.get_model('base', 'Page')
    
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
        ]
    )
    
    for page in Page.objects.all():
        if page.text:
            text_data = page.text.data
            if isinstance(text_data, dict):
                new_data = {}
                changed = False
                for lang, text in text_data.items():
                    if text and not is_tiptap_html(text):
                        new_data[lang] = md.reset().convert(str(text))
                        changed = True
                    else:
                        new_data[lang] = text
                if changed:
                    page.text.data = new_data
                    page.save(update_fields=['text'])
            elif isinstance(text_data, str) and text_data and not is_tiptap_html(text_data):
                page.text.data = md.reset().convert(text_data)
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
