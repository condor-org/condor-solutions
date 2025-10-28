# apps/ethe_medica/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.turnos_core.models import Prestador, Disponibilidad
from apps.ethe_medica.models import (
    Medico, Paciente, ResultadoTest, Establecimiento, CentroAtencion, JerarquiaCentro,
    ProtocoloSeguimiento, SeguimientoPaciente
)
from apps.ethe_medica.services.flujo_pacientes import ingresar_paciente_c1
from apps.ethe_medica.services.asignacion_turnos import reservar_turno_paciente
from apps.ethe_medica.services.protocolos import programar_seguimientos_paciente

Usuario = get_user_model()


class MedicoSerializer(serializers.ModelSerializer):
    """Serializer para médicos ETHE"""
    user = serializers.SerializerMethodField()
    prestador = serializers.SerializerMethodField()
    disponibilidades = serializers.SerializerMethodField()
    estadisticas = serializers.SerializerMethodField()
    
    # Campos para crear médico
    email = serializers.EmailField(write_only=True)
    nombre = serializers.CharField(write_only=True)
    apellido = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    centro_atencion = serializers.IntegerField(write_only=True, help_text="ID del Centro de Atención")
    disponibilidades = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="Lista de disponibilidades para el médico (solo dia_semana, hora_inicio, hora_fin, activo)"
    )
    
    class Meta:
        model = Medico
        fields = [
            "id", "user", "prestador", "categorias", "matricula",
            "especialidad_medica", "activo", "disponibilidades", "estadisticas",
            # write_only
            "email", "nombre", "apellido", "password", "centro_atencion", "disponibilidades"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]
    
    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "email": obj.user.email,
            "nombre": obj.user.nombre,
            "apellido": obj.user.apellido,
            "telefono": obj.user.telefono
        }
    
    def get_prestador(self, obj):
        return {
            "id": obj.prestador.id,
            "especialidad": obj.prestador.especialidad,
            "nombre_publico": obj.prestador.nombre_publico,
            "activo": obj.prestador.activo
        }
    
    def get_disponibilidades(self, obj):
        disponibilidades = obj.prestador.disponibilidades.filter(activo=True)
        return DisponibilidadSerializer(disponibilidades, many=True).data
    
    def get_estadisticas(self, obj):
        """Calcular estadísticas de productividad del médico"""
        from apps.turnos_core.models import Turno
        
        estadisticas = {}
        
        # Estadísticas por categoría
        if "C1" in obj.categorias:
            # C1: Pacientes ingresados
            pacientes_ingresados = Paciente.objects.filter(
                medico_ingreso=obj
            ).count()
            estadisticas["pacientes_ingresados"] = pacientes_ingresados
        
        if "C2" in obj.categorias:
            # C2: FIBROSCAN realizados
            fibroscan_realizados = ResultadoTest.objects.filter(
                medico=obj,
                tipo_test="FIBROSCAN"
            ).count()
            estadisticas["fibroscan_realizados"] = fibroscan_realizados
        
        if "C3" in obj.categorias:
            # C3: Consultas realizadas (turnos con asistio=True)
            consultas_realizadas = Turno.objects.filter(
                recurso=obj.prestador,
                asistio=True
            ).count()
            estadisticas["consultas_realizadas"] = consultas_realizadas
        
        return estadisticas
    
    def validate_categorias(self, value):
        """Validar que se proporcione al menos una categoría"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("El médico debe tener al menos una categoría (C1, C2, C3)")
        
        categorias_validas = ["C1", "C2", "C3"]
        for categoria in value:
            if categoria not in categorias_validas:
                raise serializers.ValidationError(f"Categoría '{categoria}' no es válida. Debe ser: C1, C2, C3")
        
        return value
    
    def validate(self, attrs):
        """Validar que médicos C2 y C3 tengan disponibilidades"""
        categorias = attrs.get('categorias', [])
        disponibilidades = attrs.get('disponibilidades', [])
        
        # Médicos C2 y C3 deben tener disponibilidades
        if ("C2" in categorias or "C3" in categorias) and not disponibilidades:
            raise serializers.ValidationError(
                "Los médicos C2 y C3 deben tener disponibilidades asignadas"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Crear médico con usuario y prestador"""
        from django.db import transaction
        
        with transaction.atomic():
            # 1. Crear Usuario
            user_data = {
                "email": validated_data["email"],
                "nombre": validated_data["nombre"],
                "apellido": validated_data["apellido"],
                "telefono": "",
                "tipo_usuario": "medico_m1",  # Default, se actualizará según categorías
                "cliente": self.context["request"].user.cliente
            }
            
            user = Usuario.objects.create_user(
                username=validated_data["email"],  # Usar email como username
                password=validated_data["password"],
                **user_data
            )
            
            # 2. Crear Prestador
            prestador = Prestador.objects.create(
                user=user,
                cliente=user.cliente,
                especialidad=validated_data.get("especialidad_medica", ""),
                nombre_publico=f"{user.nombre} {user.apellido}"
            )
            
            # 3. Crear Medico
            medico = Medico.objects.create(
                user=user,
                prestador=prestador,
                categorias=validated_data["categorias"],
                matricula=validated_data["matricula"],
                especialidad_medica=validated_data.get("especialidad_medica", "")
            )
            
            # 4. Crear disponibilidades si se proporcionaron
            disponibilidades_data = validated_data.pop('disponibilidades', [])
            centro_atencion_id = validated_data.pop('centro_atencion')
            
            if disponibilidades_data:
                from apps.turnos_core.models import Disponibilidad
                from apps.ethe_medica.models import CentroAtencion
                
                # Obtener el Centro de Atención específico
                try:
                    centro = CentroAtencion.objects.get(id=centro_atencion_id)
                except CentroAtencion.DoesNotExist:
                    raise serializers.ValidationError(
                        f"No se encontró el Centro de Atención con ID: {centro_atencion_id}"
                    )
                
                # Usar el lugar del Centro de Atención
                lugar_centro = centro.lugar
                
                for disp_data in disponibilidades_data:
                    Disponibilidad.objects.create(
                        prestador=prestador,
                        lugar=lugar_centro,
                        dia_semana=disp_data['dia_semana'],
                        hora_inicio=disp_data['hora_inicio'],
                        hora_fin=disp_data['hora_fin'],
                        activo=disp_data.get('activo', True)
                    )
            
            return medico


class PacienteSerializer(serializers.ModelSerializer):
    """Serializer para pacientes ETHE"""
    user = serializers.SerializerMethodField()
    centro_ingreso_nombre = serializers.CharField(source="centro_ingreso.nombre", read_only=True)
    medico_ingreso_nombre = serializers.CharField(source="medico_ingreso.user.get_full_name", read_only=True)
    
    class Meta:
        model = Paciente
        fields = [
            "id", "user", "categoria_actual", "documento", "centro_ingreso",
            "centro_ingreso_nombre", "medico_ingreso", "medico_ingreso_nombre",
            "domicilio_calle", "domicilio_ciudad", "domicilio_provincia",
            "domicilio_codigo_postal", "telefono_contacto", "email_seguimiento",
            "fecha_nacimiento", "obra_social", "activo", "fecha_ingreso",
            "historial_categorias", "creado_en", "actualizado_en"
        ]
        read_only_fields = ["id", "fecha_ingreso", "creado_en", "actualizado_en"]
    
    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "email": obj.user.email,
            "nombre": obj.user.nombre,
            "apellido": obj.user.apellido,
            "telefono": obj.user.telefono
        }


class IngresarPacienteSerializer(serializers.Serializer):
    """Serializer para ingresar paciente desde centro C1"""
    # Datos del paciente
    documento = serializers.CharField()
    nombre = serializers.CharField()
    apellido = serializers.CharField()
    email = serializers.EmailField()
    telefono = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    domicilio_calle = serializers.CharField()
    domicilio_ciudad = serializers.CharField()
    domicilio_provincia = serializers.CharField()
    domicilio_codigo_postal = serializers.CharField(required=False, allow_blank=True)
    obra_social = serializers.CharField(required=False, allow_blank=True)
    
    # Resultados de tests (ambos obligatorios)
    resultado_pocus = serializers.ChoiceField(choices=["NORMAL", "HG"])
    resultado_fib4 = serializers.ChoiceField(choices=["NR", "R"])
    
    def create(self, validated_data):
        """Crear paciente usando servicio de flujo"""
        medico = self.context["request"].user.medico_ethe
        centro = self.context["request"].user.cliente.lugares.first()  # TODO: Mejorar lógica
        
        # Separar datos del paciente de los resultados
        datos_paciente = {k: v for k, v in validated_data.items() 
                         if k not in ["resultado_pocus", "resultado_fib4"]}
        
        resultado = ingresar_paciente_c1(
            datos_paciente=datos_paciente,
            resultado_pocus=validated_data["resultado_pocus"],
            resultado_fib4=validated_data["resultado_fib4"],
            medico=medico,
            centro=centro
        )
        
        return resultado


class ResultadoTestSerializer(serializers.ModelSerializer):
    """Serializer para resultados de tests"""
    paciente_nombre = serializers.CharField(source="paciente.user.get_full_name", read_only=True)
    centro_nombre = serializers.CharField(source="centro.nombre", read_only=True)
    medico_nombre = serializers.CharField(source="medico.user.get_full_name", read_only=True)
    
    class Meta:
        model = ResultadoTest
        fields = [
            "id", "paciente", "paciente_nombre", "tipo_test", "resultado",
            "valor_numerico", "fecha_realizacion", "centro", "centro_nombre",
            "medico", "medico_nombre", "turno", "observaciones", "creado_en"
        ]
        read_only_fields = ["id", "creado_en"]
    
    def create(self, validated_data):
        """Crear resultado de test y actualizar categoría del paciente si es necesario"""
        from apps.ethe_medica.services.flujo_pacientes import procesar_resultado_fibroscan
        
        resultado = super().create(validated_data)
        
        # Si es FIBROSCAN, procesar cambio de categoría
        if resultado.tipo_test == "FIBROSCAN":
            procesar_resultado_fibroscan(
                paciente=resultado.paciente,
                resultado=resultado.resultado,
                medico=resultado.medico,
                centro=resultado.centro,
                turno=resultado.turno
            )
        
        return resultado


class EstablecimientoSerializer(serializers.ModelSerializer):
    """Serializer para establecimientos"""
    admin_nombre = serializers.CharField(source="admin_establecimiento.get_full_name", read_only=True)
    centros_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Establecimiento
        fields = [
            "id", "nombre", "direccion", "telefono", "email",
            "admin_establecimiento", "admin_nombre", "activo",
            "centros_count", "creado_en", "actualizado_en"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]
    
    def get_centros_count(self, obj):
        return obj.centros_ethe.filter(activo=True).count()


class CentroAtencionSerializer(serializers.ModelSerializer):
    """Serializer para centros de atención"""
    establecimiento_nombre = serializers.CharField(source="establecimiento.nombre", read_only=True)
    lugar_nombre = serializers.CharField(source="lugar.nombre", read_only=True)
    medicos_count = serializers.SerializerMethodField()
    
    # Campos write_only para crear el lugar automáticamente
    lugar_nombre_input = serializers.CharField(write_only=True, required=True, help_text="Nombre del lugar")
    lugar_direccion = serializers.CharField(write_only=True, required=False, allow_blank=True, help_text="Dirección del lugar")
    lugar_telefono = serializers.CharField(write_only=True, required=False, allow_blank=True, help_text="Teléfono del lugar")
    lugar_referente = serializers.CharField(write_only=True, required=False, allow_blank=True, help_text="Referente del lugar")
    
    class Meta:
        model = CentroAtencion
        fields = [
            "id", "establecimiento", "establecimiento_nombre", "lugar_nombre", "medicos_count",
            "categorias", "nombre_centro", "activo", "creado_en", "actualizado_en",
            # write_only
            "lugar_nombre_input", "lugar_direccion", "lugar_telefono", "lugar_referente"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]
    
    def create(self, validated_data):
        """Crea el lugar automáticamente y luego el centro"""
        from apps.turnos_core.models import Lugar
        
        # Extraer datos del lugar
        lugar_nombre = validated_data.pop('lugar_nombre_input')
        lugar_direccion = validated_data.pop('lugar_direccion', '')
        lugar_telefono = validated_data.pop('lugar_telefono', '')
        lugar_referente = validated_data.pop('lugar_referente', '')
        
        # Obtener cliente del usuario autenticado
        request = self.context.get('request')
        cliente = request.user.cliente
        
        # Crear Lugar
        lugar = Lugar.objects.create(
            cliente=cliente,
            nombre=lugar_nombre,
            direccion=lugar_direccion,
            telefono=lugar_telefono,
            referente=lugar_referente
        )
        
        # Crear CentroAtencion con el lugar
        centro = CentroAtencion.objects.create(
            lugar=lugar,
            **validated_data
        )
        
        return centro
    
    def get_medicos_count(self, obj):
        # Simplificar para evitar errores
        try:
            return Medico.objects.filter(activo=True).count()
        except:
            return 0


class JerarquiaCentroSerializer(serializers.ModelSerializer):
    """Serializer para jerarquías de centros"""
    centro_origen_nombre = serializers.CharField(source="centro_origen.nombre_centro", read_only=True)
    centro_destino_nombre = serializers.CharField(source="centro_destino.nombre_centro", read_only=True)
    establecimiento_origen = serializers.CharField(source="centro_origen.establecimiento.nombre", read_only=True)
    establecimiento_destino = serializers.CharField(source="centro_destino.establecimiento.nombre", read_only=True)
    
    class Meta:
        model = JerarquiaCentro
        fields = [
            "id", "centro_origen", "centro_origen_nombre", "establecimiento_origen",
            "centro_destino", "centro_destino_nombre", "establecimiento_destino",
            "categoria_origen", "categoria_destino", "activo", "prioridad",
            "distancia_km", "creado_en", "actualizado_en"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class ProtocoloSeguimientoSerializer(serializers.ModelSerializer):
    """Serializer para protocolos de seguimiento"""
    class Meta:
        model = ProtocoloSeguimiento
        fields = [
            "id", "categoria_paciente", "nombre", "descripcion",
            "frecuencia_dias", "configuracion", "activo", "creado_en", "actualizado_en"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class SeguimientoPacienteSerializer(serializers.ModelSerializer):
    """Serializer para seguimientos de pacientes"""
    paciente_nombre = serializers.CharField(source="paciente.user.get_full_name", read_only=True)
    protocolo_nombre = serializers.CharField(source="protocolo.nombre", read_only=True)
    
    class Meta:
        model = SeguimientoPaciente
        fields = [
            "id", "paciente", "paciente_nombre", "protocolo", "protocolo_nombre",
            "fecha_programada", "fecha_realizada", "estado", "observaciones",
            "creado_en", "actualizado_en"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class DisponibilidadSerializer(serializers.ModelSerializer):
    """Serializer para disponibilidades (reutilizado de turnos_core)"""
    lugar_nombre = serializers.CharField(source="lugar.nombre", read_only=True)
    dia_semana_display = serializers.CharField(source="get_dia_semana_display", read_only=True)
    
    class Meta:
        model = Disponibilidad
        fields = [
            "id", "lugar", "lugar_nombre", "dia_semana", "dia_semana_display",
            "hora_inicio", "hora_fin", "activo", "creado_en", "actualizado_en"
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class ReservarTurnoSerializer(serializers.Serializer):
    """Serializer para reservar turno de paciente"""
    turno_id = serializers.IntegerField()
    paciente_id = serializers.IntegerField()
    
    def create(self, validated_data):
        """Reservar turno usando servicio"""
        medico = self.context["request"].user.medico_ethe
        paciente = Paciente.objects.get(id=validated_data["paciente_id"])
        
        turno = reservar_turno_paciente(
            paciente=paciente,
            turno_id=validated_data["turno_id"],
            medico_reservador=medico
        )
        
        return turno


class EstadisticasSerializer(serializers.Serializer):
    """Serializer para estadísticas del dashboard"""
    total_pacientes = serializers.IntegerField()
    pacientes_por_categoria = serializers.DictField()
    tests_realizados_mes = serializers.DictField()
    centros_activos = serializers.IntegerField()
    medicos_activos = serializers.IntegerField()
    seguimientos_pendientes = serializers.IntegerField()
    tasa_asistencia = serializers.FloatField()
