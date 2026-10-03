# AGENTS.md

## Alcance actual

Este repositorio implementa únicamente acceso de lectura a la API REST de Canvas.
No agregar integraciones con Google Calendar, modelos de IA, agentes, PDFs,
anuncios ni extracción de fechas hasta que se solicite explícitamente.

## Convenciones

- Mantener el código sencillo, legible y con responsabilidades pequeñas.
- Leer secretos y configuración desde variables de entorno; nunca incluir
  credenciales reales en código, tests, documentación, logs o commits.
- Conservar `.env` fuera de Git y documentar variables nuevas en `.env.example`
  usando solo valores ficticios.
- Agregar tests sin credenciales reales para toda lógica nueva que sea aislable.
- Ejecutar `python -m unittest discover -s tests` antes de entregar cambios.
- Las consultas a Canvas deben ser de solo lectura salvo petición explícita.
