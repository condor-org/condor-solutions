# apps/common/management/commands/bootstrap_condor.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
import logging, random, string

logger = logging.getLogger(__name__)
User = get_user_model()

def _alias_random(n=10): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))
def _cbu_random(): return ''.join(random.choices('0123456789', k=22))

class Command(BaseCommand):
    help = "Bootstrap Condor: usuarios base, cliente/sedes/config, tipos, prestador/disponibilidades y generación de turnos via cron real."

    def add_arguments(self, parser):
        parser.add_argument("--super-email", default="superadmin@sadmin.com")
        parser.add_argument("--super-pass", default="sadmin123")
        parser.add_argument("--cliente-nombre", default="Lucas Padel")
        parser.add_argument("--admin-email", default="admin@admin.com")
        parser.add_argument("--admin-pass", default="admin123")
        parser.add_argument("--prof-email", default="lucas@lucas.com")
        parser.add_argument("--prof-pass", default="lucas123")
        parser.add_argument("--user-email", default="nacho@nacho.com")
        parser.add_argument("--user-pass", default="nacho123")
        parser.add_argument("--skip-migrate", action="store_true", help="No ejecutar 'migrate' antes del bootstrap.")

    def handle(self, *args, **opts):
        # 0) Migraciones (fuera de transacciones)
        if not opts["skip_migrate"]:
            self.stdout.write(self.style.WARNING("[bootstrap] Ejecutando 'migrate'..."))
            call_command("migrate", interactive=False, verbosity=1)
            self.stdout.write(self.style.SUCCESS("[bootstrap] migrate OK"))

        # 1..7) Datos base
        with transaction.atomic():
            from apps.clientes_core.models import Cliente
            from apps.turnos_core.models import Lugar, Prestador, Disponibilidad
            from apps.turnos_padel.models import (
                ConfiguracionSedePadel, TipoClasePadel, TipoAbonoPadel
            )

            # ========= 1) SUPER ADMIN =========
            super_email = opts["super_email"]; super_pass = opts["super_pass"]
            if not User.objects.filter(email=super_email).exists():
                root = User.objects.create_superuser(
                    email=super_email, password=super_pass, username=super_email,
                    tipo_usuario="super_admin", cliente=None, nombre="Super", apellido="Admin",
                )
                logger.info("[bootstrap] SuperAdmin creado id=%s email=%s", root.id, super_email)
            else:
                logger.info("[bootstrap] SuperAdmin existente email=%s", super_email)

            # ========= 2) CLIENTE =========
            cliente, created_c = Cliente.objects.get_or_create(
                nombre=opts["cliente_nombre"],
                defaults={"tipo_cliente": "padel", "theme": "classic"},
            )
            logger.info("[bootstrap] Cliente %s (id=%s)", "creado" if created_c else "existente", cliente.id)

            # ========= 3) ADMIN DEL CLIENTE =========
            admin_email = opts["admin_email"]; admin_pass = opts["admin_pass"]
            admin = User.objects.filter(email=admin_email).first()
            if not admin:
                admin = User.objects.create_user(
                    email=admin_email, password=admin_pass, username=admin_email,
                    tipo_usuario="admin_cliente", cliente=cliente,
                    nombre="Admin", apellido="Cliente", is_staff=True,
                )
                logger.info("[bootstrap] AdminCliente creado id=%s email=%s cliente_id=%s", admin.id, admin.email, cliente.id)
            else:
                logger.info("[bootstrap] AdminCliente existente email=%s (cliente_id=%s)", admin.email, admin.cliente_id or "-")

            # ========= 4) SEDES + CONFIG PADEL + TIPOS =========
            precios_tipo_clase = {"x1": 20000, "x2": 30000, "x3": 40000, "x4": 50000}
            precios_tipo_abono = {"x1": 70000, "x2": 120000, "x3": 160000, "x4": 200000}

            def ensure_sede(nombre_sede: str):
                sede, created_s = Lugar.objects.get_or_create(
                    cliente=cliente, nombre=nombre_sede,
                    defaults={"direccion": "", "referente": "", "telefono": ""}
                )
                logger.info("[bootstrap] Sede %s: %s (id=%s)", nombre_sede, "creada" if created_s else "existente", sede.id)

                config, _ = ConfiguracionSedePadel.objects.get_or_create(
                    sede=sede, defaults={"alias": _alias_random(10), "cbu_cvu": _cbu_random()}
                )
                changed = False
                if not config.alias: config.alias = _alias_random(10); changed = True
                if not config.cbu_cvu: config.cbu_cvu = _cbu_random(); changed = True
                if changed: config.save(update_fields=["alias", "cbu_cvu"])
                logger.info("[bootstrap]   Config: alias=%s cbu=%s", config.alias, config.cbu_cvu)

                for codigo, precio in precios_tipo_clase.items():
                    obj, created_tc = TipoClasePadel.objects.get_or_create(
                        configuracion_sede=config, codigo=codigo, defaults={"precio": precio, "activo": True}
                    )
                    if not created_tc and obj.precio != precio:
                        obj.precio = precio; obj.save(update_fields=["precio"])
                    logger.info("[bootstrap]   TipoClase %s $%s (%s)", obj.get_codigo_display(), obj.precio, "creado" if created_tc else "existente")

                for codigo, precio in precios_tipo_abono.items():
                    obj, created_ta = TipoAbonoPadel.objects.get_or_create(
                        configuracion_sede=config, codigo=codigo, defaults={"precio": precio, "activo": True}
                    )
                    if not created_ta and obj.precio != precio:
                        obj.precio = precio; obj.save(update_fields=["precio"])
                    logger.info("[bootstrap]   TipoAbono %s $%s (%s)", obj.get_codigo_display(), obj.precio, "creado" if created_ta else "existente")
                return sede

            sede_belgrano = ensure_sede("Belgrano")
            sede_palermo  = ensure_sede("Palermo")

            # ========= 5) PROFESOR + PRESTADOR =========
            prof_email = opts["prof_email"]; prof_pass = opts["prof_pass"]
            prof_user = User.objects.filter(email=prof_email).first()
            if not prof_user:
                prof_user = User.objects.create_user(
                    email=prof_email, password=prof_pass, username=prof_email,
                    tipo_usuario="empleado_cliente", cliente=cliente,
                    nombre="Lucas", apellido="Profe", is_staff=False,
                )
                logger.info("[bootstrap] Usuario profesor creado id=%s email=%s", prof_user.id, prof_email)
            else:
                logger.info("[bootstrap] Usuario profesor existente email=%s", prof_email)

            from apps.turnos_core.models import Prestador
            prestador, created_p = Prestador.objects.get_or_create(
                user=prof_user, cliente=cliente,
                defaults={"especialidad": "Padel", "nombre_publico": "Lucas P.", "activo": True}
            )
            if not created_p:
                changed = False
                if not prestador.nombre_publico: prestador.nombre_publico = "Lucas P."; changed = True
                if not prestador.activo: prestador.activo = True; changed = True
                if changed: prestador.save(update_fields=["nombre_publico", "activo"])
            logger.info("[bootstrap] Prestador %s (id=%s)", "creado" if created_p else "existente", prestador.id)

            # ========= 6) DISPONIBILIDADES =========
            from apps.turnos_core.models import Disponibilidad
            bloques = [
                (sede_belgrano.id, 0, "09:00", "17:00"),
                (sede_belgrano.id, 2, "09:00", "17:00"),
                (sede_palermo.id,  1, "09:00", "17:00"),
                (sede_palermo.id,  3, "09:00", "17:00"),
            ]
            creadas = 0
            for lugar_id, dia_semana, h_ini, h_fin in bloques:
                _, created_d = Disponibilidad.objects.get_or_create(
                    prestador=prestador, lugar_id=lugar_id,
                    dia_semana=dia_semana, hora_inicio=h_ini, hora_fin=h_fin,
                    defaults={"activo": True}
                )
                if created_d: creadas += 1
            logger.info("[bootstrap] Disponibilidades creadas=%s (o ya existentes)", creadas)

            # ========= 7) USUARIO FINAL =========
            user_email = opts["user_email"]; user_pass  = opts["user_pass"]
            nacho = User.objects.filter(email=user_email).first()
            if not nacho:
                nacho = User.objects.create_user(
                    email=user_email, password=user_pass, username=user_email,
                    tipo_usuario="usuario_final", cliente=cliente,
                    nombre="Nacho", apellido="Cliente", is_staff=False,
                )
                logger.info("[bootstrap] Usuario final creado id=%s email=%s", nacho.id, user_email)
            else:
                logger.info("[bootstrap] Usuario final existente email=%s", user_email)

        # 8) Generación de turnos via cron real
        self.stdout.write(self.style.WARNING("[bootstrap] Ejecutando cron 'generar_turnos_mensuales'..."))
        call_command("generar_turnos_mensuales", verbosity=1)
        self.stdout.write(self.style.SUCCESS("[bootstrap] Cron ejecutado OK"))

        # 9) Resumen
        self.stdout.write(self.style.SUCCESS("Bootstrap Condor OK"))
        self.stdout.write(self.style.SUCCESS(f"SuperAdmin: {opts['super_email']} / {opts['super_pass']}"))
        self.stdout.write(self.style.SUCCESS(f"Admin:      {opts['admin_email']} / {opts['admin_pass']}"))
        self.stdout.write(self.style.SUCCESS(f"Profesor:   {opts['prof_email']} / {opts['prof_pass']}"))
        self.stdout.write(self.style.SUCCESS(f"Usuario:    {opts['user_email']} / {opts['user_pass']}"))
