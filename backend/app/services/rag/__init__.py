"""RAG (retrieval-augmented generation) foundation services.

This package builds a knowledge base from uploaded publication PDFs by reusing
the existing document extraction pipeline, then cleaning, chunking and
embedding the text.  It intentionally contains no answer-generation logic in
this step — only the retrieval foundation.
"""
