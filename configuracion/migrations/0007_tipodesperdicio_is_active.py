# Generated by Django 4.2.21 on 2025-06-02 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuracion', '0006_alter_lamina_options_lamina_actualizado_en_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipodesperdicio',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Activo'),
        ),
    ]
