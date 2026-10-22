# Analizador de Poesía

Aplicación web para docentes de nivel secundario: se pega un poema en español y devuelve un análisis estructurado en cinco secciones.

| Sección | Qué incluye | Cómo se calcula |
| --- | --- | --- |
| **A. Métrica** | Silabeo por verso, licencias (sinalefa, sinéresis, diéresis, hiato), ley del acento final, cómputo silábico, nombre del verso y arte (menor o mayor). Si el silabeo es ambiguo, muestra las lecturas alternativas. | Motor propio basado en reglas (determinista) |
| **B. Versificación** | Rima (consonante, asonante o libre) y esquema; tipo de cada estrofa; tipo de composición con una justificación breve. | Motor propio basado en reglas (determinista) |
| **C. Recursos poéticos** | Recursos fónicos, semánticos, léxicos, gramaticales y sintácticos, con el verso citado, su número y el efecto expresivo. | API de Anthropic, con respuesta JSON validada |
| **D. Temas centrales** | Un tema principal y de dos a cuatro subtemas. | API de Anthropic |
| **E. Interpretación** | Posibles líneas de lectura en 50 palabras como máximo (la app cuenta y recorta). | API de Anthropic |

Cada resultado dudoso lleva un nivel de confianza (alta, media o baja). La terminología sigue la tradición métrica hispánica (Quilis, Navarro Tomás).

## Estructura

```
backend/
  app/              API FastAPI (sirve también el frontend)
  metrica/          motor de escansión, sin dependencias externas
    silabeo.py        división silábica fonológica y acento léxico
    verso.py          licencias, ley del acento final, lecturas alternativas
    poema.py          metro dominante, versos compuestos, confianza
    rima.py           rima consonante/asonante y esquema
    estrofas.py       estrofas y tipo de composición
    analisis.py       punto de entrada de las secciones A y B
  interpretacion/   cliente de Anthropic, esquema JSON y validaciones
frontend/           HTML, CSS y JS sin frameworks ni paso de compilación
tests/              tests de pytest (incluye los poemas de referencia)
```

## Instalación

Requiere Python 3.11 o posterior.

```bash
git clone https://github.com/TSchonfeld/analizador-poesia.git
cd analizador-poesia
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # y completá ANTHROPIC_API_KEY
```

La API key de Anthropic **solo** se lee desde la variable de entorno `ANTHROPIC_API_KEY` en el servidor: nunca llega al navegador y el archivo `.env` está en `.gitignore`. Sin API key la app funciona igual para la métrica y la versificación, y avisa que las secciones C, D y E no están disponibles.

Variables opcionales:

| Variable | Valor por defecto | Para qué sirve |
| --- | --- | --- |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Modelo usado para el análisis interpretativo |
| `ANTHROPIC_EFFORT` | `medium` | Nivel de esfuerzo del modelo (`low`, `medium`, `high`) |

## Uso

```bash
cd backend
uvicorn app.main:app --reload
```

Abrí <http://localhost:8000>, pegá un poema (separando las estrofas con una línea en blanco) y tocá **Analizar**. También podés cargar uno de los tres ejemplos. Los resultados aparecen en pestañas; desde ahí se exportan a Markdown o a PDF (con el diálogo de impresión del navegador, «Guardar como PDF»).

### API

```bash
curl -s http://localhost:8000/api/analizar \
  -H 'Content-Type: application/json' \
  -d '{"texto": "Que por mayo era, por mayo,\ncuando hace la calor,\ncuando los trigos encañan\ny están los campos en flor,", "interpretar": false}'
```

Fragmento de la respuesta (el segundo verso):

```json
{
  "numero": 2,
  "texto": "cuando hace la calor,",
  "silabeo": "cuan-do ha-ce la ca-lor",
  "licencias": [{"tipo": "hiato", "texto": "do ‖ ha"}],
  "ley_acento_final": "aguda",
  "ajuste_final": 1,
  "silabas": 8,
  "nombre": "octosílabo",
  "arte": "arte menor",
  "rima": "a",
  "terminacion": "-or",
  "confianza": "alta"
}
```

La respuesta completa tiene las claves `metrica` (versos y metros), `versificacion` (rima, estrofas y composición), `interpretativo` (recursos, temas e interpretación, o `null`) y `avisos`.

La documentación interactiva de la API está en <http://localhost:8000/docs>.

## Ejemplos

Con los poemas de referencia que usan los tests:

| Poema | Resultado |
| --- | --- |
| Garcilaso, Soneto V («Escrito está en mi alma vuestro gesto») | 14 endecasílabos, rima consonante ABBA ABBA CDE CDE, dos cuartetos y dos tercetos: **soneto**. El verso 1 se marca con confianza media porque admite dos hiatos posibles (es-tá ‖ en o mi ‖ al-ma). |
| Romance del prisionero («Que por mayo era, por mayo») | 16 octosílabos con asonancia en *o* en los pares: **romance**. En «cuando hace la calor» detecta la aguda (+1) y el hiato ante la *h*. |
| Espronceda, «Canción del pirata» | Octosílabos y tetrasílabos combinados por estrofas: **poema polimétrico**. Detecta la sinéresis de «sea cualquiera» y marca con confianza baja «a mi valor», que solo es tetrasílabo con sinafía. |

## Tests

```bash
pytest
```

Los tests del motor métrico usan un soneto de Garcilaso, un romance tradicional y la «Canción del pirata» de Espronceda (por la polimetría), además de alejandrinos de Darío, una décima de Calderón, redondillas de Sor Juana y una lira de San Juan de la Cruz. El módulo interpretativo se prueba con un cliente simulado, así que los tests no consumen la API. GitHub Actions corre los tests en cada push (Python 3.11, 3.12 y 3.13).

## Cómo funciona el motor métrico

1. **Silabeo** (`silabeo.py`): divide cada palabra en sílabas fonológicas (diptongos, triptongos, hiatos, grupos consonánticos, *h* muda, *qu* y *gu*), ubica la sílaba tónica y distingue palabras tónicas de átonas.
2. **Lecturas del verso** (`verso.py`): parte de la lectura por defecto (sinalefa en todo contacto vocálico entre palabras) y calcula el «costo» de cada desvío: hiato (más barato tras vocal tónica, ante pausa o ante *h*), sinéresis y diéresis (más caras; la diéresis marcada con *ü* o *ï* es obligatoria). La longitud es la posición de la última tónica más uno, que equivale a la ley del acento final.
3. **Metro del poema** (`poema.py`): busca la medida dominante y elige para cada verso la lectura que mejor encaja. Si hay versos compuestos (alejandrinos, dodecasílabos), computa cada hemistiquio por separado. Un verso que no encaja queda con confianza baja en lugar de forzarse.
4. **Versificación** (`rima.py`, `estrofas.py`): rima desde la última vocal tónica (en la asonancia se omite la penúltima vocal de las esdrújulas y la débil de los diptongos), esquema con mayúsculas para arte mayor y minúsculas para arte menor, estrofas y composición.

### Por qué no se usa rantanplan

Se evaluó la librería [rantanplan](https://pypi.org/project/rantanplan/) (proyecto POSTDATA, UNED): su última versión es de 2021, fija `spacy==2.2.4`, que no se instala en Python 3.11 ni 3.13, y con spaCy 3 falla al cargar el pipeline. Además necesita un modelo de spaCy de unos 40 MB solo para etiquetar categorías gramaticales. El motor de este repositorio reescribe la lógica de sus reglas sin esas dependencias; la tonicidad de las palabras se resuelve con una lista cerrada de átonas. rantanplan se distribuye con licencia Apache 2.0.

## Análisis interpretativo

El backend envía el poema numerado (y el resumen métrico, para que el modelo no lo contradiga) a la API de Anthropic con salida estructurada: el modelo solo puede responder con JSON que cumpla el esquema de `interpretacion/esquema.py`. Después, `interpretacion/validacion.py`:

- descarta cualquier recurso cuya cita no aparezca literalmente en el poema (no se inventan recursos) y corrige el número de verso si la cita está en otro;
- limita los subtemas a cuatro;
- cuenta las palabras de la interpretación y la recorta a 50 si se excede.

Si el modelo declina la solicitud, la API la reintenta con otro modelo (parámetro `fallbacks`).

## Despliegue

### Render

1. Subí el repositorio a GitHub.
2. En Render, **New → Blueprint** y elegí el repositorio: `render.yaml` crea el servicio web.
3. Cargá `ANTHROPIC_API_KEY` en **Environment** cuando Render la pida.

También se puede crear a mano un **Web Service** de Python con:

- Build command: `pip install -r requirements.txt`
- Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Railway

1. **New Project → Deploy from GitHub repo**.
2. Railway detecta Python e instala `requirements.txt`; el `Procfile` define el comando de inicio.
3. En **Variables**, agregá `ANTHROPIC_API_KEY`.

### Vercel

Vercel está pensado para funciones sin servidor; esta app corre mejor como servicio persistente en Render o Railway.

## Limitaciones conocidas

- **Sinafía:** el motor no hace sinalefa entre el final de un verso y el comienzo del siguiente; esos versos quedan con una sílaba de más y confianza baja.
- **Acentuación dudosa:** algunas palabras cambian de tonicidad según el contexto (por ejemplo, *como*, *cuando*, *donde* como relativos o como interrogativos sin tilde); el motor usa la lista de átonas y puede proponer alternativas.
- ***h* aspirada:** en textos de los Siglos de Oro la *h* que viene de *f* latina impedía la sinalefa. El motor lo trata como alternativa probable, no como regla fija.
- **Hiatos y diptongos inestables:** palabras como *riela* o *suave* admiten dos pronunciaciones; cuando el metro no decide, se muestran ambas lecturas.
- **Rima:** la rima consonante se compara por pronunciación sin seseo (*casa* y *caza* no riman en consonante). Un estribillo repetido rima consigo mismo.
- **Composiciones poco frecuentes:** la silva, la estrofa libre o el verso libre con metro de base se identifican de forma aproximada.
- **Análisis interpretativo:** depende de un modelo de lenguaje, puede variar entre ejecuciones y conviene revisarlo antes de usarlo en clase.
