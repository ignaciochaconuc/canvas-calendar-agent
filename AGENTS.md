# AGENTS.md

## Alcance actual

Este repositorio implementa exploración de lectura de la API REST de Canvas y un
pipeline determinístico que convierte fechas estructuradas de assignments y calendar
events a `AcademicEvent`. El texto sin fecha estructurada se conserva como
`EventCandidate`. No agregar Google Calendar, modelos de IA, agentes, descarga o
lectura de PDFs ni interpretación automática de texto hasta petición explícita.

## Convenciones

- Mantener el código sencillo, legible y con responsabilidades pequeñas.
- Leer secretos y configuración desde variables de entorno; nunca incluir
  credenciales reales en código, tests, documentación, logs o commits.
- Conservar `.env` fuera de Git y documentar variables nuevas en `.env.example`
  usando solo valores ficticios.
- Agregar tests sin credenciales reales para toda lógica nueva que sea aislable.
- Ejecutar `python -m unittest discover -s tests` antes de entregar cambios.
- Las consultas a Canvas deben ser de solo lectura salvo petición explícita.
- No asumir que `enrollment_state=active` identifica el semestre académico actual;
  conservar y mostrar la información del periodo de Canvas.
- Reutilizar la paginación común y validar que sus enlaces permanezcan en el mismo
  origen antes de enviar el token.
- No descargar archivos: consultar únicamente sus metadatos en esta etapa.
- Normalizar timestamps con zona mediante `zoneinfo` a `America/Santiago`; nunca
  eliminar offsets ni asumir silenciosamente una zona para timestamps ingenuos.
- Deduplicar eventos solo por identidad explícita (`source_type`, `source_id`), no
  mediante similitud semántica.
- `config.json` puede contener selección local de IDs de cursos, pero jamás secretos.
