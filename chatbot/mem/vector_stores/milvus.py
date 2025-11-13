from loguru import logger
from typing import Dict, Optional

import time
from pydantic import BaseModel
from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field, model_validator
from mem.vector_stores.base import VectorStoreBase

try:
    import pymilvus  # noqa: F401
except ImportError:
    raise ImportError("The 'pymilvus' library is required. Please install it using 'pip install pymilvus'.")

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient


class MetricType(str, Enum):
    """
    Metric Constant for milvus/ zilliz server.
    """

    def __str__(self) -> str:
        return str(self.value)

    L2 = "L2"
    IP = "IP"
    COSINE = "COSINE"
    HAMMING = "HAMMING"
    JACCARD = "JACCARD"


class OutputData(BaseModel):
    id: Optional[str]  # memory id
    score: Optional[float]  # distance
    payload: Optional[Dict]  # metadata


class MilvusDBConfig(BaseModel):
    url: str = Field("http://localhost:19530", description="Full URL for Milvus/Zilliz server")
    token: str = Field(None, description="Token for Zilliz server / local setup defaults to None.")
    user: str = Field(None, description="user name.")
    password: str = Field(None, description="password.")
    collection_name: str = Field("mem0", description="Name of the collection")
    embedding_model_dims: int = Field(1536, description="Dimensions of the embedding model")
    metric_type: str = Field("COSINE", description="Metric type for similarity search")

    @model_validator(mode="before")
    @classmethod
    def validate_extra_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        allowed_fields = set(cls.model_fields.keys())
        input_fields = set(values.keys())
        extra_fields = input_fields - allowed_fields
        if extra_fields:
            raise ValueError(
                f"Extra fields not allowed: {', '.join(extra_fields)}. Please input only the following fields: {', '.join(allowed_fields)}"
            )
        return values

    model_config = {
        "arbitrary_types_allowed": True,
    }


class MilvusDB(VectorStoreBase):
    def __init__(
        self,
        url: str,
        token: str,
        user: str,
        password: str,
        collection_name: str,
        embedding_model_dims: int,
        metric_type: MetricType,
    ) -> None:
        """Initialize the MilvusDB database.

        Args:
            url (str): Full URL for Milvus/Zilliz server.
            token (str): Token/api_key for Zilliz server / for local setup defaults to None.
            collection_name (str): Name of the collection (defaults to mem0).
            embedding_model_dims (int): Dimensions of the embedding model (defaults to 1536).
            metric_type (MetricType): Metric type for similarity search (defaults to L2).
        """
        self.collection_name = collection_name
        self.embedding_model_dims = embedding_model_dims
        self.metric_type = metric_type
        if token:
            self.client = MilvusClient(uri=url, token=token)
        else:
            self.client = MilvusClient(uri=url, user=user, password=password)
        self.create_col(
            collection_name=self.collection_name,
            vector_size=self.embedding_model_dims,
            metric_type=self.metric_type,
        )

    def create_col(
        self,
        collection_name: str,
        vector_size: int,
        metric_type: MetricType = MetricType.COSINE,
    ) -> None:
        """Create a new collection with index_type AUTOINDEX.

        Args:
            collection_name (str): Name of the collection (defaults to mem0).
            vector_size (int): Dimensions of the embedding model (defaults to 1536).
            metric_type (MetricType, optional): metric type for similarity search. Defaults to MetricType.COSINE.
        """

        if self.client.has_collection(collection_name):
            logger.info(f"Collection {collection_name} already exists. Skipping creation.")
        else:
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=512),
                FieldSchema(name="vectors", dtype=DataType.FLOAT_VECTOR, dim=vector_size),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="timestamp", dtype=DataType.INT32),
            ]

            schema = CollectionSchema(fields, enable_dynamic_field=True)

            index = self.client.prepare_index_params(
                field_name="vectors", metric_type=metric_type, index_type="AUTOINDEX", index_name="vector_index"
            )
            self.client.create_collection(collection_name=collection_name, schema=schema, index_params=index)

            # 新增索引 需要milvus v2.5.14
            new_index_params = self.client.prepare_index_params()
            new_index_params.add_index(
                field_name="metadata",
                index_type="INVERTED",
                index_name="userid_index",
                params={"json_path": "metadata[\"user_id\"]", "json_cast_type": "varchar"}
            )
            new_index_params.add_index(
                field_name="metadata",
                index_type="INVERTED",
                index_name="agentid_index",
                params={"json_path": "metadata[\"agent_id\"]", "json_cast_type": "varchar"}
            )
            new_index_params.add_index(
                field_name="metadata",
                index_type="INVERTED",
                index_name="type_index",
                params={"json_path": "metadata[\"type\"]", "json_cast_type": "varchar"}
            )
            new_index_params.add_index(
                field_name="timestamp",
                index_type="STL_SORT",
                index_name="timestamp_index",
            )

            self.client.create_index(
                collection_name=collection_name,
                index_params=new_index_params,
                sync=False  # Whether to wait for index creation to complete before returning. Defaults to True.
            )

    def insert(self, vectors, payloads=None, ids=None, **kwargs: Optional[dict[str, any]]):
        """Insert vectors into a collection.

        Args:
            vectors (List[List[float]]): List of vectors to insert.
            payloads (list[dict], optional): List of payloads corresponding to vectors. Defaults to None.
            ids (list[str], optional): List of IDs corresponding to vectors. Defaults to None.
        """
        for idx, embedding, metadata in zip(ids, vectors, payloads):
            data = {"id": idx, "vectors": embedding, "metadata": metadata, "timestamp": int(time.time())}
            self.client.insert(collection_name=self.collection_name, data=data, **kwargs)

    def _create_filter(self, filters: dict):
        """Prepare filters for efficient query.

        Args:
            filters (dict): filters [user_id, agent_id, run_id]

        Returns:
            str: formated filter.
        """
        operands = []
        for key, value in filters.items():
            if isinstance(value, str):
                operands.append(f'(metadata["{key}"] == "{value}")')
            else:
                operands.append(f'(metadata["{key}"] == {value})')

        return " and ".join(operands)

    def _parse_output(self, data: list, threshold: float):
        """
        Parse the output data.

        Args:
            data (Dict): Output data.

        Returns:
            List[OutputData]: Parsed output data.
        """
        memory = []

        for value in data:
            uid, score, metadata = (
                value.get("id"),
                value.get("distance"),
                value.get("entity", {}).get("metadata"),
            )

            # score threshold = 0.4
            if score >= threshold:
                memory_obj = OutputData(id=uid, score=score, payload=metadata)
                memory.append(memory_obj)

        return memory

    def search(self, query: str, vectors: list, limit: int = 5, filters: dict = None, threshold: float = 0.4) -> list:
        """
        Search for similar vectors.

        Args:
            query (str): Query.
            vectors (List[float]): Query vector.
            limit (int, optional): Number of results to return. Defaults to 5.
            filters (Dict, optional): Filters to apply to the search. Defaults to None.
            threshold: score_threshold

        Returns:
            list: Search results.
        """
        query_filter = self._create_filter(filters) if filters else None
        hits = self.client.search(
            collection_name=self.collection_name,
            data=[vectors],
            limit=limit,
            filter=query_filter,
            output_fields=["*"],
        )
        result = self._parse_output(data=hits[0], threshold=threshold)
        return result

    def delete(self, vector_id):
        """
        Delete a vector by ID.

        Args:
            vector_id (str): ID of the vector to delete.
        """
        self.client.delete(collection_name=self.collection_name, ids=vector_id)

    def update(self, vector_id=None, vector=None, payload=None):
        """
        Update a vector and its payload.

        Args:
            vector_id (str): ID of the vector to update.
            vector (List[float], optional): Updated vector.
            payload (Dict, optional): Updated payload.
        """
        schema = {"id": vector_id, "vectors": vector, "metadata": payload, "timestamp": int(time.time())}
        self.client.upsert(collection_name=self.collection_name, data=schema)

    def get(self, vector_id):
        """
        Retrieve a vector by ID.

        Args:
            vector_id (str): ID of the vector to retrieve.

        Returns:
            OutputData: Retrieved vector.
        """
        result = self.client.get(collection_name=self.collection_name, ids=vector_id)
        output = OutputData(
            id=result[0].get("id", None),
            score=None,
            payload=result[0].get("metadata", None),
        )
        return output

    def list_cols(self):
        """
        List all collections.

        Returns:
            List[str]: List of collection names.
        """
        return self.client.list_collections()

    def delete_col(self):
        """Delete a collection."""
        return self.client.drop_collection(collection_name=self.collection_name)

    def col_info(self):
        """
        Get information about a collection.

        Returns:
            Dict[str, Any]: Collection information.
        """
        return self.client.get_collection_stats(collection_name=self.collection_name)

    def list(self, filters: dict = None, limit: int = 100) -> list:
        """
        List all vectors in a collection.

        Args:
            filters (Dict, optional): Filters to apply to the list.
            limit (int, optional): Number of vectors to return. Defaults to 100.

        Returns:
            List[OutputData]: List of vectors.
        """
        query_filter = self._create_filter(filters) if filters else None
        result = self.client.query(collection_name=self.collection_name, filter=query_filter, limit=limit)
        memories = []
        for data in result:
            obj = OutputData(id=data.get("id"), score=None, payload=data.get("metadata"))
            memories.append(obj)
        return memories

    def reset(self):
        """Reset the index by deleting and recreating it."""
        logger.warning(f"Resetting index {self.collection_name}...")
        self.delete_col()
        self.create_col(self.collection_name, self.embedding_model_dims, self.metric_type)
