# Generated by Django 5.0.6 on 2024-12-02 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EcoVestidoor', '0009_remove_venta_productos_venta_metodo_pago'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_logged_in',
            field=models.BooleanField(default=False),
        ),
    ]
