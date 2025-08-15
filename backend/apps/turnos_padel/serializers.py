# apps/turnos_padel/serializers.py
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from apps.turnos_padel.models import ConfiguracionSedePadel, TipoClasePadel
from apps.turnos_core.models import Lugar, Turno, Disponibilidad, BloqueoTurnos, Prestador
from rest_framework import serializers
from django.db.models import Q
from django.utils import timezone
from calendar import monthrange, Calendar
from apps.turnos_padel.models import AbonoMes, TipoClasePadel


class TipoClasePadelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # Permite crear sin ID
    class Meta:
        model = TipoClasePadel
        fields = ["id", "nombre", "precio"]

class ConfiguracionSedePadelSerializer(serializers.ModelSerializer):
    tipos_clase = TipoClasePadelSerializer(many=True)

    class Meta:
        model = ConfiguracionSedePadel
        fields = ["id", "alias", "cbu_cvu", "tipos_clase"]

    def update(self, instance, validated_data):
        tipos_data = validated_data.pop("tipos_clase", [])

        # Actualizar alias y CBU
        instance.alias = validated_data.get("alias", instance.alias)
        instance.cbu_cvu = validated_data.get("cbu_cvu", instance.cbu_cvu)
        instance.save()

        # IDs enviados desde frontend
        enviados_ids = [td.get("id") for td in tipos_data if td.get("id")]

        # Eliminar tipos que no están
        instance.tipos_clase.exclude(id__in=enviados_ids).delete()

        # Crear o actualizar tipos
        for tipo_data in tipos_data:
            tipo_id = tipo_data.get("id")
            if tipo_id:
                tipo = instance.tipos_clase.get(id=tipo_id)
                tipo.nombre = tipo_data.get("nombre", tipo.nombre)
                tipo.precio = tipo_data.get("precio", tipo.precio)
                tipo.save()
            else:
                TipoClasePadel.objects.create(configuracion_sede=instance, **tipo_data)

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

        user = self.context["request"].user
        if user.tipo_usuario == "super_admin":
            cliente = validated_data.pop("cliente", None)
            if not cliente:
                raise serializers.ValidationError("Debe especificar un cliente si es super_admin.")
        else:
            validated_data.pop("cliente", None)  # eliminamos si vino del request
            cliente = user.cliente

        sede = Lugar.objects.create(cliente=cliente, **validated_data)


        # Crear configuración
        config = ConfiguracionSedePadel.objects.create(
            sede=sede,
            alias=config_data.get("alias", ""),
            cbu_cvu=config_data.get("cbu_cvu", "")
        )

        # Crear tipos
        if tipos_data:
            for tipo in tipos_data:
                TipoClasePadel.objects.create(configuracion_sede=config, **tipo)
        else:
            for nombre in ["Individual", "2 Personas", "3 Personas", "4 Personas"]:
                TipoClasePadel.objects.create(configuracion_sede=config, nombre=nombre, precio=0)

        return sede

    def update(self, instance, validated_data):
        config_data = validated_data.pop("configuracion_padel", {})
        tipos_data = config_data.pop("tipos_clase", [])

        # Actualizar datos sede
        for field in ["nombre", "direccion", "referente", "telefono"]:
            setattr(instance, field, validated_data.get(field, getattr(instance, field)))
        instance.save()

        # Crear configuración si no existe
        config = getattr(instance, "configuracion_padel", None)
        if not config:
            config = ConfiguracionSedePadel.objects.create(sede=instance)

        # Actualizar configuración
        config.alias = config_data.get("alias", config.alias)
        config.cbu_cvu = config_data.get("cbu_cvu", config.cbu_cvu)
        config.save()

        # Sincronizar tipos
        enviados_ids = [t.get("id") for t in tipos_data if t.get("id")]
        config.tipos_clase.exclude(id__in=enviados_ids).delete()
        for tipo in tipos_data:
            if "id" in tipo:
                obj = config.tipos_clase.get(id=tipo["id"])
                obj.nombre = tipo.get("nombre", obj.nombre)
                obj.precio = tipo.get("precio", obj.precio)
                obj.save()
            else:
                TipoClasePadel.objects.create(configuracion_sede=config, **tipo)

        return instance

class AbonoMesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbonoMes
        fields = ["id","usuario","sede","prestador","anio","mes","dia_semana","hora","tipo_clase","monto","estado","creado_en","actualizado_en","fecha_limite_renovacion"]
        read_only_fields = ["estado","creado_en","actualizado_en","fecha_limite_renovacion"]

    def validate(self, attrs):
        usuario = attrs["usuario"]
        sede = attrs["sede"]
        prestador = attrs["prestador"]
        tipo_clase = attrs["tipo_clase"]
        anio, mes = attrs["anio"], attrs["mes"]
        dia_semana, hora = attrs["dia_semana"], attrs["hora"]

        # 1) mismo cliente
        if not all([
            getattr(usuario, "cliente_id", None) == sede.cliente_id == prestador.cliente_id ==
            tipo_clase.configuracion_sede.sede.cliente_id
        ]):
            raise serializers.ValidationError("Todos los elementos del abono deben pertenecer al mismo cliente.")

        # 2) tipo_clase de la misma sede
        if tipo_clase.configuracion_sede.sede_id != sede.id:
            raise serializers.ValidationError({"tipo_clase": "El tipo de clase no pertenece a la sede seleccionada."})

        # 3) validar franja completa (mes actual y siguiente): todos los días deben tener turno
        #    y ninguno puede estar 'reservado'.
        from apps.turnos_padel.services.abonos import _proximo_mes
        fechas_actual = self._fechas_del_mes_por_dia_semana(anio, mes, dia_semana)
        if not fechas_actual:
            raise serializers.ValidationError("No hay fechas válidas en el mes para ese día de semana.")

        prox_anio, prox_mes = _proximo_mes(anio, mes)
        fechas_prox = self._fechas_del_mes_por_dia_semana(prox_anio, prox_mes, dia_semana)

        def _chequear_mes(fechas, etiqueta):
            qs = Turno.objects.filter(
                fecha__in=fechas, hora=hora, lugar=sede,
                content_type__model="prestador", object_id=prestador.id
            ).only("id","fecha","estado")
            # mapear por fecha
            por_fecha = {t.fecha: t for t in qs}
            faltantes = [f for f in fechas if f not in por_fecha]
            if faltantes:
                raise serializers.ValidationError({etiqueta: f"Faltan turnos generados para {len(faltantes)} fecha(s)."})

            reservados = [t for t in por_fecha.values() if t.estado == "reservado"]
            if reservados:
                raise serializers.ValidationError({etiqueta: "Hay turnos ya reservados en la franja; no se puede crear el abono."})

            # si llegó acá, todas las fechas existen y están en disponible o cancelado
            return True

        _chequear_mes(fechas_actual, "mes_actual")
        if fechas_prox:
            _chequear_mes(fechas_prox, "mes_siguiente")

        return attrs

    @staticmethod
    def _fechas_del_mes_por_dia_semana(anio:int, mes:int, dia_semana:int):
        from calendar import Calendar
        fechas = []
        for week in Calendar(firstweekday=0).monthdatescalendar(anio, mes):
            for d in week:
                if d.month == mes and d.weekday() == dia_semana:
                    fechas.append(d)
        return fechas

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


    def get_turnos_reservados(self, obj):
        return [t.id for t in obj.turnos_reservados.all()]

    def get_turnos_prioridad(self, obj):
        return [t.id for t in obj.turnos_prioridad.all()]

    def get_tipo_turno_code(self, obj):
        nombre = (obj.tipo_clase.nombre or "").strip().lower()
        return {
            "individual": "individual",
            "2 personas": "x2",
            "3 personas": "x3",
            "4 personas": "x4"
        }.get(nombre, "")

