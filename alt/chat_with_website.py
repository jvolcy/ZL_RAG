#!/usr/bin/env python3

import chromadb
import ollama

from sentence_transformers import SentenceTransformer

##########################################################################
# Configuration
##########################################################################

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "website"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

OLLAMA_MODEL = "qwen3:14b"

TOP_K = 5

##########################################################################
# Load Components
##########################################################################

print("Loading embedding model...")

embedder = SentenceTransformer(
    EMBEDDING_MODEL
)

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_collection(
    COLLECTION_NAME
)

print("Ready.")

##########################################################################
# Retrieval
##########################################################################

def retrieve_context(question):

    query_embedding = embedder.encode(
        question
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    return documents, metadatas

##########################################################################
# Prompt Builder
##########################################################################

def build_prompt(question, documents):

    context = "\n\n".join(documents)

    prompt = f"""
You are an assistant that answers questions about a website.

Use ONLY the information contained in the supplied context.

If the answer cannot be found in the context,
say:

"I could not find that information in the website content."

Do not invent facts.

CONTEXT
========

{context}

QUESTION
========

{question}

ANSWER
======
"""

    return prompt

##########################################################################
# Ask Ollama
##########################################################################

def ask_ollama(prompt):

    response = ollama.chat(

        model=OLLAMA_MODEL,

        messages=[

            {
                "role": "system",
                "content":
                "Answer accurately using provided context."
            },

            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]

##########################################################################
# Interactive Chat Loop
##########################################################################

def chat():

    print()
    print("Website Assistant")
    print("Type 'quit' to exit.")
    print()

    while True:

        question = input("\nQuestion> ").strip()

        if not question:
            continue

        if question.lower() in [
            "quit",
            "exit",
            "q"
        ]:
            break

        print("\nSearching...")

        documents, metadatas = retrieve_context(
            question
        )

        prompt = build_prompt(
            question,
            documents
        )

        print("Asking model...")

        answer = ask_ollama(
            prompt
        )

        print("\n" + "="*70)
        print("ANSWER")
        print("="*70)
        print(answer)

        print("\nSources:")
        shown = set()

        for meta in metadatas:

            source = meta["source"]

            if source not in shown:
                print(" -", source)
                shown.add(source)

        print()

##########################################################################
# Main
##########################################################################

if __name__ == "__main__":
    chat()