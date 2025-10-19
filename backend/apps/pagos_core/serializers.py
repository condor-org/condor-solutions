# apps/pagos_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.turnos_core.models import Turno
from apps.pagos_core.models import ComprobantePago, ComprobanteAbono
from apps.turnos_padel.models import AbonoMes  # 🧩 requerido por ComprobanteAbonoUploadSerializer


class ComprobanteUploadSerializer(serializers.Serializer):
    """
    Subida de comprobante para un turno individual.
    - Valida existencia y pertenencia del turno (multi-tenant).
    - Aplica validaciones básicas de archivo (extensión/peso).
    """
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField()

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        archivo = attrs["archivo"]
        user = self.context["request"].user

        # 1) Turno existente
        try:
            turno = Turno.objects.select_related("usuario").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "Turno no encontrado"})

        # 2) Scope por rol/cliente
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.context['request'])
        cliente_actual = getattr(self.context['request'], 'cliente_actual', None)
        
        if rol_actual == "usuario_final" and turno.usuario_id != user.id:
            raise serializers.ValidationError({"turno_id": "No tenés permiso sobre este turno"})
        elif rol_actual == "admin_cliente" and cliente_actual:
            # Verificar que el usuario del turno tiene roles en el cliente actual
            from apps.auth_core.models import UserClient
            if not UserClient.objects.filter(
                usuario=turno.usuario,
                cliente=cliente_actual,
                activo=True
            ).exists():
                raise serializers.ValidationError({"turno_id": "No tenés permiso sobre este turno"})

        # 3) Archivo: tamaño/extensión (hard limit 3MB; extensiones controladas)
        max_size = 3 * 1024 * 1024  # 3MB
        if archivo.size > max_size:
            raise serializers.ValidationError({"archivo": "El archivo no puede superar 3 MB"})

        ext = archivo.name.rsplit(".", 1)[-1].lower()
        allowed_ext = {"pdf", "png", "jpg", "jpeg", "webp", "bmp"}
        if ext not in allowed_ext:
            raise serializers.ValidationError({"archivo": f"Extensión no permitida: {ext}"})

        return attrs

    def create(self, validated_data):
        """
        Delegamos el procesamiento a ComprobanteService (OCR + reglas).
        """
        from apps.pagos_core.services.comprobantes import ComprobanteService

        turno_id = validated_data["turno_id"]
        archivo = validated_data["archivo"]
        usuario = self.context["request"].user

        try:
            # Hints de contexto para el service (cliente)
            validated_data["cliente"] = usuario.cliente
            comprobante = ComprobanteService.upload_comprobante(
                turno_id=turno_id,
                file_obj=archivo,
                usuario=usuario
            )
            return comprobante
        except DjangoValidationError as e:
            # Normalizamos a DRF ValidationError
            raise serializers.ValidationError({"error": e.messages})


class ComprobantePagoSerializer(LoggedModelSerializer):
    """
    Serializer de lectura para listados de comprobantes.
    - Enriquece con datos denormalizados del turno (usuario, profesor, sede, cliente).
    - Usa LoggedModelSerializer para trazabilidad de serialización.
    """
    usuario_nombre = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    turno_hora = serializers.SerializerMethodField()
    profesor_nombre = serializers.SerializerMethodField()
    sede_nombre = serializers.SerializerMethodField()
    especialidad_nombre = serializers.SerializerMethodField()
    cliente_nombre = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    estado_pago = serializers.SerializerMethodField()
    monto = serializers.SerializerMethodField()

    class Meta:
        model = ComprobantePago
        fields = [
            "id",
            "created_at",
            "turno_id",
            "valido",
            "datos_extraidos",
            "usuario_nombre",
            "usuario_email",
            "turno_hora",
            "profesor_nombre",
            "sede_nombre",
            "especialidad_nombre",
            "cliente_nombre",
            "tipo",
            "tipo_display",
            "estado_pago",
            "monto",
        ]

    # ⚠️ En estos getters se usa print() para logs de error.
    #    Recomendación: migrar a logging.getLogger(__name__).exception(...) para consistencia.

    def get_usuario_nombre(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno and obj.turno.usuario:
                return (
                    obj.turno.usuario.get_full_name()
                    or obj.turno.usuario.username
                    or obj.turno.usuario.email
                )
            # Si no tiene turno (rechazado), buscar en PagoIntento
            else:
                from django.contrib.contenttypes.models import ContentType
                from apps.pagos_core.models import PagoIntento
                ct = ContentType.objects.get_for_model(ComprobantePago)
                pago_intento = PagoIntento.objects.filter(
                    content_type=ct,
                    object_id=obj.id
                ).first()
                if pago_intento:
                    return (
                        pago_intento.usuario.get_full_name()
                        or pago_intento.usuario.username
                        or pago_intento.usuario.email
                    )
            return ""
        except Exception as e:
            print(f"[DEBUG] usuario_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_usuario_email(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno and obj.turno.usuario:
                return obj.turno.usuario.email
            # Si no tiene turno (rechazado), buscar en PagoIntento
            else:
                from django.contrib.contenttypes.models import ContentType
                from apps.pagos_core.models import PagoIntento
                ct = ContentType.objects.get_for_model(ComprobantePago)
                pago_intento = PagoIntento.objects.filter(
                    content_type=ct,
                    object_id=obj.id
                ).first()
                if pago_intento:
                    return pago_intento.usuario.email
            return ""
        except Exception as e:
            print(f"[DEBUG] usuario_email ERROR comprobante {obj.id}: {e}")
            return ""

    def get_turno_hora(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno:
                return obj.turno.hora.strftime("%H:%M")
            # Si no tiene turno (rechazado), mostrar información del comprobante
            else:
                datos = obj.datos_extraidos or {}
                fecha_detectada = datos.get('fecha_detectada')
                if fecha_detectada:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(fecha_detectada.replace('Z', '+00:00'))
                        return dt.strftime("%H:%M")
                    except:
                        pass
            return None
        except Exception as e:
            print(f"[DEBUG] turno_hora ERROR comprobante {obj.id}: {e}")
            return None

    def get_profesor_nombre(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno:
                recurso = obj.turno.recurso
                if hasattr(recurso, "nombre_publico"):
                    return recurso.nombre_publico
                return str(recurso)
            # Si no tiene turno (rechazado), mostrar información del comprobante
            else:
                datos = obj.datos_extraidos or {}
                return datos.get('nombre_destinatario', '')
        except Exception as e:
            print(f"[DEBUG] profesor_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_sede_nombre(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno:
                return obj.turno.lugar.nombre
            # Si no tiene turno (rechazado), usar información del cliente
            else:
                return obj.cliente.nombre
        except Exception as e:
            print(f"[DEBUG] sede_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_cliente_nombre(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno:
                return obj.turno.lugar.cliente.nombre
            # Si no tiene turno (rechazado), usar información directa del cliente
            else:
                return obj.cliente.nombre
        except Exception as e:
            print(f"[DEBUG] cliente_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_especialidad_nombre(self, obj):
        try:
            # Si tiene turno, usar la información del turno
            if obj.turno:
                recurso = obj.turno.recurso
                if hasattr(recurso, "especialidad"):
                    return recurso.especialidad
            # Si no tiene turno (rechazado), mostrar información del comprobante
            else:
                datos = obj.datos_extraidos or {}
                return datos.get('motivo_cancelacion', '')
            return ""
        except Exception as e:
            print(f"[DEBUG] especialidad_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_tipo(self, obj):
        """Obtener el tipo de comprobante (turno o abono)"""
        return getattr(obj, 'tipo', 'turno')

    def get_tipo_display(self, obj):
        """Obtener el nombre legible del tipo"""
        return getattr(obj, 'tipo_display', 'Clase Individual')

    def get_estado_pago(self, obj):
        """Determina el estado del pago basándose en el PagoIntento asociado"""
        try:
            from django.contrib.contenttypes.models import ContentType
            from apps.pagos_core.models import PagoIntento
            
            ct = ContentType.objects.get_for_model(ComprobantePago)
            pago_intento = PagoIntento.objects.filter(
                content_type=ct,
                object_id=obj.id
            ).first()
            
            if pago_intento:
                return pago_intento.estado
            else:
                # Si no hay PagoIntento, asumir pendiente
                return "pendiente"
        except Exception as e:
            print(f"[DEBUG] estado_pago ERROR comprobante {obj.id}: {e}")
            return "pendiente"

    def get_monto(self, obj):
        """Obtiene el monto del comprobante desde datos_extraidos o PagoIntento"""
        try:
            # Primero intentar desde datos_extraidos
            datos = obj.datos_extraidos or {}
            monto = datos.get('monto')
            if monto is not None:
                return float(monto)
            
            # Si no hay monto en datos_extraidos, buscar en PagoIntento
            from django.contrib.contenttypes.models import ContentType
            from apps.pagos_core.models import PagoIntento
            
            ct = ContentType.objects.get_for_model(ComprobantePago)
            pago_intento = PagoIntento.objects.filter(
                content_type=ct,
                object_id=obj.id
            ).first()
            
            if pago_intento:
                return float(pago_intento.monto_esperado)
            
            return 0.0
        except Exception as e:
            print(f"[DEBUG] monto ERROR comprobante {obj.id}: {e}")
            return 0.0


class ComprobanteUnificadoSerializer(serializers.Serializer):
    """
    Serializer unificado para mostrar tanto ComprobantePago como ComprobanteAbono
    en la lista de pagos preaprobados.
    """
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    tipo = serializers.CharField()
    tipo_display = serializers.CharField()
    valido = serializers.BooleanField()
    datos_extraidos = serializers.JSONField()
    
    # Campos específicos de turnos
    turno_id = serializers.IntegerField(required=False)
    usuario_nombre = serializers.CharField(required=False)
    usuario_email = serializers.CharField(required=False)
    turno_hora = serializers.TimeField(required=False)
    profesor_nombre = serializers.CharField(required=False)
    sede_nombre = serializers.CharField(required=False)
    especialidad_nombre = serializers.CharField(required=False)
    cliente_nombre = serializers.CharField(required=False)
    
    # Campos específicos de abonos
    abono_mes_id = serializers.IntegerField(required=False)
    abono_mes_anio = serializers.IntegerField(required=False)
    abono_mes_mes = serializers.IntegerField(required=False)
    abono_mes_precio = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    abono_mes_configuracion_personalizada = serializers.JSONField(required=False)


class TurnoReservaSerializer(serializers.Serializer):
    """
    Reserva de un turno (con/sin comprobante según rol).
    - usuario_final: requiere archivo (comprobante).
    - admin_cliente: puede reservar sin archivo.
    - Valida existencia del turno, que no esté reservado, y pertenencia al cliente.
    """
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False)

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        archivo = attrs.get("archivo")
        user = self.context["request"].user

        # Obtener rol actual
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.context['request'])
        cliente_actual = getattr(self.context['request'], 'cliente_actual', None)
        
        # Turno existente y libre
        try:
            turno = Turno.objects.select_related("usuario", "prestador__cliente").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "El turno no existe."})
        if turno.usuario is not None:
            raise serializers.ValidationError({"turno_id": "Ese turno ya está reservado."})

        # Reglas por rol
        if rol_actual == "usuario_final":
            # Debe subir comprobante y el turno debe pertenecer a su cliente
            if not archivo:
                raise serializers.ValidationError({"archivo": "Debés subir un comprobante."})
            if cliente_actual and turno.prestador.cliente_id != cliente_actual.id:
                raise serializers.ValidationError({"turno_id": "No tenés acceso a este turno."})

            # Validación básica del archivo (mismo criterio que ComprobanteUploadSerializer)
            max_size = 3 * 1024 * 1024
            if archivo.size > max_size:
                raise serializers.ValidationError({"archivo": "El archivo no puede superar 3 MB"})
            ext = archivo.name.rsplit(".", 1)[-1].lower()
            allowed_ext = {"pdf", "png", "jpg", "jpeg", "webp", "bmp"}
            if ext not in allowed_ext:
                raise serializers.ValidationError({"archivo": f"Extensión no permitida: {ext}"})

        elif rol_actual == "admin_cliente":
            # Puede reservar sin archivo pero debe pertenecer a su cliente
            if cliente_actual and turno.prestador.cliente_id != cliente_actual.id:
                raise serializers.ValidationError({"turno_id": "No tenés acceso a este turno."})
        else:
            # Otros roles no participan de este flujo
            raise serializers.ValidationError("No tenés permiso para reservar turnos.")

        return attrs

    def create(self, validated_data):
        """
        Persiste la reserva:
        - admin_cliente: sin comprobante.
        - usuario_final: sube comprobante y luego reserva.
        """
        from apps.pagos_core.services.comprobantes import ComprobanteService

        user = self.context["request"].user
        turno_id = validated_data["turno_id"]
        archivo = validated_data.get("archivo")
        
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.context['request'])

        turno = Turno.objects.get(pk=turno_id)

        # admin_cliente → reserva directa
        if rol_actual == "admin_cliente":
            turno.usuario = user
            turno.estado = "reservado"
            turno.save(update_fields=["usuario", "estado"])
            return turno

        # usuario_final → procesa comprobante antes de reservar
        comprobante = ComprobanteService.upload_comprobante(
            turno_id=turno_id,
            file_obj=archivo,
            usuario=user
        )
        turno = comprobante.turno
        turno.usuario = user
        turno.estado = "reservado"
        turno.save(update_fields=["usuario", "estado"])
        return turno


class ComprobanteAbonoSerializer(LoggedModelSerializer):
    """
    Serializer para listado de ComprobanteAbono.
    """
    abono_mes_id = serializers.IntegerField(source="abono_mes.id", read_only=True)
    abono_mes_anio = serializers.IntegerField(source="abono_mes.anio", read_only=True)
    abono_mes_mes = serializers.IntegerField(source="abono_mes.mes", read_only=True)
    abono_mes_precio = serializers.DecimalField(source="abono_mes.precio", max_digits=10, decimal_places=2, read_only=True)
    abono_mes_configuracion_personalizada = serializers.JSONField(source="abono_mes.configuracion_personalizada", read_only=True)
    abono_mes_renovado = serializers.BooleanField(source="abono_mes.renovado", read_only=True)
    abono_mes_fecha_limite_renovacion = serializers.DateField(source="abono_mes.fecha_limite_renovacion", read_only=True)
    abono_mes_dia_semana = serializers.IntegerField(source="abono_mes.dia_semana", read_only=True)
    abono_mes_dia_semana_label = serializers.SerializerMethodField()
    abono_mes_hora = serializers.TimeField(source="abono_mes.hora", read_only=True)
    abono_mes_hora_text = serializers.SerializerMethodField()
    abono_mes_prestador_nombre = serializers.SerializerMethodField()
    usuario_nombre = serializers.CharField(source="abono_mes.usuario.nombre", read_only=True)
    usuario_email = serializers.CharField(source="abono_mes.usuario.email", read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)
    tipo = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    es_renovacion = serializers.SerializerMethodField()
    estado_pago = serializers.SerializerMethodField()
    monto = serializers.SerializerMethodField()

    class Meta:
        model = ComprobanteAbono
        fields = [
            "id",
            "created_at",
            "valido",
            "datos_extraidos",
            "abono_mes_id",
            "abono_mes_anio",
            "abono_mes_mes",
            "abono_mes_precio",
            "abono_mes_configuracion_personalizada",
            "abono_mes_renovado",
            "abono_mes_fecha_limite_renovacion",
            "abono_mes_dia_semana",
            "abono_mes_dia_semana_label",
            "abono_mes_hora",
            "abono_mes_hora_text",
            "abono_mes_prestador_nombre",
            "usuario_nombre",
            "usuario_email",
            "cliente_nombre",
            "tipo",
            "tipo_display",
            "es_renovacion",
            "estado_pago",
            "monto",
        ]

    def get_tipo(self, obj):
        return 'abono'

    def get_tipo_display(self, obj):
        return 'Abono Mensual'

    def get_es_renovacion(self, obj):
        """Determina si este comprobante es de una renovación de abono."""
        abono = obj.abono_mes
        if not abono:
            return False
        
        # Es renovación si:
        # 1. El abono está marcado como renovado, O
        # 2. Tiene fecha límite de renovación (indica que es renovación)
        return abono.renovado or bool(abono.fecha_limite_renovacion)

    def get_estado_pago(self, obj):
        """Determina el estado del pago basándose en el PagoIntento asociado"""
        try:
            from django.contrib.contenttypes.models import ContentType
            from apps.pagos_core.models import PagoIntento
            
            ct = ContentType.objects.get_for_model(ComprobanteAbono)
            pago_intento = PagoIntento.objects.filter(
                content_type=ct,
                object_id=obj.id
            ).first()
            
            if pago_intento:
                return pago_intento.estado
            else:
                # Si no hay PagoIntento, asumir pendiente
                return "pendiente"
        except Exception as e:
            print(f"[DEBUG] estado_pago ERROR comprobante abono {obj.id}: {e}")
            return "pendiente"

    def get_monto(self, obj):
        """Obtiene el monto del comprobante desde datos_extraidos o PagoIntento"""
        try:
            # Primero intentar desde datos_extraidos
            datos = obj.datos_extraidos or {}
            monto = datos.get('monto')
            if monto is not None:
                return float(monto)
            
            # Si no hay monto en datos_extraidos, buscar en PagoIntento
            from django.contrib.contenttypes.models import ContentType
            from apps.pagos_core.models import PagoIntento
            
            ct = ContentType.objects.get_for_model(ComprobanteAbono)
            pago_intento = PagoIntento.objects.filter(
                content_type=ct,
                object_id=obj.id
            ).first()
            
            if pago_intento:
                return float(pago_intento.monto_esperado)
            
            # Si no hay PagoIntento, usar el precio del abono
            if obj.abono_mes:
                return float(obj.abono_mes.precio)
            
            return 0.0
        except Exception as e:
            print(f"[DEBUG] monto ERROR comprobante abono {obj.id}: {e}")
            return 0.0

    def get_abono_mes_dia_semana_label(self, obj):
        """Devuelve el nombre del día de la semana del abono"""
        if not obj.abono_mes:
            return None
        
        DSEM = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_semana = obj.abono_mes.dia_semana
        if 0 <= dia_semana <= 6:
            return DSEM[dia_semana]
        return None

    def get_abono_mes_hora_text(self, obj):
        """Devuelve la hora del abono en formato HH:MM"""
        if not obj.abono_mes or not obj.abono_mes.hora:
            return None
        
        return obj.abono_mes.hora.strftime("%H:%M")

    def get_abono_mes_prestador_nombre(self, obj):
        """Devuelve el nombre del prestador del abono"""
        if not obj.abono_mes or not obj.abono_mes.prestador:
            return None
        
        prestador = obj.abono_mes.prestador
        if prestador.user:
            return f"{prestador.user.nombre} {prestador.user.apellido}".strip()
        return None


class ComprobanteAbonoUploadSerializer(serializers.Serializer):
    """
    Subida de comprobante para un AbonoMes (y aplicación opcional de bonificaciones).
    - `archivo` es requerido solo si el neto a pagar > 0 (lo decide el view/service).
    - `bonificaciones_ids` puede venir vacío (lista opcional).
    """
    abono_mes_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False)  # sólo si monto > 0
    bonificaciones_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    def validate(self, attrs):
        user = self.context["request"].user
        # Abono existente y del mismo cliente
        try:
            abono = AbonoMes.objects.select_related("sede__cliente").get(pk=attrs["abono_mes_id"])
        except AbonoMes.DoesNotExist:
            raise serializers.ValidationError({"abono_mes_id": "Abono no encontrado"})
        # Verificar permisos según el rol
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.context['request'])
        cliente_actual = getattr(self.context['request'], 'cliente_actual', None)
        
        if rol_actual == "admin_cliente" and cliente_actual:
            if abono.sede.cliente_id != cliente_actual.id:
                raise serializers.ValidationError({"abono_mes_id": "No tenés permiso sobre este abono"})
        elif rol_actual == "usuario_final":
            # Usuario final solo puede usar sus propios abonos
            if abono.usuario_id != user.id:
                raise serializers.ValidationError({"abono_mes_id": "No tenés permiso sobre este abono"})
        elif not user.is_super_admin:
            raise serializers.ValidationError({"abono_mes_id": "No tenés permiso sobre este abono"})
        return attrs

    def create(self, validated_data):
        """
        Delegamos el procesamiento al service de comprobantes de abono.
        """
        from apps.pagos_core.services.comprobantes import ComprobanteService
        usuario = self.context["request"].user
        return ComprobanteService.upload_comprobante_abono(
            abono_mes_id=validated_data["abono_mes_id"],
            file_obj=validated_data.get("archivo"),
            usuario=usuario,
            cliente=getattr(usuario, "cliente", None),
            bonificaciones_ids=validated_data.get("bonificaciones_ids") or [],
        )
