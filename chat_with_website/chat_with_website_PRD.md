# Product Requirements Document

## Project: Website Knowledge Assistant

### Document Version

1.0

### Purpose

Build a Python application that uses Retrieval-Augmented Generation (RAG) to answer questions using content stored in a ChromaDB knowledge base.

The application shall run locally and use Ollama-hosted language models.

---

# Goals

The system shall:

* Accept natural language questions.
* Retrieve relevant website content.
* Construct grounded prompts.
* Generate answers using Ollama.
* Provide source attribution.

---

# Non-Goals

The system shall not:

* Crawl websites.
* Generate embeddings for website content.
* Modify indexed data.
* Fine-tune language models.

---

# Functional Requirements

## FR-1 Startup

At startup the application shall:

* Load the embedding model.
* Connect to ChromaDB.
* Verify collection availability.
* Verify Ollama connectivity.

Startup failures shall generate meaningful errors.

---

## FR-2 User Input

The system shall:

* Accept user questions interactively.
* Support continuous chat sessions.
* Allow graceful exit commands.

Supported commands:

* quit
* exit
* q

---

## FR-3 Query Embedding

For every question the system shall:

* Generate an embedding using the configured embedding model.

The query embedding model must match the model used during indexing.

---

## FR-4 Retrieval

The system shall:

* Query ChromaDB using vector similarity search.
* Retrieve the top K matching chunks.

The value of K shall be configurable.

Default:

* K = 5

---

## FR-5 Prompt Construction

The system shall construct prompts containing:

* Assistant instructions
* Retrieved context
* User question

The prompt shall explicitly instruct the LLM to:

* Use supplied context
* Avoid hallucination
* Admit when information is unavailable

---

## FR-6 Ollama Integration

The system shall:

* Connect to a local Ollama server.
* Submit prompts.
* Receive generated responses.

Supported models include:

* qwen3:14b
* qwen3:32b
* llama3
* mistral

The configured model shall be user selectable.

---

## FR-7 Source Attribution

The system shall display:

* Source URLs used during retrieval

Source URLs shall be deduplicated before presentation.

---

## FR-8 Chat Session

The system shall support:

* Multiple questions per session
* Repeated retrieval operations
* Continuous interaction until exit

---

# Future Requirements

## Phase 2: Conversation Memory

The system should support:

* Multi-turn conversation history
* Context retention
* Follow-up questions

---

## Phase 2: Reranking

The system should support:

* Initial retrieval of 20 chunks
* Cross-encoder reranking
* Final selection of top chunks

---

## Phase 2: Hybrid Search

The system should support:

* Vector search
* Keyword search
* Combined scoring

---

## Phase 2: Tool Use

The system should support tool calling for:

* Python execution
* CSV analysis
* PDF generation
* Translation
* Document search

---

# Non-Functional Requirements

## Performance

Target response time:

* Retrieval under 1 second
* Full response under 10 seconds on typical hardware

---

## Reliability

The system shall:

* Handle Ollama failures gracefully
* Handle ChromaDB failures gracefully
* Continue running after individual query errors

---

## Security

The system shall:

* Operate entirely locally
* Not require cloud services
* Not transmit data externally

---

# Success Criteria

The system is considered successful when:

* Questions are answered using indexed content
* Sources are displayed correctly
* Responses are grounded in retrieved context
* Users can interact continuously in a local chat session
