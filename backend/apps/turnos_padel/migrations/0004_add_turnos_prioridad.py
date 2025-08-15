from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("turnos_padel", "0003_add_turnos_reservados"),
        ("turnos_core", "0001_initial"),  # Ajustar si tenés una posterior
    ]

    operations = [
        migrations.AddField(
            model_name="abonomes",
            name="turnos_prioridad",
            field=models.ManyToManyField(
                to="turnos_core.Turno",
                related_name="abonos_prioritarios",
                blank=True,
            ),
        ),
    ]
