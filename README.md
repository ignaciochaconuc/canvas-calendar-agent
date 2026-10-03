# canvas-calendar-agent

Explorador y pipeline de solo lectura para normalizar información académica de
Canvas UC antes de construir futuras integraciones.

Esta etapa permite elegir un curso y consultar tareas, módulos, páginas, archivos,
eventos de calendario, anuncios y syllabus. No descarga archivos ni integra Google
Calendar, OpenAI o agentes. Las fechas explícitas se transforman localmente en
`AcademicEvent`; el texto pendiente queda como `EventCandidate`.

## Requisitos e instalación

- Python 3.10 o superior
- Un token de acceso personal de Canvas

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura `.env` con la raíz de la misma instancia donde generaste el token:

```dotenv
CANVAS_BASE_URL=https://cursos.canvas.uc.cl
CANVAS_TOKEN=tu_token_personal
OPENAI_API_KEY=tu_api_key_de_openai
```

`.env` está ignorado por Git. No compartas ni confirmes ese archivo.

## Explorar un curso

```powershell
python main.py
```

La CLI lista los cursos cuya **matrícula** figura como activa. Esto no significa
necesariamente que sean cursos del semestre actual. Cada fila muestra ID, nombre,
código, `enrollment_term_id`, estado y publicación cuando Canvas la informa.

Después de elegir un curso por número se consultan y resumen:

- assignments, con descripción, fechas, tipos de entrega y URL en los datos crudos;
- módulos y sus items (páginas, archivos, tareas, quizzes, enlaces y otros tipos);
- metadatos de páginas y archivos, sin descargar contenido;
- eventos de calendario;
- anuncios;
- detalles del curso y cuerpo HTML del syllabus, si existe.

La muestra impresa contiene como máximo tres títulos por categoría. Si Canvas no
autoriza una fuente, la CLI la marca como no disponible y continúa con las demás.

## Pipeline de eventos

La primera ejecución permite elegir varios cursos y guarda únicamente sus IDs en
`config.json`:

```powershell
python main.py pipeline
```

Para reemplazar posteriormente esa selección:

```powershell
python main.py pipeline --select-courses
```

`config.json` es local y está ignorado por Git. Su formato está documentado en
`config.example.json`; nunca contiene tokens.

El flujo actual es:

```text
Canvas (solo GET)
  -> assignments con due_at + calendar events con start_at
  -> AcademicEvent normalizado en America/Santiago
  -> deduplicación por source_type + source_id

Canvas (texto sin fecha estructurada)
  -> anuncios + syllabus + páginas con body + assignments sin due_at
  -> EventCandidate pendiente de interpretación
```

Las fechas ISO 8601 conservan su instante y se convierten mediante `zoneinfo` a
`America/Santiago`. No se aceptan timestamps sin zona horaria. No hay clasificación
por IA: las tareas se marcan como `assignment` y los eventos genéricos de calendario
como `other` hasta una etapa posterior.

## Agente experimental

El modo `agent` permite elegir manualmente uno de los primeros diez
`EventCandidate` de los cursos configurados y realizar una única interpretación:

```powershell
python main.py agent
```

El agente usa el OpenAI Agents SDK y devuelve un `ExtractedAcademicEvent` validado
por Pydantic. Recibe únicamente:

- nombre del curso;
- tipo de fuente;
- título y texto del candidato;
- fecha de publicación, si existe.

No recibe el token de Canvas, IDs internos, URLs, archivos ni el cliente de Canvas.
No tiene tools, handoffs, memoria o acceso directo a sistemas externos. Por tanto,
solo puede interpretar el texto seleccionado: no puede consultar Canvas, modificar
datos, descargar PDFs ni escribir en Google Calendar.

Componentes educativos del agente:

- `agent/academic_agent.py`: define el `Agent` y ejecuta `Runner.run_sync`;
- `agent/instructions.py`: contiene sus instrucciones;
- `agent/schemas.py`: define el `output_type` Pydantic.

La clave se lee exclusivamente desde `OPENAI_API_KEY` en `.env`. Los tests mockean
el Runner y nunca realizan llamadas reales ni consumen API.

## Tests

Los tests usan respuestas simuladas y no necesitan credenciales ni red:

```powershell
python -m unittest discover -s tests
```

## Seguridad y alcance

- El token se lee exclusivamente desde `CANVAS_TOKEN`.
- Solo se realizan solicitudes HTTP `GET`.
- La paginación rechaza enlaces hacia otro origen para no filtrar el token.
- Los archivos se enumeran como metadatos; nunca se descargan.
- El agente experimental solo interpreta un candidato elegido manualmente.
- No hay integración con calendarios ni acciones externas.
