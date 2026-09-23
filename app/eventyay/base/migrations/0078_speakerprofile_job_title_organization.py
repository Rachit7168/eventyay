from django.db import migrations, models
from django_scopes import scope


def migrate_legacy_speaker_role_answers(apps, schema_editor):
    """Copy answers from the old custom-question hack into profile fields."""
    Event = apps.get_model('base', 'Event')
    TalkQuestion = apps.get_model('base', 'TalkQuestion')
    Answer = apps.get_model('base', 'Answer')
    SpeakerProfile = apps.get_model('base', 'SpeakerProfile')

    legacy_keys = {
        'speaker_job_title': 'job_title',
        'speaker_organization': 'organization',
    }

    for event in Event.objects.all():
        with scope(event=event):
            for import_key, profile_field in legacy_keys.items():
                for question in TalkQuestion.objects.filter(event=event, import_key=import_key, target='speaker'):
                    answers = Answer.objects.filter(question=question, person__isnull=False).values(
                        'person_id', 'answer'
                    )
                    for row in answers:
                        answer = (row['answer'] or '').strip()
                        if not answer:
                            continue
                        # Truncate legacy answers to fit within the 255-character limit
                        answer = answer[:255]
                        
                        profile = SpeakerProfile.objects.filter(
                            event=event,
                            user_id=row['person_id'],
                        ).first()
                        if not profile:
                            continue
                        if getattr(profile, profile_field, None):
                            continue
                        setattr(profile, profile_field, answer)
                        profile.save(update_fields=[profile_field])
                    
                    # Deactivate legacy speaker question after migration
                    question.active = False
                    question.save(update_fields=['active'])


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0077_admin_message_center'),
    ]

    operations = [
        migrations.AddField(
            model_name='speakerprofile',
            name='job_title',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Job Title'),
        ),
        migrations.AddField(
            model_name='speakerprofile',
            name='organization',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Organization'),
        ),
        migrations.RunPython(
            migrate_legacy_speaker_role_answers,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
