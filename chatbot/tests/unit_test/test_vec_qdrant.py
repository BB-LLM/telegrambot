from mem.vector_stores.qdrant import Qdrant
from mem.embeddings.embed_api import embedding
import time

import shortuuid

qdrant_cfg = {
    "collection_name": "memory_test",
    "embedding_model_dims": 2560,
    "client": None,
    "host": "", # http://7.34.73.70:6333/collections
    "port": 6333,
    "path": "/Users/zouwuhe/Desktop/src/mem_minus/wks/qdrant",
    "url": "https://d8a17329-41df-49fc-811f-c5e762a2b12e.europe-west3-0.gcp.cloud.qdrant.io:6333",
    "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zyODVTAKCSNpo0cBBh6yXMlf29A8nJAaz42KTTZP2hk",
    "on_disk": False
}

faiss_inst = Qdrant(**qdrant_cfg)


def test_insert():
    faiss_inst.reset()
    # Insert more docs in another subject.
    docs = [
        "Machine learning has been used for drug design.",
        "Computational synthesis with AI algorithms predicts molecular properties.",
        "DDR1 is involved in cancers and fibrosis.",
    ]
    vectors = embedding(docs)
    ids = [i for i in range(len(docs))]
    payloads = [dict(text=doc) for doc in docs]
    faiss_inst.insert(vectors, payloads=payloads, ids=ids)


def test_search():
    query = "tell me AI related information"
    vector = embedding(query)
    result = faiss_inst.search(query, vector, limit=5)
    print(result)


def test_delete():
    vector_id = 0
    faiss_inst.delete(vector_id)


def test_update():
    vector_id = 1
    text = 'Machine learning has been used for drug design, it not bad!'
    vector = embedding(text)
    payload = dict(text=text)
    faiss_inst.update(vector_id, vector=vector, payload=payload)


def test_get():
    vector_id = 1
    result = faiss_inst.get(vector_id)
    print(result)


if __name__ == "__main__":
    test_insert()
    time.sleep(3)
    test_search()

    test_delete()
    time.sleep(1)
    test_search()

    test_update()
    test_get()
