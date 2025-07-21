# 🦅 Cóndor – Documentación Técnica del Backend

Este backend gestiona turnos para profesores, administra comprobantes de pago, y permite la organización eficiente de turnos disponibles en distintas sedes deportivas. Está estructurado en dos apps principales:

- `turnos_core`: lógica base para turnos, lugares, y comprobantes
- `turnos_padel_core`: lógica específica del dominio de pádel, incluyendo profesores y disponibilidades

---

## 🧱 Estructura General

### 🔗 Relaciones principales

- `Profesor` trabaja en múltiples `Lugar`es (sedes) a través de `Disponibilidad`
- Cada `Disponibilidad` representa un rango horario semanal fijo para un profe
- A partir de estas disponibilidades se generan `Turno`s automáticos para un mes determinado
- Los `Turnos` pueden ser reservados por usuarios con un comprobante adjunto

---

## 📦 App: `turnos_core`

Contiene la lógica compartida entre distintos servicios y tipos de turnos.

### 🗂️ Modelos

#### 📍 `Lugar`
- Representa una sede física (ej: Palermo)
- Campos: `nombre`, `dirección`
- Usado en `Turno` y `Disponibilidad`

#### 🕒 `Turno`
- Representa un turno de atención disponible
- Campos: `fecha`, `hora`, `lugar`, `estado`, `usuario`, `servicio`, `object_id`, `content_type`
- Relación polimórfica con el recurso (ej: `Profesor`)

#### 📎 `Comprobante`
- Adjunta un archivo a un turno reservado
- Extrae y almacena datos del comprobante
- Campos: `archivo`, `fecha_carga`, `usuario`, `turno`, `datos_extraidos`, `estado`

---

## 📦 App: `turnos_padel_core`

Contiene la lógica específica del dominio de pádel.

### 🗂️ Modelos

#### 🎾 `Profesor`
- Recurso principal del sistema de turnos
- Campos: `nombre`, `email`, `activo`, etc.

#### 🗓️ `Disponibilidad`
- Franja horaria semanal recurrente para un profe
- Campos: `profesor`, `lugar`, `dia_semana`, `hora_inicio`, `hora_fin`, `activo`

---

## 🔁 Servicios

### 🔧 `generar_turnos_del_mes()`

Genera automáticamente los `Turno`s de un mes basándose en las `Disponibilidad`es activas.

```python
generar_turnos_del_mes(anio=2025, mes=7, duracion_minutos=60, profesor_id=3)



📑 Cómo comenzar
Configurar un superuser

Cargar sedes (Lugar) desde el admin

Crear profesores (Profesor)

Cargar disponibilidades semanales por sede

Generar turnos del mes desde el admin o via API

Permitir reservas con carga de comprobante