# apps/turnos_padel/serializers.py
from rest_framework import serializers
from apps.turnos_core.models import Lugar, Turno
from django.db.models import Q
from apps.turnos_padel.models import (
    ConfiguracionSedePadel,
    TipoClasePadel,
    TipoAbonoPadel,
    AbonoMes,
    TIPO_CODIGO_CHOICES,  # catálogo x1..x4
)
from apps.turnos_padel.utils import proximo_mes
import logging
logger = logging.getLogger(__name__)

from django.utils import timezone


# ===== Catálogos =====
class TipoClasePadelSerializer(serializers.ModelSerializer):
    # id opcional para soportar UPSERT en listas embebidas
    id = serializers.IntegerField(required=False)

    class Meta:
        model = TipoClasePadel
        fields = ["id", "codigo", "precio", "activo"]


class TipoAbonoPadelSerializer(serializers.ModelSerializer):
    # id opcional para soportar UPSERT en listas embebidas
    id = serializers.IntegerField(required=False)

    class Meta:
        model = TipoAbonoPadel
        fields = ["id", "codigo", "precio", "activo"]


# ===== Configuración de Sede (incluye catálogos embebidos) =====
class ConfiguracionSedePadelSerializer(serializers.ModelSerializer):
    # Embebemos catálogos para edición masiva desde el front
    tipos_clase = TipoClasePadelSerializer(many=True)
    tipos_abono = TipoAbonoPadelSerializer(many=True, required=False)

    class Meta:
        model = ConfiguracionSedePadel
        fields = ["id", "alias", "cbu_cvu", "tipos_clase", "tipos_abono"]

    def update(self, instance, validated_data):
        """
        Upsert de catálogos por id/código + cleanup de no enviados.
        ✔️ Idempotente respecto al payload: lo no enviado se elimina.
        ⚠️ Mantiene side-effect de borrar tipos no incluidos.
        """
        tipos_data = validated_data.pop("tipos_clase", [])
        tipos_abono_data = validated_data.pop("tipos_abono", [])

        # alias / CBU
        instance.alias = validated_data.get("alias", instance.alias)
        instance.cbu_cvu = validated_data.get("cbu_cvu", instance.cbu_cvu)
        instance.save()

        # ---- Tipos de Clase (upsert + prune)
        vistos_ids = set()
        for tc in tipos_data:
            tc_id = tc.get("id")
            tc_codigo = tc.get("codigo")
            if tc_id:
                obj = instance.tipos_clase.get(id=tc_id)  # 404->500: asumimos front envía ids válidos
                obj.codigo = tc_codigo or obj.codigo
                obj.precio = tc.get("precio", obj.precio)
                obj.activo = tc.get("activo", obj.activo)
                obj.save()
                vistos_ids.add(obj.id)
            else:
                try:
                    obj = instance.tipos_clase.get(codigo=tc_codigo)
                    obj.precio = tc.get("precio", obj.precio)
                    obj.activo = tc.get("activo", obj.activo)
                    obj.save()
                except TipoClasePadel.DoesNotExist:
                    obj = TipoClasePadel.objects.create(configuracion_sede=instance, **tc)
                vistos_ids.add(obj.id)

        # Elimina los tipos no presentes en el payload (prune)
        instance.tipos_clase.exclude(id__in=list(vistos_ids)).delete()

        # ---- Tipos de Abono (upsert + prune)
        vistos_ids = set()
        for ta in tipos_abono_data:
            ta_id = ta.get("id")
            ta_codigo = ta.get("codigo")
            if ta_id:
                obj = instance.tipos_abono.get(id=ta_id)
                obj.codigo = ta_codigo or obj.codigo
                obj.precio = ta.get("precio", obj.precio)
                obj.activo = ta.get("activo", obj.activo)
                obj.save()
                vistos_ids.add(obj.id)
            else:
                try:
                    obj = instance.tipos_abono.get(codigo=ta_codigo)
                    obj.precio = ta.get("precio", obj.precio)
                    obj.activo = ta.get("activo", obj.activo)
                    obj.save()
                except TipoAbonoPadel.DoesNotExist:
                    obj = TipoAbonoPadel.objects.create(configuracion_sede=instance, **ta)
                vistos_ids.add(obj.id)

        instance.tipos_abono.exclude(id__in=list(vistos_ids)).delete()
        return instance


# ===== Sede con configuración embebida =====
class SedePadelSerializer(serializers.ModelSerializer):
    # Incluye configuración para creación/edición en un solo request
    configuracion_padel = ConfiguracionSedePadelSerializer()

    class Meta:
        model = Lugar
        fields = [
            "id", "nombre", "direccion", "referente", "telefono", "configuracion_padel"
        ]

    def create(self, validated_data):
        """
        Crea la sede + configuración + catálogos por defecto (x1..x4).
        🔐 Cliente se toma del usuario salvo super_admin (debe enviarlo).
        """
        config_data = validated_data.pop("configuracion_padel", {})
        tipos_data = config_data.pop("tipos_clase", [])
        tipos_abono_data = config_data.pop("tipos_abono", [])

        user = self.context["request"].user
        if user.tipo_usuario == "super_admin":
            cliente = validated_data.pop("cliente", None)
            if not cliente:
                raise serializers.ValidationError("Debe especificar un cliente si es super_admin.")
        else:
            # Evita que un admin_cliente/empleado fuerce cliente distinto
            validated_data.pop("cliente", None)
            cliente = user.cliente

        sede = Lugar.objects.create(cliente=cliente, **validated_data)

        # Crear configuración base
        config = ConfiguracionSedePadel.objects.create(
            sede=sede,
            alias=config_data.get("alias", ""),
            cbu_cvu=config_data.get("cbu_cvu", "")
        )

        # Tipos de clase (default si no se proveen)
        if tipos_data:
            for t in tipos_data:
                TipoClasePadel.objects.create(configuracion_sede=config, **t)
        else:
            for t in [
                {"codigo": "x1", "precio": 0, "activo": True},
                {"codigo": "x2", "precio": 0, "activo": True},
                {"codigo": "x3", "precio": 0, "activo": True},
                {"codigo": "x4", "precio": 0, "activo": True},
            ]:
                TipoClasePadel.objects.create(configuracion_sede=config, **t)

        # Tipos de abono (default si no se proveen)
        if tipos_abono_data:
            for ta in tipos_abono_data:
                TipoAbonoPadel.objects.create(configuracion_sede=config, **ta)
        else:
            for ta in [
                {"codigo": "x1", "precio": 0, "activo": True},
                {"codigo": "x2", "precio": 0, "activo": True},
                {"codigo": "x3", "precio": 0, "activo": True},
                {"codigo": "x4", "precio": 0, "activo": True},
            ]:
                TipoAbonoPadel.objects.create(configuracion_sede=config, **ta)

        return sede

    def update(self, instance, validated_data):
        """
        Actualiza datos básicos de la sede y delega configuración (alias/CBU + catálogos).
        ✔️ Asegura config si no existiese.
        """
        conf_data = validated_data.pop("configuracion_padel", None)

        # Datos básicos (safe set)
        for field in ["nombre", "direccion", "referente", "telefono"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        # Asegurar config y delegar actualización granular
        if conf_data is not None:
            config = getattr(instance, "configuracion_padel", None)
            if config is None:
                config = ConfiguracionSedePadel.objects.create(sede=instance)
            ConfiguracionSedePadelSerializer().update(config, conf_data)

        return instance


# ===== Turnos compactos para incrustar en detalles =====
class TurnoSimpleSerializer(serializers.ModelSerializer):
    lugar = serializers.StringRelatedField()  # usa __str__ de Lugar (ligero para listados)

    class Meta:
        model = Turno
        fields = ["id", "fecha", "hora", "lugar", "estado"]


# ===== Abono (detalle enriquecido para read) =====
class AbonoMesDetailSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()
    sede = serializers.StringRelatedField()
    prestador = serializers.StringRelatedField()
    tipo_clase = TipoClasePadelSerializer()
    turnos_reservados = TurnoSimpleSerializer(many=True)
    turnos_prioridad = TurnoSimpleSerializer(many=True)

    class Meta:
        model = AbonoMes
        fields = [
            "id", "usuario", "sede", "prestador",
            "anio", "mes", "dia_semana", "hora", "tipo_clase",
            "monto", "estado", "fecha_limite_renovacion",
            "turnos_reservados", "turnos_prioridad",
            "creado_en", "actualizado_en"
        ]


# ===== Abono (serializer base para create/update) =====
class AbonoMesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbonoMes
        fields = [
            "id", "usuario", "sede", "prestador", "anio", "mes", "dia_semana", "hora",
            "tipo_clase", "tipo_abono", "monto", "estado", "creado_en", "actualizado_en", "fecha_limite_renovacion"
        ]
        read_only_fields = ["estado", "creado_en", "actualizado_en", "fecha_limite_renovacion"]
        # Evitamos UniqueTogetherValidator implícito; se valida manualmente por estado="pagado"
        validators = []
        # 'monto' es sugerido/calc. por backend; no obligatorio en payload
        extra_kwargs = {
            "monto": {"required": False, "allow_null": True}
        }

    def validate(self, attrs):
        """
        Validaciones de negocio para garantizar consistencia del abono:
        - Unicidad condicional de franja si ya existe un 'pagado'.
        - Todo debe pertenecer al mismo cliente (multi-tenant).
        - tipo_clase y (si viene) tipo_abono deben corresponder a la sede.
        - Debe haber turnos generados y libres en todas las fechas requeridas:
          * Mes actual: solo fechas >= hoy.
          * Mes siguiente: todas las fechas del patrón.
        """
        usuario = attrs["usuario"]
        sede = attrs["sede"]
        prestador = attrs["prestador"]
        tipo_clase = attrs["tipo_clase"]
        anio, mes = attrs["anio"], attrs["mes"]
        dia_semana, hora = attrs["dia_semana"], attrs["hora"]

        # 0) Unicidad condicional por franja (solo choca con 'pagado')
        existe_pagado = AbonoMes.objects.filter(
            sede=sede, prestador=prestador, anio=anio, mes=mes,
            dia_semana=dia_semana, hora=hora, estado="pagado"
        ).exists()
        if existe_pagado:
            logger.warning(
                "[abonos.validate][unique] franja tomada sede=%s prestador=%s %04d-%02d dsem=%s hora=%s",
                getattr(sede, 'id', None), getattr(prestador, 'id', None),
                anio, mes, dia_semana, hora
            )
            raise serializers.ValidationError({
                "franja": "Ya existe un abono pagado para esa franja (sede, prestador, día y hora)."
            })

        # 1) Consistencia de cliente (scope multi-tenant)
        cliente_id = sede.cliente_id
        if not (
            getattr(usuario, "cliente_id", None) == cliente_id and
            prestador.cliente_id == cliente_id and
            tipo_clase.configuracion_sede.sede.cliente_id == cliente_id
        ):
            logger.warning(
                "[abonos.validate][cliente_mismatch] usuario=%s(%s) sede=%s(%s) prestador=%s(%s) tipo_clase.sede=%s(%s)",
                getattr(usuario, "id", None), getattr(usuario, "cliente_id", None),
                sede.id, sede.cliente_id,
                prestador.id, prestador.cliente_id,
                tipo_clase.configuracion_sede.sede_id,
                tipo_clase.configuracion_sede.sede.cliente_id
            )
            raise serializers.ValidationError("Todos los elementos del abono deben pertenecer al mismo cliente.")

        # 2) tipo_clase debe pertenecer a la sede seleccionada
        if tipo_clase.configuracion_sede.sede_id != sede.id:
            raise serializers.ValidationError({
                "tipo_clase": "El tipo de clase no pertenece a la sede seleccionada."
            })

        # Helpers
        def _proximo_mes(anio_i, mes_i):
            return (anio_i + 1, 1) if mes_i == 12 else (anio_i, mes_i + 1)

        # 3) Validar existencia y disponibilidad de TODOS los turnos requeridos
        hoy = timezone.localdate()
        fechas_actual_todas = self._fechas_del_mes_por_dia_semana(anio, mes, dia_semana)
        # Mes actual: solo futuro (>= hoy)
        fechas_actual = [d for d in fechas_actual_todas if d >= hoy]

        prox_anio, prox_mes = _proximo_mes(anio, mes)
        fechas_prox = self._fechas_del_mes_por_dia_semana(prox_anio, prox_mes, dia_semana)

        logger.debug(
            "[abonos.validate] hoy=%s anio=%s mes=%s dsem=%s -> actual_total=%s actual_fut=%s prox=%s",
            hoy, anio, mes, dia_semana, len(fechas_actual_todas), len(fechas_actual), len(fechas_prox)
        )

        if not fechas_actual and not fechas_prox:
            raise serializers.ValidationError("No hay fechas futuras para ese día de semana en este ni en el próximo mes.")

        def _chequear_mes(fechas, etiqueta):
            qs = Turno.objects.filter(
                fecha__in=fechas, hora=hora, lugar=sede,
                content_type__model="prestador", object_id=prestador.id
            ).only("id", "fecha", "estado")
            turnos_map = {t.fecha: t for t in qs}

            # Deben existir todos los turnos del patrón
            faltantes = [f for f in fechas if f not in turnos_map]
            if faltantes:
                logger.warning(
                    "[abonos.validate][faltantes] etiqueta=%s faltan=%s ej=%s",
                    etiqueta, len(faltantes), faltantes[:3]
                )
                raise serializers.ValidationError({
                    etiqueta: f"Faltan turnos generados para {len(faltantes)} fecha(s)."
                })

            # Ninguno debe estar reservado
            reservados = [t for t in turnos_map.values() if t.estado == "reservado"]
            if reservados:
                logger.warning(
                    "[abonos.validate][reservados] etiqueta=%s count=%s",
                    etiqueta, len(reservados)
                )
                raise serializers.ValidationError({
                    etiqueta: "Hay turnos ya reservados en la franja; no se puede crear el abono."
                })

        if fechas_actual:
            _chequear_mes(fechas_actual, "mes_actual")
        if fechas_prox:
            _chequear_mes(fechas_prox, "mes_siguiente")

        # 4) tipo_abono (si viene) debe pertenecer a la misma sede
        tipo_abono = attrs.get("tipo_abono")
        if tipo_abono and tipo_abono.configuracion_sede.sede_id != sede.id:
            raise serializers.ValidationError({
                "tipo_abono": "El tipo de abono no pertenece a la sede seleccionada."
            })

        return attrs

    @staticmethod
    def _fechas_del_mes_por_dia_semana(anio: int, mes: int, dia_semana: int):
        """Devuelve todas las fechas del mes que caen en 'dia_semana' (0=lunes..6=domingo)."""
        from calendar import Calendar
        fechas = []
        for week in Calendar(firstweekday=0).monthdatescalendar(anio, mes):
            for d in week:
                if d.month == mes and d.weekday() == dia_semana:
                    fechas.append(d)
        return fechas

    # Calcula 'monto' automáticamente si no viene (usa precio del tipo_abono o tipo_clase)
    def create(self, validated_data):
        tipo_abono = validated_data.get("tipo_abono") or validated_data.get("tipo_clase")
        monto_in = validated_data.get("monto", None)

        if monto_in in (None, ""):
            precio = getattr(tipo_abono, "precio", None)
            if precio is None:
                logger.warning(
                    "[abonos.create][no_precio] tipo_abono=%s tipo_clase=%s -> monto=0",
                    getattr(validated_data.get("tipo_abono"), "id", None),
                    getattr(validated_data.get("tipo_clase"), "id", None),
                )
                validated_data["monto"] = 0
            else:
                validated_data["monto"] = precio

        logger.info(
            "[abonos.create] usuario=%s sede=%s prestador=%s dsem=%s hora=%s anio=%s mes=%s tipo=%s monto=%s",
            getattr(validated_data.get("usuario"), "id", None),
            getattr(validated_data.get("sede"), "id", None),
            getattr(validated_data.get("prestador"), "id", None),
            validated_data.get("dia_semana"),
            validated_data.get("hora"),
            validated_data.get("anio"),
            validated_data.get("mes"),
            getattr(tipo_abono, "id", None),
            validated_data.get("monto"),
        )
        return super().create(validated_data)

    # Incluye 'monto_sugerido' en la representación (UX front)
    def to_representation(self, instance):
        data = super().to_representation(instance)
        tipo_ref = getattr(instance, "tipo_abono", None) or getattr(instance, "tipo_clase", None)
        data["monto_sugerido"] = getattr(tipo_ref, "precio", None) if tipo_ref else None
        return data
