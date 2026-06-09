# condor-solutions — Sitio web institucional

**Qué es:** la landing pública y estática de Condor-Solutions.

**Para qué existe:** es el **sitio web oficial del negocio** exigido por Meta para la
**verificación de Business Account** (habilitar WhatsApp Business API). Expone de forma
visible y accesible los datos legales del negocio (nombre, dirección, teléfono, web HTTPS)
junto con una presentación de servicios y un formulario de contacto.

> ⚠️ **No es parte del stack desplegado en la VM Oracle.** Este repo vive junto al resto del
> ecosistema CONDOR (`condor-infra`, `condor-app-configs`, `ethe`, `padel`) solo por orden.
> A diferencia de ellos, **no usa Traefik, ni Doppler, ni `cnd-ia.com`**: es un sitio estático
> servido por **GitHub Pages**. Independiente y sin backend.

- **URL:** https://condor-solutions.github.io/condor-solutions/
- **Stack:** HTML5 + CSS3 + JavaScript vanilla. Sin build, sin dependencias, sin Node.

## Estructura

```
index.html    # Página única (hero, info legal, servicios, sobre nosotros, contacto)
styles.css    # Estilos
script.js     # Interacciones del lado del cliente (nav, formulario)
.nojekyll     # Desactiva el procesamiento Jekyll de GitHub Pages
```

`DOCUMENTOS_ARGENTINA_META.md` — guía de los documentos necesarios para la verificación de
negocio de Meta en Argentina.

## Datos del negocio (los que ve Meta)

| Campo | Valor |
|---|---|
| Razón social | Luque Ignacio Javier |
| CUIT | 20-36357044-6 |
| Nombre comercial | Condor Solutions |
| Dirección | Mendoza 1925, Piso 9, CABA (1428), Argentina |
| Teléfono | +54 9 11 6051-3033 |
| Email | contacto@cnd-ia.com |
| Sitio web | https://cnd-ia.com |

Mantener estos datos **idénticos** a los cargados en Meta Business Manager: cualquier
discrepancia hace fallar la verificación.

## Desarrollo local

No requiere build. Abrir `index.html` en el navegador, o servirlo con cualquier servidor
estático (`python3 -m http.server`).

## Despliegue (GitHub Pages)

No hay workflows: GitHub Pages sirve los archivos estáticos directamente.

1. **Settings → Pages**
2. **Source:** Branch `master`, carpeta `/ (root)`
3. **Save** — el sitio queda online en pocos minutos.

Cada push a la rama configurada actualiza el sitio automáticamente.
</content>
</invoke>
