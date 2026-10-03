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
- No hay integración con calendarios, IA, agentes ni interpretación de texto libre.
