"""
Vector Index Builder with MiniLM
================================
Generates semantic embeddings for enhanced schema documents.
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer
import os

def load_enhanced_documents(path: str):
    """Load enhanced schema documents."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_embeddings(documents, model_name='sentence-transformers/all-MiniLM-L6-v2'):
    """Generate MiniLM embeddings for all documents."""
    
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Extract document texts
    texts = [doc['document'] for doc in documents]
    
    print(f"Generating embeddings for {len(texts)} documents...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    
    print(f"Embedding shape: {embeddings.shape}")
    
    return embeddings.tolist()


def build_vector_index(enhanced_docs_path: str, output_path: str):
    """Build complete vector index."""
    
    # Load documents
    print("Loading enhanced documents...")
    documents = load_enhanced_documents(enhanced_docs_path)
    
    # Generate embeddings
    embeddings = generate_embeddings(documents)
    
    # Combine with metadata
    vector_index = []
    for i, doc in enumerate(documents):
        vector_index.append({
            "table": doc['table'],
            "column": doc['column'],
            "data_type": doc['data_type'],
            "embedding": embeddings[i],
            "semantic": doc.get('semantic', {}),
            "search_text": doc['document']
        })
    
    # Save
    print(f"Saving vector index to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(vector_index, f, indent=2)
    
    print(f"Vector index created with {len(vector_index)} entries")
    
    # Print sample
    print("\nSample entry:")
    sample = vector_index[0]
    print(f"  Table: {sample['table']}")
    print(f"  Column: {sample['column']}")
    print(f"  Embedding dims: {len(sample['embedding'])}")
    
    return vector_index


if __name__ == "__main__":
    build_vector_index(
        "enhanced_schema_documents.json",
        "vector_index.json"
    )
