# AGENTS.md

## Alcance actual

Este repositorio implementa únicamente exploración de lectura de la API REST de
Canvas: cursos, tareas, módulos e items, páginas, metadatos de archivos, eventos,
anuncios y syllabus. No agregar integraciones con Google Calendar, modelos de IA,
agentes, descarga o lectura de PDFs ni extracción automática de fechas hasta que se
solicite explícitamente.

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
