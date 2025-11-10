from loguru import logger
import os
import shutil
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, Field, model_validator

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    Range,
    VectorParams,
)

from mem.vector_stores.base import VectorStoreBase


class QdrantConfig(BaseModel):
    from qdrant_client import QdrantClient

    QdrantClient: ClassVar[type] = QdrantClient

    collection_name: str = Field("mem0", description="Name of the collection")
    embedding_model_dims: Optional[int] = Field(1536, description="Dimensions of the embedding model")
    client: Optional[QdrantClient] = Field(None, description="Existing Qdrant client instance")
    host: Optional[str] = Field(None, description="Host address for Qdrant server")
    port: Optional[int] = Field(None, description="Port for Qdrant server")
    path: Optional[str] = Field("/tmp/qdrant", description="Path for local Qdrant database")
    url: Optional[str] = Field(None, description="Full URL for Qdrant server")
    api_key: Optional[str] = Field(None, description="API key for Qdrant server")
    on_disk: Optional[bool] = Field(False, description="Enables persistent storage")


    @model_validator(mode="before")
    @classmethod
    def check_host_port_or_path(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        host, port, path, url, api_key = (
            values.get("host"),
            values.get("port"),
            values.get("path"),
            values.get("url"),
            values.get("api_key"),
        )
        if not path and not (host and port) and not (url and api_key):
            raise ValueError("Either 'host' and 'port' or 'url' and 'api_key' or 'path' must be provided.")
        return values


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


class Qdrant(VectorStoreBase):
    def __init__(
        self,
        collection_name: str,
        embedding_model_dims: int,
        client: QdrantClient = None,
        host: str = None,
        port: int = None,
        path: str = None,
        url: str = None,
        api_key: str = None,
        on_disk: bool = False,
    ):
        """
        Initialize the Qdrant vector store.

        Args:
            collection_name (str): Name of the collection.
            embedding_model_dims (int): Dimensions of the embedding model.
            client (QdrantClient, optional): Existing Qdrant client instance. Defaults to None.
            host (str, optional): Host address for Qdrant server. Defaults to None.
            port (int, optional): Port for Qdrant server. Defaults to None.
            path (str, optional): Path for local Qdrant database. Defaults to None.
            url (str, optional): Full URL for Qdrant server. Defaults to None.
            api_key (str, optional): API key for Qdrant server. Defaults to None.
            on_disk (bool, optional): Enables persistent storage. Defaults to False.
        """
        if client:
            self.client = client
        else:
            params = {}
            if api_key:
                params["api_key"] = api_key
            if url:
                params["url"] = url
            if host and port:
                params["host"] = host
                params["port"] = port
            if not params:
                params["path"] = path
                if not on_disk:
                    if os.path.exists(path) and os.path.isdir(path):
                        shutil.rmtree(path)

            self.client = QdrantClient(**params)

        self.collection_name = collection_name
        self.embedding_model_dims = embedding_model_dims
        self.on_disk = on_disk
        self.create_col(self.embedding_model_dims, self.on_disk)

    def create_col(self, vector_size: int, on_disk: bool, distance: Distance = Distance.COSINE):
        """
        Create a new collection.

        Args:
            vector_size (int): Size of the vectors to be stored.
            on_disk (bool): Enables persistent storage.
            distance (Distance, optional): Distance metric for vector similarity. Defaults to Distance.COSINE.
        """
        # Skip creating collection if already exists
        response = self.list_cols()
        for collection in response.collections:
            if collection.name == self.collection_name:
                logger.debug(f"Collection {self.collection_name} already exists. Skipping creation.")
                return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance, on_disk=on_disk),
        )

    def insert(self, vectors: list, payloads: list = None, ids: list = None, **kwargs: Optional[dict[str, any]]):
        """
        Insert vectors into a collection.

        Args:
            vectors (list): List of vectors to insert.
            payloads (list, optional): List of payloads corresponding to vectors. Defaults to None.
            ids (list, optional): List of IDs corresponding to vectors. Defaults to None.
        """
        logger.info(f"Inserting {len(vectors)} vectors into collection {self.collection_name}")
        points = [
            PointStruct(
                id=idx if ids is None else ids[idx],
                vector=vector,
                payload=payloads[idx] if payloads else {},
            )
            for idx, vector in enumerate(vectors)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def _create_filter(self, filters: dict) -> Filter:
        """
        Create a Filter object from the provided filters.

        Args:
            filters (dict): Filters to apply.

        Returns:
            Filter: The created Filter object.
        """
        conditions = []
        for key, value in filters.items():
            if isinstance(value, dict) and "gte" in value and "lte" in value:
                conditions.append(FieldCondition(key=key, range=Range(gte=value["gte"], lte=value["lte"])))
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=conditions) if conditions else None

    def search(self, query: str, vectors: list, limit: int = 5, filters: dict = None, threshold: float = 0.4) -> list:
        """
        Search for similar vectors.

        Args:

            query (str): Query
            vectors (list): Query vector.
            limit (int, optional): Number of results to return. Defaults to 5.
            filters (dict, optional): Filters to apply to the search. Defaults to None.
            threshold: score_threshold

        Returns:
            list: Search results.
        """
        query_filter = self._create_filter(filters) if filters else None
        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=vectors,
            query_filter=query_filter,
            score_threshold=threshold,
            limit=limit,
        )
        return hits.points

    def delete(self, vector_id: int):
        """
        Delete a vector by ID.

        Args:
            vector_id (int): ID of the vector to delete.
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(
                points=[vector_id],
            ),
        )

    def update(self, vector_id: int, vector: list = None, payload: dict = None):
        """
        Update a vector and its payload.

        Args:
            vector_id (int): ID of the vector to update.
            vector (list, optional): Updated vector. Defaults to None.
            payload (dict, optional): Updated payload. Defaults to None.
        """
        point = PointStruct(id=vector_id, vector=vector, payload=payload)
        self.client.upsert(collection_name=self.collection_name, points=[point])

    def get(self, vector_id: int) -> dict:
        """
        Retrieve a vector by ID.

        Args:
            vector_id (int): ID of the vector to retrieve.

        Returns:
            dict: Retrieved vector.
        """
        result = self.client.retrieve(collection_name=self.collection_name, ids=[vector_id], with_payload=True)
        return result[0] if result else None

    def list_cols(self) -> list:
        """
        List all collections.

        Returns:
            list: List of collection names.
        """
        return self.client.get_collections()

    def delete_col(self):
        """Delete a collection."""
        self.client.delete_collection(collection_name=self.collection_name)

    def col_info(self) -> dict:
        """
        Get information about a collection.

        Returns:
            dict: Collection information.
        """
        return self.client.get_collection(collection_name=self.collection_name)

    def list(self, filters: dict = None, limit: int = 100) -> list:
        """
        List all vectors in a collection.

        Args:
            filters (dict, optional): Filters to apply to the list. Defaults to None.
            limit (int, optional): Number of vectors to return. Defaults to 100.

        Returns:
            list: List of vectors.
        """
        query_filter = self._create_filter(filters) if filters else None
        result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return result[0]

    def reset(self):
        """Reset the index by deleting and recreating it."""
        logger.warning(f"Resetting index {self.collection_name}...")
        self.delete_col()
        self.create_col(self.embedding_model_dims, self.on_disk)
