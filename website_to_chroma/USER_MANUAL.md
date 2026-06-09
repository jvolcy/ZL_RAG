# Website Knowledge Base Indexer — User Manual

## Overview

The **Website Knowledge Base Indexer** is a desktop application that builds a searchable vector index from website content. It runs a three-stage pipeline:

1. **Crawl & HTML** — download pages and extract readable text  
2. **Chunking** — split text into overlapping segments  
3. **Embed & Store** — generate embeddings and save them to a local ChromaDB database  

The result is a ChromaDB collection you can connect to a separate chatbot or RAG application (for example, one powered by Ollama). This program does **not** answer questions or call an LLM itself.

Each pipeline stage is **independent**: you can run, re-run, or skip stages without repeating earlier work. Intermediate results are saved to disk as versioned files.

---

## Requirements

- **Python 3.10+** (3.12 recommended)
- **Linux** (primary target; the GUI uses Tkinter, which is included with most Python installations)
- Network access to the website you want to crawl
- Sufficient disk space for crawl output, chunk files, embedding models (downloaded on first use), and ChromaDB storage

### Python dependencies

Installed automatically from `requirements.txt`:

- beautifulsoup4  
- chromadb  
- PyYAML  
- requests  
- sentence-transformers  

The first embedding run downloads the selected model from Hugging Face; this may take several minutes.

---

## Installation

From the project directory:

```bash
source setup.sh
```

This creates a virtual environment (`.venv`), activates it, and installs dependencies.

> **Note:** `setup.sh` must be **sourced**, not executed directly:
>
> ```bash
> source setup.sh
> ```
>
> or
>
> ```bash
> . setup.sh
> ```

---

## Starting the application

With the virtual environment activated:

```bash
python main.py
```

Or use the convenience script (after setup):

```bash
./start.sh
```

On launch, you are prompted to **create a new project** or **open an existing one**.

---

## Projects

A **project** is a self-contained workspace on disk. All configuration, intermediate outputs, and the vector database for one indexing effort live inside a single project folder.

### Creating a project

1. **File → New Project…**
2. Choose a **parent directory** (where the project folder will be created).
3. Enter a **project name**.

The application creates a subdirectory named after your project (special characters are converted to underscores). For example, choosing parent `/home/user/indexes` and name `My Wiki` creates:

```
/home/user/indexes/My_Wiki/
```

### Opening a project

**File → Open Project…** and select the project folder that contains `project.json`.

### Project folder layout

```
my_project/
├── project.json          # Project manifest and run history
├── tab1_config.json      # Crawl settings (auto-saved)
├── tab2_config.json      # Chunking settings (auto-saved)
├── tab3_config.json      # Embedding settings (auto-saved)
├── outputs/
│   ├── crawl/
│   │   ├── crawl_20260609T120000.jsonl
│   │   └── crawl_20260609T143022.jsonl   # versioned outputs
│   └── chunks/
│       ├── chunks_20260609T120500.jsonl
│       └── chunks_20260609T150000.jsonl
└── chroma_db/            # ChromaDB persistent storage
```

Settings on each tab are **saved automatically** to the corresponding `tab*_config.json` file when you change them.

---

## Application layout

The main window has:

- A **menu bar** (File → New Project, Open Project, Exit)
- A **project header** showing the open project name and path
- **Three tabs**, one per pipeline stage
- On each tab:
  - **Configuration** fields at the top
  - **Run** and **Cancel** buttons
  - A **progress bar**
  - A **log panel** with live output

Long-running tasks execute in the background so the interface stays responsive.

---

## Typical workflow

### Full pipeline (first time)

1. Create or open a project.
2. **Tab 1** — set the start URL and crawl options, then click **Run**.
3. **Tab 2** — confirm the crawl JSONL input (defaults to the latest crawl output), adjust chunk settings, click **Run**.
4. **Tab 3** — confirm the chunks JSONL input, choose an embedding model, click **Run**.

When Tab 1 or Tab 2 finishes successfully, the next tab’s **input path** is updated automatically to that run’s output file.

### Re-running a single stage

Because each stage reads from disk, you can re-run any tab without repeating earlier steps:

| Goal | Action |
|------|--------|
| Re-crawl the site | Run Tab 1 only |
| Re-chunk with different sizes | Run Tab 2 (point input at any crawl file) |
| Re-embed or switch models | Run Tab 3 (point input at any chunks file) |

Older output files are **kept** (versioned by timestamp). You can select a previous file using **Browse…** on Tab 2 or Tab 3.

### Staleness warnings

Tabs 2 and 3 show a warning at the top if a **newer upstream output** exists than the file currently selected as input. For example, after re-crawling without re-chunking, Tab 2 warns that your selected crawl file may be stale.

You can ignore the warning if you intentionally want to use an older file.

---

## Tab 1: Crawl & HTML

Downloads web pages, parses HTML, removes scripts/styles, and saves extracted text.

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Start URL** | Page where crawling begins | `https://example.com` |
| **Max pages** | Maximum number of pages to crawl | `100` |
| **Crawl delay (s)** | Seconds to wait between requests | `0` |
| **Request timeout (s)** | HTTP timeout per page | `30` |
| **User agent** | `User-Agent` header sent with requests | `WebsiteToChromaIndexer/1.0` |
| **Output directory** | Where versioned crawl files are written | `<project>/outputs/crawl` |

### Crawl scope

Three checkboxes control which links are followed. **All internal links** overrides the other two when checked.

| Option | Effect |
|--------|--------|
| **All internal links** | Follow every link on the same domain |
| **Start URL and descendants** | Follow the start page and any path under it |
| **Siblings of start path and their descendants** | Follow same-level sibling paths (e.g. `/docs/other` when start is `/docs/start`) and everything under those siblings |

These options are **additive** (except when “All internal links” is on). Examples:

- **Descendants only** — check “Start URL and descendants”; leave siblings unchecked.  
- **Descendants + siblings** — check both (default).  
- **Entire site** — check “All internal links”.

### Output

Each run creates a timestamped file:

```
crawl_YYYYMMDDTHHMMSS.jsonl
```

Each line is one page:

```json
{"url": "https://example.com/page", "text": "...", "crawled_at": "2026-06-09T12:00:00+00:00"}
```

Raw HTML is **not** saved.

### Limitations

- No JavaScript rendering (static HTML only)  
- No authentication or login-protected pages  
- Only `http://` and `https://` pages with HTML content are processed  
- Failed pages are logged and skipped; the crawl continues  

---

## Tab 2: Chunking

Reads a crawl JSONL file and splits page text into overlapping chunks.

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Input (crawl JSONL)** | Crawl output file to chunk | Latest crawl output |
| **Chunk size** | Target chunk length in characters | `1000` |
| **Chunk overlap** | Overlap between consecutive chunks | `200` |
| **Output directory** | Where versioned chunk files are written | `<project>/outputs/chunks` |

Overlap must be less than chunk size.

### Output

Each run creates:

```
chunks_YYYYMMDDTHHMMSS.jsonl
```

Each line is one chunk:

```json
{"text": "...", "source_url": "https://example.com/page", "chunk_index": 0}
```

---

## Tab 3: Embed & Store

Reads a chunks JSONL file, generates vector embeddings, and stores them in ChromaDB.

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Input (chunks JSONL)** | Chunks file to embed | Latest chunks output |
| **Embedding model** | Sentence Transformers model (dropdown) | `BAAI/bge-small-en-v1.5` |
| **Embed batch size** | Chunks processed per embedding batch | `32` |
| **ChromaDB path** | Persistent database directory | `<project>/chroma_db` |
| **Collection name** | ChromaDB collection name | `website` |
| **Store batch size** | Chunks written per ChromaDB upsert | `100` |
| **Rebuild collection** | Delete and recreate the named collection before storing | Off |
| **Wipe entire ChromaDB folder** | Delete the full `chroma_db` directory before storing | Off |

### Embedding models

Predefined options in the dropdown:

- `BAAI/bge-small-en-v1.5` (default; fast, good quality)  
- `BAAI/bge-base-en-v1.5` (larger, often better quality)  
- `nomic-ai/nomic-embed-text-v1.5`  
- `sentence-transformers/all-MiniLM-L6-v2` (lightweight)  

If a saved project uses a model not in the list, it appears in the dropdown automatically.

### Rebuild vs. wipe

| Option | Scope | When to use |
|--------|-------|-------------|
| **Rebuild collection** | Deletes only the named collection (e.g. `website`) | Normal re-index; other collections in the same folder are kept |
| **Wipe entire ChromaDB folder** | Deletes everything under `chroma_path` | Full reset; removes all collections and orphaned data |

These two options are **mutually exclusive**. Wipe shows a **confirmation dialog** before running. After a successful wipe, the wipe checkbox **clears automatically** so it is not left enabled by mistake.

If neither option is checked, new embeddings are **upserted** into the existing collection (same chunk IDs are updated; new chunks are added).

### ChromaDB metadata

Each stored chunk includes:

- **Document text** — the chunk content  
- **Embedding** — vector from the selected model  
- **Metadata** — `source_url`, `chunk_index`  

---

## Using the index with other tools

After Tab 3 completes, point your retrieval application at:

- **Path:** the project’s `chroma_db` folder (or the custom path you configured)  
- **Collection:** the collection name you set (default `website`)  

Example (Python):

```python
import chromadb

client = chromadb.PersistentClient(path="/path/to/my_project/chroma_db")
collection = client.get_collection("website")
results = collection.query(query_texts=["your search query"], n_results=5)
```

Ensure your retrieval app uses an embedding model **compatible** with the one used during indexing, or pass pre-computed query embeddings.

---

## Tips and troubleshooting

### Crawl returns few or no pages

- Verify the start URL is reachable in a browser.  
- Check crawl scope — a narrow scope may exclude most site links.  
- Increase **Max pages**.  
- Add **Crawl delay** if the server rate-limits requests.  
- Sites that require JavaScript will not render correctly (no JS support).

### Embedding run is slow

- First run downloads the model; later runs are faster.  
- Use a smaller model (`bge-small` or `all-MiniLM-L6-v2`).  
- Increase **Embed batch size** if you have enough RAM/GPU memory.

### “Configuration error” on Run

- Required paths (input, ChromaDB path) must be set.  
- Chunk overlap must be less than chunk size.  
- Start URL must begin with `http://` or `https://`.

### Cancel a running task

Click **Cancel** on the active tab. The task stops at the next safe checkpoint (between pages or embedding batches). Partial results from an interrupted Tab 1 or Tab 2 run are not saved unless the stage completed.

### Exit while a task is running

Closing the window prompts for confirmation. Choosing to exit cancels any running task.

---

## What this program does not do

- Answer questions or generate chat responses  
- Render JavaScript-heavy sites  
- Crawl login-protected or authenticated content  
- Modify website content  
- Query or browse the index from within this GUI (indexing only)  

---

## Quick reference

| Task | Steps |
|------|-------|
| New index from scratch | Tab 1 → Tab 2 → Tab 3 |
| Update crawl only | Tab 1 → Run |
| Re-chunk existing crawl | Tab 2 → pick crawl file → Run |
| Re-embed existing chunks | Tab 3 → pick chunks file → Run |
| Replace one collection | Tab 3 → Rebuild collection → Run |
| Full database reset | Tab 3 → Wipe entire ChromaDB folder → confirm → Run |
| Switch embedding model | Tab 3 → new model → Rebuild or Wipe → Run |

---

## File reference

| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `setup.sh` | Create venv and install dependencies |
| `start.sh` | Launch the GUI |
| `project.json` | Project name, timestamps, run history |
| `tab1_config.json` | Saved crawl settings |
| `tab2_config.json` | Saved chunking settings |
| `tab3_config.json` | Saved embedding settings |
| `outputs/crawl/*.jsonl` | Versioned crawl results |
| `outputs/chunks/*.jsonl` | Versioned chunk results |
| `chroma_db/` | ChromaDB persistent vector store |
