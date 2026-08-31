from django.db import migrations


def initialize_global_video_settings(apps, schema_editor):
    SettingsStore = apps.get_model('base', 'GlobalSettingsObject_SettingsStore')

    video_settings = [
        'video_jitsi_enabled',
        'video_bbb_enabled',
        'video_janus_enabled',
        'video_streaming_enabled',
        'video_chat_channels_enabled',
        'video_qna_enabled',
        'video_polls_enabled',
    ]

    for key in video_settings:
        if not SettingsStore.objects.filter(key=key).exists():
            SettingsStore.objects.create(key=key, value='True')


def reverse_global_video_settings(apps, schema_editor):
    SettingsStore = apps.get_model('base', 'GlobalSettingsObject_SettingsStore')

    video_settings = [
        'video_jitsi_enabled',
        'video_bbb_enabled',
        'video_janus_enabled',
        'video_streaming_enabled',
        'video_chat_channels_enabled',
        'video_qna_enabled',
        'video_polls_enabled',
    ]

    SettingsStore.objects.filter(key__in=video_settings).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0067_user_profile_picture_user_profile_picture_thumbnail_and_more'),
    ]

    operations = [
        migrations.RunPython(initialize_global_video_settings, reverse_global_video_settings),
    ]
