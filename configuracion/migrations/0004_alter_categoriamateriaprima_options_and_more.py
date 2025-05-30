# Generated by Django 5.2 on 2025-04-25 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuracion', '0003_ubicacion'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='categoriamateriaprima',
            options={'ordering': ['nombre'], 'verbose_name': 'Categoría Materia Prima', 'verbose_name_plural': 'Categorías Materias Primas'},
        ),
        migrations.AlterModelOptions(
            name='cuentacontable',
            options={'ordering': ['codigo'], 'verbose_name': 'Cuenta Contable', 'verbose_name_plural': 'Cuentas Contables'},
        ),
        migrations.AlterModelOptions(
            name='lamina',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Lámina', 'verbose_name_plural': 'Tipos de Lámina'},
        ),
        migrations.AlterModelOptions(
            name='programalamina',
            options={'ordering': ['nombre'], 'verbose_name': 'Programa de Lámina', 'verbose_name_plural': 'Programas de Lámina'},
        ),
        migrations.AlterModelOptions(
            name='servicio',
            options={'ordering': ['nombre'], 'verbose_name': 'Servicio', 'verbose_name_plural': 'Servicios'},
        ),
        migrations.AlterModelOptions(
            name='tipoimpresion',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Impresión', 'verbose_name_plural': 'Tipos de Impresión'},
        ),
        migrations.AlterModelOptions(
            name='tiposellado',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Sellado', 'verbose_name_plural': 'Tipos de Sellado'},
        ),
        migrations.AlterModelOptions(
            name='tipotinta',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Tinta', 'verbose_name_plural': 'Tipos de Tinta'},
        ),
        migrations.AlterModelOptions(
            name='tipotroquel',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Troquel', 'verbose_name_plural': 'Tipos de Troquel'},
        ),
        migrations.AlterModelOptions(
            name='tipovalvula',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Válvula', 'verbose_name_plural': 'Tipos de Válvula'},
        ),
        migrations.AlterModelOptions(
            name='tipozipper',
            options={'ordering': ['nombre'], 'verbose_name': 'Tipo de Zipper', 'verbose_name_plural': 'Tipos de Zipper'},
        ),
        migrations.AlterModelOptions(
            name='tratamiento',
            options={'ordering': ['nombre'], 'verbose_name': 'Tratamiento Superficie', 'verbose_name_plural': 'Tratamientos Superficie'},
        ),
        migrations.AddField(
            model_name='categoriamateriaprima',
            name='descripcion',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='causaparo',
            name='aplica_a',
            field=models.CharField(blank=True, help_text='Opcional: Tipos de máquina donde aplica', max_length=200),
        ),
        migrations.AlterField(
            model_name='estadoproducto',
            name='nombre',
            field=models.CharField(help_text='Nombre del estado (ej: Activo, Obsoleto).', max_length=50, unique=True, verbose_name='Nombre Estado'),
        ),
        migrations.AlterField(
            model_name='proceso',
            name='orden_flujo',
            field=models.PositiveIntegerField(db_index=True, default=0, help_text='Orden en el flujo productivo estándar (menor=antes)'),
        ),
    ]
