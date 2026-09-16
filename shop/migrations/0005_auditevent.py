from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0004_usertokenstate')]

    operations = [
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('occurred_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('action', models.CharField(db_index=True, max_length=40)),
                ('actor_id', models.BigIntegerField(blank=True, db_index=True, null=True)),
                ('source', models.CharField(default='system', max_length=80)),
                ('request_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('object_type', models.CharField(blank=True, max_length=80)),
                ('object_id', models.CharField(blank=True, max_length=64)),
                ('changes', models.JSONField(default=dict)),
            ],
            options={
                'ordering': ['-occurred_at', '-id'],
                'default_permissions': ('view',),
                'indexes': [models.Index(fields=['object_type', 'object_id'], name='audit_object_idx')],
            },
        ),
    ]
