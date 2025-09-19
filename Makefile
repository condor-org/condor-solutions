# ==== Makefile Condor ====
# Uso rápido:
#   make up                # levanta todo
#   make down              # baja todo
#   make reset-db          # BAJA STACK y BORRA volúmenes (DB + Redis)  << destructive
#   make clean-db          # barre el schema public en Postgres (sin borrar volúmenes)
#   make migrate           # aplica migraciones
#   make makemig           # genera migraciones
#   make plan              # muestra plan de migración
#   make bootstrap-condor  # corre el management command bootstrap_condor (con migrate + cron)
#   make init              # clean-db + bootstrap-condor
#   make reset-bootstrap   # reset-db + bootstrap-condor
#   make cron              # corre manualmente generar_turnos_mensuales
#   make logs              # tail logs backend
#   make psql              # abre psql dentro del contenedor db
#   make backend-shell     # shell dentro del contenedor backend
#   make rebuild           # rebuild de imágenes y levanta

DC := docker compose -p condor_local --env-file .env -f docker-compose-local.yml

.PHONY: up up-backend down reset-db clean-db wait-db makemig plan migrate bootstrap-condor bootstrap-condor-skip-migrate init reset-bootstrap cron logs psql backend-shell rebuild

up:
	$(DC) up -d

# levanta backend (y por dependencia, db/redis)
up-backend:
	$(DC) up -d backend

down:
	$(DC) down --remove-orphans

reset-db:
	$(DC) down -v --remove-orphans
	$(DC) up -d db redis

clean-db:
	$(DC) up -d db
	$(DC) exec db bash -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $$POSTGRES_USER; GRANT ALL ON SCHEMA public TO public;"'

# espera a que Postgres acepte conexiones
wait-db:
	@$(DC) exec db bash -lc '\
	for i in $$(seq 1 30); do \
	  pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" && exit 0; \
	  echo "[wait-db] Postgres no listo aún... intento $$i/30"; \
	  sleep 1; \
	done; \
	echo "[wait-db] Timeout esperando Postgres" >&2; exit 1'

makemig: up-backend wait-db
	$(DC) exec backend bash -lc "python manage.py makemigrations"

plan: up-backend wait-db
	$(DC) exec backend bash -lc "python manage.py migrate --plan"

migrate: up-backend wait-db
	$(DC) exec backend bash -lc "python manage.py migrate"

bootstrap-condor: up-backend wait-db
	$(DC) exec backend bash -lc 'python manage.py bootstrap_condor'

# Variante que saltea migrate (por si ya está aplicada)
bootstrap-condor-skip-migrate: up-backend wait-db
	$(DC) exec backend bash -lc 'python manage.py bootstrap_condor --skip-migrate \
	  --super-email "superadmin@sadmin.com" --super-pass "sadmin123" \
	  --admin-email "admin@admin.com"   --admin-pass "admin123" \
	  --prof-email "lucas@lucas.com"    --prof-pass "lucas123" \
	  --user-email "nacho@nacho.com"    --user-pass "nacho123"'

# setup de cero con schema limpio (sin borrar volúmenes)
init: clean-db bootstrap-condor

# setup de cero con volúmenes borrados
reset-bootstrap: reset-db bootstrap-condor
	@echo "✅ Base de datos reseteada, migraciones aplicadas y datos iniciales cargados"

# corre manualmente el cron real de generación de turnos
cron: up-backend wait-db
	$(DC) exec backend bash -lc "python manage.py generar_turnos_mensuales"

logs:
	$(DC) logs -f backend

psql:
	$(DC) exec db bash -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

backend-shell: up-backend
	$(DC) exec backend bash

rebuild:
	$(DC) build --no-cache
	$(DC) up -d


