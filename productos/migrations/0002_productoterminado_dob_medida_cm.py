# Generated by Django 4.2.21 on 2025-05-20 15:32

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoterminado',
            name='dob_medida_cm',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Medida para el proceso de doblado en centímetros', max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(0.0)], verbose_name='Doblado: Medida (cm)'),
        ),
    ]
