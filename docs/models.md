# 📦 Modelos Backend - Proyecto App Turnos Pádel

## 🛡️ auth\_core

```python
class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    tipo_usuario = models.CharField(max_length=30, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email or self.username
```

---

## 📅 turnos\_core

```python
class Lugar(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(blank=True, null=True)
    referente = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="servicios")
    lugar = models.ForeignKey("Lugar", on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.lugar})" if self.lugar else self.nombre


class Turno(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("confirmado", "Confirmado"), ("cancelado", "Cancelado"), ("vencido", "Vencido")]

    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True, related_name="turnos")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    recurso = GenericForeignKey("content_type", "object_id")
    lugar = models.ForeignKey("Lugar", on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("fecha", "hora", "content_type", "object_id")

    def __str__(self):
        base = f"{self.fecha} {self.hora} reservado por {self.usuario}"
        return f"{base} - {self.servicio}" if self.servicio else f"{base} en {self.recurso}"
```

---

## 💰 pagos\_core

```python
class PagoIntento(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("pre_aprobado", "Preaprobado"), ("rechazado", "Rechazado"), ("confirmado", "Confirmado")]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    monto_esperado = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10, default="ARS")
    alias_destino = models.CharField(max_length=100)
    cbu_destino = models.CharField(max_length=64, blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    origen = GenericForeignKey("content_type", "object_id")
    tiempo_expiracion = models.DateTimeField()
    external_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    id_transaccion_banco = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pago de {self.usuario} - {self.estado}"


def comprobante_upload_path(instance, filename):
    return f"comprobantes/turno_{instance.turno.id}/{filename}"


class ComprobantePago(models.Model):
    turno = models.OneToOneField(Turno, on_delete=models.CASCADE, related_name="comprobante", null=True, blank=True)
    archivo = models.FileField(upload_to=comprobante_upload_path)
    hash_archivo = models.CharField(max_length=64, unique=True)
    valido = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    datos_extraidos = models.JSONField(blank=True, null=True)
    nro_operacion = models.CharField(max_length=100, blank=True, null=True)
    emisor_nombre = models.CharField(max_length=255, blank=True, null=True)
    emisor_cbu = models.CharField(max_length=22, blank=True, null=True)
    emisor_cuit = models.CharField(max_length=20, blank=True, null=True)
    fecha_detectada = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Comprobante #{self.pk} – Turno {self.turno_id}"


class ConfiguracionPago(models.Model):
    destinatario = models.CharField(max_length=255)
    cbu = models.CharField(max_length=22)
    alias = models.CharField(max_length=100, blank=True)
    monto_esperado = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_maximo_minutos = models.IntegerField(default=60)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CBU: {self.cbu} – Monto esperado: {self.monto_esperado}"
```

---

## 🎾 turnos\_padel\_core

```python
class Profesor(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    especialidad = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True)
    sedes = models.ManyToManyField(Lugar, through="Disponibilidad", related_name="profesores")

    def __str__(self):
        return self.nombre


class Disponibilidad(models.Model):
    profesor = models.ForeignKey("Profesor", on_delete=models.CASCADE, related_name="disponibilidades")
    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE)
    dia_semana = models.IntegerField(choices=[(0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo")])
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profesor", "lugar", "dia_semana", "hora_inicio", "hora_fin")

    def __str__(self):
        return f"{self.profesor} en {self.lugar} los {self.get_dia_semana_display()} de {self.hora_inicio} a {self.hora_fin}"
```
