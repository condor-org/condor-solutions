from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('turnos_padel', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='abonomes',
            name='fecha_limite_renovacion',
            field=models.DateField(null=True, blank=True),
        ),
    ]
