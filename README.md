# canvas-calendar-agent

Explorador y pipeline de solo lectura para normalizar información académica de
Canvas UC antes de construir futuras integraciones.

Permite consultar fuentes de Canvas, transformar fechas explícitas en
`AcademicEvent` e interpretar manualmente un `EventCandidate` mediante un agente.
Puede descargar manualmente PDFs prefiltrados para extraer texto localmente. No
integra Google Calendar ni procesa archivos masivamente.

## Requisitos e instalación

- Python 3.10 o superior
- Un token de acceso personal de Canvas
- Ollama, solo si se usará el proveedor local

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
MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:8b
MAX_FILE_SIZE_MB=20
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

## Explorar documentos PDF

`python main.py files` lista solamente PDFs y XLSX cuyo nombre parece corresponder a un
programa, calendario, cronograma, proyecto o planificación en los cursos configurados. El
usuario elige cuáles descargar. Se guardan en `.cache/canvas_files/`, se extrae el
texto por página con PyMuPDF y se generan candidatos solo para bloques que combinan
vocabulario de eventos con meses o patrones de fecha. PDFs escaneados sin capa de
texto se reportan sin candidatos; no hay OCR.

`python main.py files --agent` añade una segunda selección manual y envía exactamente
un candidato al agente configurado. Nunca envía el documento completo automáticamente.

Los XLSX se leen localmente con `openpyxl` en modo `data_only=True`: no se ejecutan
fórmulas ni macros y solo se crean bloques de hojas/filas con fechas o vocabulario
académico. Las descargas aceptan solo PDF/XLSX, aplican `MAX_FILE_SIZE_MB` y no reenvían
el token de Canvas a hosts externos durante redirecciones.

El agente devuelve `CandidateAnalysis.events`, por lo que un bloque puede producir cero,
uno o varios eventos. Día, mes y año son campos separados; el agente debe dejar el año
nulo si no aparece en el texto. Después, código determinístico puede completarlo solo
cuando nombre, código o periodo del curso contienen un único año explícito.
Una barrera posterior al modelo elimina cualquier año que no aparezca literalmente en
el bloque, incluso si el modelo incumple la instrucción.

## Agente experimental

El modo `agent` permite elegir manualmente uno de los primeros diez
`EventCandidate` de los cursos configurados y realizar una única interpretación:

```powershell
python main.py agent
```

El agente usa el OpenAI Agents SDK y devuelve un `ExtractedAcademicEvent` validado
por Pydantic. El backend puede ser Ollama local u OpenAI sin duplicar la definición
del agente. Recibe únicamente:

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
- `agent/model_provider.py`: construye el modelo y valida su disponibilidad.

### Ollama local

Instala Ollama desde su instalador para Windows y confirma que el comando esté
disponible. Después descarga el modelo configurado:

```powershell
ollama pull qwen3:8b
```

La aplicación espera el endpoint OpenAI-compatible local:

```text
http://localhost:11434/v1
```

Normalmente la aplicación de Ollama inicia el servicio. Si no está activo, puedes
iniciarlo manualmente:

```powershell
ollama serve
```

Comprueba el modelo y el endpoint antes de ejecutar el agente:

```powershell
ollama list
Invoke-RestMethod http://localhost:11434/v1/models
python main.py agent
```

`ollama run qwen3:8b` permite además comprobar el modelo de forma interactiva, pero
no necesita permanecer abierto si el servicio ya está ejecutándose. Ollama no exige
`OPENAI_API_KEY`; internamente se usa el valor público ficticio `ollama` requerido
por el cliente compatible. El tracing hacia OpenAI queda desactivado.

### Cambiar a OpenAI

Configura estas variables en `.env`:

```dotenv
MODEL_PROVIDER=openai
OPENAI_MODEL=tu_modelo
OPENAI_API_KEY=tu_api_key
```

Solo la capa `model_provider.py` conoce la diferencia entre proveedores. El Agent,
las instrucciones, el Runner y el schema son los mismos. Los tests mockean modelos
y Runner; nunca ejecutan inferencia real ni consumen API.

## Tests

Los tests usan respuestas simuladas y no necesitan credenciales ni red:

```powershell
python -m unittest discover -s tests
```

## Seguridad y alcance

- El token se lee exclusivamente desde `CANVAS_TOKEN`.
- Solo se realizan solicitudes HTTP `GET`.
- La paginación rechaza enlaces hacia otro origen para no filtrar el token.
- Solo se descargan PDFs relevantes seleccionados explícitamente, a una caché ignorada.
- El agente experimental solo interpreta un candidato elegido manualmente.
- No hay integración con calendarios ni acciones externas.
