# apps/turnos_padel/serializers.py
from rest_framework import serializers
from apps.turnos_core.models import Lugar, Turno
from django.db.models import Q
from apps.turnos_padel.models import (
    ConfiguracionSedePadel,
    TipoClasePadel,
    TipoAbonoPadel,
    AbonoMes,
    TIPO_CODIGO_CHOICES,  # si no lo usás, podés quitarlo sin problema
)
from apps.turnos_padel.utils import proximo_mes
import logging
logger = logging.getLogger(__name__)

class TipoClasePadelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = TipoClasePadel
        fields = ["id", "codigo", "precio", "activo"]

class TipoAbonoPadelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = TipoAbonoPadel
        fields = ["id", "codigo", "precio", "activo"]


class ConfiguracionSedePadelSerializer(serializers.ModelSerializer):
    tipos_clase = TipoClasePadelSerializer(many=True)
    tipos_abono = TipoAbonoPadelSerializer(many=True, required=False)

    class Meta:
        model = ConfiguracionSedePadel
        fields = ["id", "alias", "cbu_cvu", "tipos_clase", "tipos_abono"]

    def update(self, instance, validated_data):
        tipos_data = validated_data.pop("tipos_clase", [])
        tipos_abono_data = validated_data.pop("tipos_abono", [])

        # alias / CBU
        instance.alias = validated_data.get("alias", instance.alias)
        instance.cbu_cvu = validated_data.get("cbu_cvu", instance.cbu_cvu)
        instance.save()

        # ---- Tipos de Clase (upsert por id/codigo; actualiza precio/activo)
        vistos_ids = set()
        for tc in tipos_data:
            tc_id = tc.get("id")
            tc_codigo = tc.get("codigo")
            if tc_id:
                obj = instance.tipos_clase.get(id=tc_id)
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

        instance.tipos_clase.exclude(id__in=list(vistos_ids)).delete()

        # ---- Tipos de Abono (upsert por id/codigo; actualiza precio/activo)
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


class SedePadelSerializer(serializers.ModelSerializer):
    configuracion_padel = ConfiguracionSedePadelSerializer()

    class Meta:
        model = Lugar
        fields = [
            "id", "nombre", "direccion", "referente", "telefono", "configuracion_padel"
        ]

    def create(self, validated_data):
        config_data = validated_data.pop("configuracion_padel", {})
        tipos_data = config_data.pop("tipos_clase", [])
        tipos_abono_data = config_data.pop("tipos_abono", [])

        user = self.context["request"].user
        if user.tipo_usuario == "super_admin":
            cliente = validated_data.pop("cliente", None)
            if not cliente:
                raise serializers.ValidationError("Debe especificar un cliente si es super_admin.")
        else:
            validated_data.pop("cliente", None)
            cliente = user.cliente

        sede = Lugar.objects.create(cliente=cliente, **validated_data)

        # Crear configuración
        config = ConfiguracionSedePadel.objects.create(
            sede=sede,
            alias=config_data.get("alias", ""),
            cbu_cvu=config_data.get("cbu_cvu", "")
        )

        # Tipos de clase
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

        # Tipos de abono
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
        conf_data = validated_data.pop("configuracion_padel", None)

        # Actualizar datos básicos de la sede
        for field in ["nombre", "direccion", "referente", "telefono"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        # Asegurar config y delegar la actualización (alias/cbu + tipos)
        if conf_data is not None:
            config = getattr(instance, "configuracion_padel", None)
            if config is None:
                config = ConfiguracionSedePadel.objects.create(sede=instance)
            ConfiguracionSedePadelSerializer().update(config, conf_data)

        return instance

class TurnoSimpleSerializer(serializers.ModelSerializer):
    lugar = serializers.StringRelatedField()

    class Meta:
        model = Turno
        fields = ["id", "fecha", "hora", "lugar", "estado"]

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

class AbonoMesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbonoMes
        fields = [
            "id", "usuario", "sede", "prestador", "anio", "mes", "dia_semana", "hora",
            "tipo_clase", "tipo_abono", "monto", "estado", "creado_en", "actualizado_en", "fecha_limite_renovacion"
        ]
        read_only_fields = ["estado", "creado_en", "actualizado_en", "fecha_limite_renovacion"]
        # 🔒 Evitamos que DRF genere UniqueTogetherValidator que ignora la condición del constraint:
        validators = []

    def validate(self, attrs):
        usuario = attrs["usuario"]
        sede = attrs["sede"]
        prestador = attrs["prestador"]
        tipo_clase = attrs["tipo_clase"]
        anio, mes = attrs["anio"], attrs["mes"]
        dia_semana, hora = attrs["dia_semana"], attrs["hora"]

        # 0) Unicidad condicional (estado="pagado")
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

        # 1) Validar que todo sea del mismo cliente
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

        # 2) tipo_clase debe ser de la sede seleccionada
        if tipo_clase.configuracion_sede.sede_id != sede.id:
            raise serializers.ValidationError({
                "tipo_clase": "El tipo de clase no pertenece a la sede seleccionada."
            })

        # 3) Validar existencia de todos los turnos requeridos (mes actual y próximo)
        fechas_actual = self._fechas_del_mes_por_dia_semana(anio, mes, dia_semana)
        if not fechas_actual:
            raise serializers.ValidationError("No hay fechas válidas en el mes para ese día de semana.")

        prox_anio, prox_mes = proximo_mes(anio, mes)
        fechas_prox = self._fechas_del_mes_por_dia_semana(prox_anio, prox_mes, dia_semana)

        def _chequear_mes(fechas, etiqueta):
            qs = Turno.objects.filter(
                fecha__in=fechas, hora=hora, lugar=sede,
                content_type__model="prestador", object_id=prestador.id
            ).only("id", "fecha", "estado")
            turnos_map = {t.fecha: t for t in qs}

            faltantes = [f for f in fechas if f not in turnos_map]
            if faltantes:
                raise serializers.ValidationError({
                    etiqueta: f"Faltan turnos generados para {len(faltantes)} fecha(s)."
                })

            reservados = [t for t in turnos_map.values() if t.estado == "reservado"]
            if reservados:
                raise serializers.ValidationError({
                    etiqueta: "Hay turnos ya reservados en la franja; no se puede crear el abono."
                })

        _chequear_mes(fechas_actual, "mes_actual")
        if fechas_prox:
            _chequear_mes(fechas_prox, "mes_siguiente")

        # tipo_abono debe pertenecer a la sede
        tipo_abono = attrs.get("tipo_abono")
        sede = attrs["sede"]
        if tipo_abono and tipo_abono.configuracion_sede.sede_id != sede.id:
            raise serializers.ValidationError({
                "tipo_abono": "El tipo de abono no pertenece a la sede seleccionada."
            })

        return attrs

    @staticmethod
    def _fechas_del_mes_por_dia_semana(anio: int, mes: int, dia_semana: int):
        from calendar import Calendar
        fechas = []
        for week in Calendar(firstweekday=0).monthdatescalendar(anio, mes):
            for d in week:
                if d.month == mes and d.weekday() == dia_semana:
                    fechas.append(d)
        return fechas
