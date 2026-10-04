# AGENTS.md

## Alcance actual

Este repositorio implementa exploración de lectura de Canvas, un pipeline
determinístico y un agente experimental que interpreta manualmente un único
`EventCandidate` con salida Pydantic. El agente no tiene tools ni acceso directo a
Canvas. El backend puede ser Ollama local u OpenAI mediante una capa desacoplada.
Incluye descarga manual y extracción local de PDFs y XLSX relevantes. No agregar Google
Calendar, OCR, tools, handoffs, memoria/sessions ni procesamiento automático masivo
hasta petición explícita.

## Convenciones

`sync-all` interactivo debe mostrar y persistir conflictos sin resolverlos
automáticamente. `sync-all --non-interactive` nunca solicita input, omite conflictos y
termina sin error para poder ejecutarse desde Windows Task Scheduler.

`sync-all` y `calendar-sync --auto` pueden escribir sin confirmación únicamente eventos
con fecha completa que satisfacen la política conservadora. Assignments y calendar
events explícitos son seguros; fuentes del agente requieren confianza configurable
(0.9 por defecto), fecha completa y ausencia de conflicto. Mantener calendarios e
idempotencia separados por semestre y usar solo popup a 10080/1440 minutos, sin email.

La escritura en Google Calendar se realiza solo mediante código Python después de
revisión y confirmación explícita. El agente permanece sin tools ni acceso a Google.
OAuth, revisión, configuración del calendario y registro de sincronización son archivos
locales ignorados por Git. No actualizar automáticamente eventos ya sincronizados.

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
- Descargar solo PDFs/XLSX elegidos explícitamente, con límite de tamaño, caché ignorada,
  validación MIME y sin reenviar autenticación a orígenes externos.
- Normalizar timestamps con zona mediante `zoneinfo` a `America/Santiago`; nunca
  eliminar offsets ni asumir silenciosamente una zona para timestamps ingenuos.
- Deduplicar eventos solo por identidad explícita (`source_type`, `source_id`), no
  mediante similitud semántica.
- `config.json` puede contener selección local de IDs de cursos, pero jamás secretos.
- Leer la clave de OpenAI exclusivamente desde `OPENAI_API_KEY`; nunca incluirla en
  prompts, logs, tests, documentación o commits.
- El modelo solo debe recibir nombre del curso, tipo de fuente, título, texto y fecha
  de publicación del candidato. No pasar tokens, objetos cliente, IDs o URLs.
- Descartar cualquier año del modelo que no aparezca explícitamente en el texto; los
  años faltantes se resuelven después mediante metadata inequívoca del curso.
- Los tests del agente deben mockear el Runner y no pueden usar la API real.
- Mantener `tools=[]` hasta que se solicite explícitamente una primera tool.
- Mantener toda dependencia y configuración específica de Ollama/OpenAI dentro de
  `agent/model_provider.py`; el resto del agente no debe conocer el proveedor.
- Ollama usa `OLLAMA_BASE_URL`, `OLLAMA_MODEL` y la clave ficticia pública `ollama`;
  no debe requerir `OPENAI_API_KEY` y debe desactivar tracing hacia OpenAI.
- OpenAI usa `OPENAI_MODEL` y exige `OPENAI_API_KEY` exclusivamente desde el entorno.
