from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("turnos_padel", "0002_add_fecha_limite_renovacion"),
        ("turnos_core", "0001_initial"),  # Ajustá si tenés una migración posterior
    ]

    operations = [
        migrations.AddField(
            model_name="abonomes",
            name="turnos_reservados",
            field=models.ManyToManyField(
                to="turnos_core.Turno",
                related_name="abonos",
                blank=True,
            ),
        ),
    ]
