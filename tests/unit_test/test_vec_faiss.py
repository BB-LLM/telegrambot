from mem.vector_stores.faiss import FAISS
from mem.embeddings.embed_api import embedding
import time

import shortuuid

faiss_cfg = {
    "collection_name": "memory_test",
    "path": "/Users/zouwuhe/Desktop/src/mem_minus/wks/faiss",
    "distance_strategy": "euclidean",
    "normalize_L2": False,
    "embedding_model_dims": 2560
}

faiss_inst = FAISS(**faiss_cfg)


def test_insert():
    faiss_inst.reset()
    # Insert more docs in another subject.
    docs = [
        "Machine learning has been used for drug design.",
        "Computational synthesis with AI algorithms predicts molecular properties.",
        "DDR1 is involved in cancers and fibrosis.",
    ]
    vectors = embedding(docs)
    ids = [str(shortuuid.uuid()) for i in range(len(docs))]
    payloads = [dict(text=doc) for doc in docs]
    faiss_inst.insert(vectors, payloads=payloads, ids=ids)


def test_search():
    query = "tell me AI related information"
    vector = embedding(query)
    result = faiss_inst.search(query, vector, limit=5)
    print(result)


def test_delete():
    vector_id = 'nscfTZ5ovaGxwWYbXncpoN'
    faiss_inst.delete(vector_id)


def test_update():
    vector_id = '8F5REw8BPD7rTmZPbYxAmU'
    text = 'Machine learning has been used for drug design, it not bad!'
    vector = embedding(text)
    payload = dict(text=text)
    faiss_inst.update(vector_id, vector=vector, payload=payload)


def test_get():
    vector_id = '8F5REw8BPD7rTmZPbYxAmU'
    result = faiss_inst.get(vector_id)
    print(result)


if __name__ == "__main__":
    test_insert()
    time.sleep(3)
    test_search()

    # test_delete()
    # time.sleep(1)
    # test_search()

    # test_update()
    # time.sleep(1)
    # test_search()
    # test_get()
