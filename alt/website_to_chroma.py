#!/usr/bin/env python3

import requests
import chromadb
import hashlib

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import urlparse

from sentence_transformers import SentenceTransformer

##########################################################################
# Configuration
##########################################################################

START_URL = "https://www.example.org"

MAX_PAGES = 100

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "website"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

##########################################################################
# Utilities
##########################################################################

def normalize_url(url):
    """
    Remove fragments.
    """

    parsed = urlparse(url)

    return parsed._replace(fragment="").geturl()


def is_internal_link(base_domain, url):

    parsed = urlparse(url)

    return (
        parsed.netloc == ""
        or parsed.netloc == base_domain
    )


##########################################################################
# Crawl Website
##########################################################################

def extract_text(html):

    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    return "\n".join(lines)


def crawl_site(start_url, max_pages=100):

    domain = urlparse(start_url).netloc

    visited = set()

    queue = [start_url]

    pages = []

    while queue and len(visited) < max_pages:

        url = queue.pop(0)

        url = normalize_url(url)

        if url in visited:
            continue

        print(f"Crawling: {url}")

        visited.add(url)

        try:

            response = requests.get(
                url,
                timeout=15
            )

            response.raise_for_status()

        except Exception as e:

            print(f"Failed: {url}")
            print(e)

            continue

        html = response.text

        text = extract_text(html)

        pages.append({
            "url": url,
            "text": text
        })

        soup = BeautifulSoup(html, "lxml")

        for link in soup.find_all("a", href=True):

            href = link["href"]

            absolute = urljoin(url, href)

            absolute = normalize_url(absolute)

            if is_internal_link(domain, absolute):

                if absolute not in visited:

                    queue.append(absolute)

    return pages


##########################################################################
# Chunking
##########################################################################

def chunk_text(text,
               chunk_size=1000,
               overlap=200):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += (chunk_size - overlap)

    return chunks


##########################################################################
# Build Documents
##########################################################################

def build_documents(pages):

    docs = []

    for page in pages:

        chunks = chunk_text(
            page["text"],
            CHUNK_SIZE,
            CHUNK_OVERLAP
        )

        for chunk_number, chunk in enumerate(chunks):

            docs.append({

                "id": hashlib.md5(
                    (
                        page["url"]
                        + str(chunk_number)
                    ).encode()
                ).hexdigest(),

                "text": chunk,

                "source": page["url"],

                "chunk": chunk_number
            })

    return docs


##########################################################################
# Chroma Storage
##########################################################################

def create_collection():

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    try:
        client.delete_collection(
            COLLECTION_NAME
        )
    except:
        pass

    collection = client.create_collection(
        COLLECTION_NAME
    )

    return collection


def store_documents(documents):

    print(
        f"Loading embedding model: "
        f"{EMBEDDING_MODEL}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    collection = create_collection()

    batch_size = 32

    for i in range(
            0,
            len(documents),
            batch_size):

        batch = documents[
            i:i + batch_size
        ]

        texts = [
            d["text"]
            for d in batch
        ]

        embeddings = model.encode(
            texts,
            show_progress_bar=False
        )

        collection.add(

            ids=[
                d["id"]
                for d in batch
            ],

            documents=texts,

            embeddings=[
                e.tolist()
                for e in embeddings
            ],

            metadatas=[

                {
                    "source": d["source"],
                    "chunk": d["chunk"]
                }

                for d in batch
            ]
        )

        print(
            f"Stored "
            f"{min(i+batch_size, len(documents))}"
            f"/{len(documents)}"
        )

    print(
        f"\nDone.\n"
        f"Indexed {len(documents)} chunks."
    )


##########################################################################
# Main
##########################################################################

def main():

    print("Step 1: Crawling Website")

    pages = crawl_site(
        START_URL,
        MAX_PAGES
    )

    print(
        f"Collected {len(pages)} pages"
    )

    print("Step 2: Chunking")

    documents = build_documents(
        pages
    )

    print(
        f"Created {len(documents)} chunks"
    )

    print("Step 3: Embedding + Chroma")

    store_documents(
        documents
    )

    print("Finished")


if __name__ == "__main__":
    main()