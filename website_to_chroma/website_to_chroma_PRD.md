# Product Requirements Document

## Project: Website Knowledge Base Indexer

### Document Version

1.0

### Purpose

Build a Python application that crawls a website, extracts textual content, generates embeddings for the content, and stores the resulting vector representations in a local ChromaDB database for later retrieval by a chatbot.

The application is intended to run locally on Linux and support self-hosted AI assistants powered by Ollama.

---

# Goals

The system shall:

* Crawl a website beginning from a specified URL.
* Discover and follow internal links.
* Extract useful textual content from HTML pages.
* Remove non-content elements such as scripts and styles.
* Split content into appropriately sized chunks.
* Generate vector embeddings for each chunk.
* Store embeddings and metadata in ChromaDB.
* Support periodic re-indexing of the website.

---

# Non-Goals

The system shall not:

* Answer user questions.
* Generate responses using an LLM.
* Modify website content.
* Perform authentication-protected crawling.
* Execute JavaScript rendering.

---

# Functional Requirements

## FR-1 Configuration

The application shall allow configuration of:

* Start URL
* Maximum pages to crawl
* Chunk size
* Chunk overlap
* ChromaDB storage location
* Collection name
* Embedding model name

Configuration may be supplied through:

* Constants
* Configuration file
* Command line arguments

---

## FR-2 Website Crawling

The application shall:

* Crawl pages beginning from the configured start URL.
* Follow only internal links.
* Ignore external domains.
* Prevent duplicate page processing.
* Support configurable crawl limits.

The crawler shall maintain:

* Visited URL list
* Pending URL queue

---

## FR-3 HTML Processing

The application shall:

* Download page content.
* Parse HTML.
* Remove:

  * script tags
  * style tags
  * noscript tags

The application shall extract readable text from remaining content.

---

## FR-4 Content Storage

For each page the system shall store:

* URL
* Extracted text
* Crawl timestamp

---

## FR-5 Text Chunking

The application shall:

* Divide text into overlapping chunks.
* Support configurable chunk size.
* Support configurable overlap.

Each chunk shall contain:

* Chunk text
* Source URL
* Chunk number

---

## FR-6 Embedding Generation

The application shall:

* Load a Sentence Transformer model.
* Generate embeddings for every chunk.
* Process embeddings in batches.

Supported models should include:

* BAAI/bge-small-en-v1.5
* BAAI/bge-base-en-v1.5
* nomic-ai embeddings

---

## FR-7 Vector Storage

The application shall:

* Create a ChromaDB collection.
* Store:

  * Chunk ID
  * Chunk text
  * Embedding
  * Metadata

Metadata shall include:

* Source URL
* Chunk index

---

## FR-8 Rebuild Mode

The application shall support:

* Full index rebuild
* Collection replacement

The existing collection may be deleted before re-indexing.

---

# Non-Functional Requirements

## Performance

The system should:

* Process at least 100 pages per crawl.
* Batch embedding requests.
* Support indexing several thousand chunks.

---

## Reliability

The system shall:

* Continue crawling after individual page failures.
* Log failed URLs.
* Avoid duplicate processing.

---

## Logging

The application shall log:

* Pages crawled
* Chunks generated
* Embeddings stored
* Errors encountered

---

# Success Criteria

A successful run results in:

* Website content stored in ChromaDB
* Source metadata attached to all chunks
* No duplicate URLs indexed
* Chroma collection available for retrieval applications
