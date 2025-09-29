import concurrent
import hashlib
import json
import os
import time
import uuid
import warnings
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Optional
from loguru import logger
import pytz
from pydantic import ValidationError

from mem.memory.configs import MemoryConfig, MemoryItem, mem0_dir
from mem.com.enums import MemoryType
from mem.vector_stores.prompts import (
    get_update_memory_messages,
    SUMMARY_SYSTEM_PROMPT

)
from mem.memory.base import MemoryBase

from mem.memory.utils import (
    get_fact_retrieval_messages,
    get_profile_retrieval_messages,
    parse_messages,
    parse_vision_messages,
    remove_code_blocks,
)
from mem.com.factory import EmbedderFactory, LlmFactory, VectorStoreFactory

RUN_MODE = os.getenv("RUN_MODE", 'info')

def _build_filters_and_metadata(
    *,  # Enforce keyword-only arguments
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    actor_id: Optional[str] = None,  # For query-time filtering
    input_metadata: Optional[Dict[str, Any]] = None,
    input_filters: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Constructs metadata for storage and filters for querying based on session and actor identifiers.

    This helper ties every memory/query to exactly one session id (`user_id`, `agent_id`, or `run_id`) and optionally narrows queries to a specific `actor_id`.  It returns two dicts:


    1. `base_metadata_template`: Used as a template for metadata when storing new memories.
       It includes the primary session identifier(s) and any `input_metadata`.
    2. `effective_query_filters`: Used for querying existing memories. It includes the
       primary session identifier(s), any `input_filters`, and a resolved actor
       identifier for targeted filtering if specified by any actor-related inputs.

    Actor filtering precedence: explicit `actor_id` arg → `filters["actor_id"]`
    This resolved actor ID is used for querying but is not added to `base_metadata_template`,
    as the actor for storage is typically derived from message content at a later stage.

    Args:
        user_id (Optional[str]): User identifier, primarily for Classic Mode session scoping.
        agent_id (Optional[str]): Agent identifier, for Classic Mode session scoping or
            as auxiliary information in Group Mode.
        run_id (Optional[str]): Run identifier, for Classic Mode session scoping or
            as auxiliary information in Group Mode.
        actor_id (Optional[str]): Explicit actor identifier, used as a potential source for
            actor-specific filtering. See actor resolution precedence in the main description.
        input_metadata (Optional[Dict[str, Any]]): Base dictionary to be augmented with
            session identifiers for the storage metadata template. Defaults to an empty dict.
        input_filters (Optional[Dict[str, Any]]): Base dictionary to be augmented with
            session and actor identifiers for query filters. Defaults to an empty dict.

    Returns:
        tuple[Dict[str, Any], Dict[str, Any]]: A tuple containing:
            - base_metadata_template (Dict[str, Any]): Metadata template for storing memories,
              scoped to the determined session.
            - effective_query_filters (Dict[str, Any]): Filters for querying memories,
              scoped to the determined session and potentially a resolved actor.
    """

    base_metadata_template = deepcopy(input_metadata) if input_metadata else {}
    effective_query_filters = deepcopy(input_filters) if input_filters else {}

    if user_id:
        effective_query_filters["user_id"] = base_metadata_template["user_id"] = user_id
    if agent_id:
        effective_query_filters["agent_id"] = base_metadata_template["agent_id"] = agent_id
    if run_id:
        effective_query_filters["run_id"] = base_metadata_template["run_id"] = run_id

    if not any(key in effective_query_filters for key in ("user_id", "agent_id", "run_id")):
        raise ValueError("One of the filters: user_id, agent_id or run_id is required!")

    return base_metadata_template, effective_query_filters


class Memory(MemoryBase):
    def __init__(self, config: MemoryConfig = MemoryConfig()):
        self.config = config

        self.custom_fact_extraction_prompt = self.config.custom_fact_extraction_prompt
        self.custom_update_memory_prompt = self.config.custom_update_memory_prompt
        self.embedding_model = EmbedderFactory.create(
            self.config.embedder.provider,
            self.config.embedder.config,
            self.config.vector_store.config,
        )
        self.vector_store = VectorStoreFactory.create(
            self.config.vector_store.provider, self.config.vector_store.config
        )
        self.llm = LlmFactory.create(self.config.llm.provider, self.config.llm.config)
        self.collection_name = self.config.vector_store.config.collection_name
        self.api_version = self.config.version

        self.enable_graph = False

        if self.config.graph_store.config:
            if self.config.graph_store.provider == "memgraph":
                from mem.graphs.memgraph_memory import MemoryGraph
            else:
                from mem.graphs.graph_memory import MemoryGraph

            self.graph = MemoryGraph(self.config)
            self.enable_graph = True
        else:
            self.graph = None

    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]):
        try:
            config = cls._process_config(config_dict)
            config = MemoryConfig(**config_dict)
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        return cls(config)

    @staticmethod
    def _process_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        if "graph_store" in config_dict:
            if "vector_store" not in config_dict and "embedder" in config_dict:
                config_dict["vector_store"] = {}
                config_dict["vector_store"]["config"] = {}
                config_dict["vector_store"]["config"]["embedding_model_dims"] = config_dict["embedder"]["config"][
                    "embedding_dims"
                ]
        try:
            return config_dict
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise

    def memory_post_process(self, memory):
        return memory.replace('用户', '玩家').replace('user', '玩家').replace('助手', 'NPC').replace('assistant', 'NPC')

    def _create_summary(
            self,
            messages,
            sid=None,
            user_id=None,
            agent_id=None,
            run_id=None,
            metadata=None,
            filters=None,
            prompt=None,
    ):
        """
        Create a session summary.

        Args:
            messages (str or List[Dict[str, str]]): Messages to store in the memory.
            sid (str, optional): ID of the request. Default to None.
            user_id (str, optional): ID of the user creating the memory. Defaults to None.
            agent_id (str, optional): ID of the agent creating the memory. Defaults to None.
            run_id (str, optional): ID of the run creating the memory. Defaults to None.
            metadata (dict, optional): Metadata to store with the memory. Defaults to None.
            filters (dict, optional): Filters to apply to the search. Defaults to None.
            prompt (str, optional): Prompt to use for memory deduction. Defaults to None.

        Returns:
            dict: A dictionary containing the result of the session summary.
            result: str, session summary


        """
        if metadata is None:
            metadata = {}
        metadata["type"] = "summary"

        filters = filters or {}
        if user_id:
            filters["user_id"] = metadata["user_id"] = user_id
        if agent_id:
            filters["agent_id"] = metadata["agent_id"] = agent_id
        if run_id:
            filters["run_id"] = metadata["run_id"] = run_id

        if not any(key in filters for key in ("user_id", "agent_id", "run_id")):
            raise ValueError("One of the filters: user_id, agent_id or run_id is required!")

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        messages = parse_vision_messages(messages)
        parsed_messages = parse_messages(messages)

        summary_prompt = SUMMARY_SYSTEM_PROMPT if prompt is None else prompt
        messages = [{"role": "system", "content": summary_prompt},
                    {"role": "user", "content": parsed_messages}]

        response = self.llm.generate_response(
            messages=messages,
            response_format={"type": "json_object"},
        )
        summary_info = dict(messages=messages, response=response, type='summary')
        logger.info(f'{sid} | summary:{json.dumps(summary_info, ensure_ascii=False)}')

        logger.info(f"{sid} | _create_summary | summary result: {response}")

        try:
            response = remove_code_blocks(response)
            summary_result = json.loads(response)
        except Exception as e:
            logger.exception(f"{sid} | Error in new_retrieved_facts: {e}")
            summary_result = {}

        # save to vec
        new_mem = self.memory_post_process(summary_result.get("summary", ''))
        if len(new_mem) > 0:
            metadata.update(**summary_result)
            memory_id = self._create_memory(data=new_mem, existing_embeddings={}, metadata=metadata)
            summary_result.update({"id": memory_id})

        return {"result": summary_result}

    def add(
        self,
        messages,
        *,   # 表示位置参数后的所有参数必须通过关键字传递
        sid: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True,
        memory_type: Optional[str] = "vector",
        prompt: Optional[str] = None,
    ):
        """
        Create a new memory.

        Adds new memories scoped to a single session id (e.g. `user_id`, `agent_id`, or `run_id`). One of those ids is required.

        Args:
            messages (str or List[Dict[str, str]]): The message content or list of messages
                (e.g., `[{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]`)
                to be processed and stored.
            sid(str, optional): ID of the request. Default to None.
            user_id (str, optional): ID of the user creating the memory. Defaults to None.
            agent_id (str, optional): ID of the agent creating the memory. Defaults to None.
            run_id (str, optional): ID of the run creating the memory. Defaults to None.
            metadata (dict, optional): Metadata to store with the memory. Defaults to None.
            infer (bool, optional): If True (default), an LLM is used to extract key facts from
                'messages' and decide whether to add, update, or delete related memories.
                If False, 'messages' are added as raw memories directly.
            memory_type (str, optional): Specifies the type of memory. Currently, "default", "vector", "graph", "summary"
            prompt (str, optional): Prompt to use for the memory creation. Defaults to None.


        Returns:
            dict: A dictionary containing the result of the memory addition operation, typically
                  including a list of memory items affected (added, updated) under a "results" key,
                  and potentially "relations" if graph store is enabled.
                  Example for v1.1+: `{"results": [{"id": "...", "memory": "...", "event": "ADD"}]}`
        """

        processed_metadata, effective_filters = _build_filters_and_metadata(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            input_metadata=metadata,
        )

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        elif isinstance(messages, dict):
            messages = [messages]

        elif not isinstance(messages, list):
            raise ValueError("messages must be str, dict, or list[dict]")

        # 不同的记忆类型
        if memory_type not in MemoryType.ENUMS.value:
            raise ValueError(
                f"Invalid 'memory_type'. Please pass one of the [{MemoryType.ENUMS.value}]"
            )
        if memory_type == MemoryType.SUMMARY.value:
            results = self._create_summary(messages, sid=sid, user_id=user_id, agent_id=agent_id, run_id=run_id,
                                           metadata=processed_metadata, filters=effective_filters, prompt=prompt)
            return results

        if memory_type == MemoryType.VECTOR.value:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future1 = executor.submit(self._add_to_vector_store, messages, processed_metadata, effective_filters, infer, "profile", sid)
                future2 = executor.submit(self._add_to_vector_store, messages, processed_metadata, effective_filters, infer, "facts", sid)

                concurrent.futures.wait([future1, future2])
                profile_result = future1.result()
                facts_result = future2.result()
            results = profile_result + facts_result
            return {"results": results}

        if memory_type == MemoryType.GRAPH.value:
            results = self._add_to_graph(messages=messages, filters=effective_filters)
            return {"relations": results}

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(self._add_to_vector_store, messages, processed_metadata, effective_filters, infer)
            future2 = executor.submit(self._add_to_graph, messages, effective_filters)

            concurrent.futures.wait([future1, future2])

            vector_store_result = future1.result()
            graph_result = future2.result()

        if self.api_version == "v1.0":
            warnings.warn(
                "The current add API output format is deprecated. "
                "To use the latest format, set `api_version='v1.1'`. "
                "The current format will be removed in mem0ai 1.1.0 and later versions.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return vector_store_result

        if self.enable_graph:
            return {
                "results": vector_store_result,
                "relations": graph_result,
            }

        return {"results": vector_store_result}

    def _add_to_vector_store(self, messages, metadata, filters, infer=True, mtype="profile", sid=None):
        if not infer:
            """原始文本，直接写入."""
            returned_memories = []
            for message_dict in messages:
                if (
                    not isinstance(message_dict, dict)
                    or message_dict.get("role") is None
                    or message_dict.get("content") is None
                ):
                    logger.warning(f"{sid} | extract | Skipping invalid message format: {message_dict}")
                    continue

                if message_dict["role"] == "system":
                    continue

                per_msg_meta = deepcopy(metadata)
                per_msg_meta["role"] = message_dict["role"]

                actor_name = message_dict.get("name")
                if actor_name:
                    per_msg_meta["actor_id"] = actor_name

                msg_content = message_dict["content"]
                msg_embeddings = self.embedding_model.embed(msg_content, "add")
                mem_id = self._create_memory(msg_content, msg_embeddings, per_msg_meta)

                returned_memories.append(
                    {
                        "id": mem_id,
                        "memory": msg_content,
                        "event": "ADD",
                        "actor_id": actor_name if actor_name else None,
                        "role": message_dict["role"],
                    }
                )
            return returned_memories

        parsed_messages = parse_messages(messages)
        metadata = deepcopy(metadata)
        filters = deepcopy(filters)
        filters["type"] = mtype
        metadata["type"] = mtype

        if self.config.custom_fact_extraction_prompt:
            system_prompt = self.config.custom_fact_extraction_prompt
            user_prompt = f"Input:\n{parsed_messages}"
        elif mtype == 'facts':
            system_prompt, user_prompt = get_fact_retrieval_messages(parsed_messages)
        else:
            system_prompt, user_prompt = get_profile_retrieval_messages(parsed_messages)

        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}]
        response = self.llm.generate_response(
            messages=messages,
            response_format={"type": "json_object"},
        )
        if RUN_MODE == "debug":
            extract_info = dict(messages=messages, response=response, type='extract')
            logger.info(f'{sid} | extract:{json.dumps(extract_info, ensure_ascii=False)}')
        logger.info(f"{sid} | extract {mtype} result: {response}")

        try:
            response = remove_code_blocks(response)
            new_retrieved_facts = [self.memory_post_process(x) for x in json.loads(response)["memories"]]
        except Exception as e:
            logger.exception(f"Error in new_retrieved_facts: {e}")
            new_retrieved_facts = []

        retrieved_old_memory = []
        new_message_embeddings = {}
        for new_mem in new_retrieved_facts:
            messages_embeddings = self.embedding_model.embed(new_mem, "add")
            new_message_embeddings[new_mem] = messages_embeddings
            existing_memories = self.vector_store.search(
                query=new_mem,
                vectors=messages_embeddings,
                limit=3,
                filters=filters,
                threshold=0.6
            )
            for mem in existing_memories:
                if mem.payload["type"] == mtype:
                    retrieved_old_memory.append({"id": mem.id, "text": mem.payload["data"]})

        unique_data = {}
        for item in retrieved_old_memory:
            unique_data[item["id"]] = item
        retrieved_old_memory = list(unique_data.values())
        logger.info(f"{sid} | extract | Total existing memories: {len(retrieved_old_memory)}")

        # mapping UUIDs with integers for handling UUID hallucinations
        temp_uuid_mapping = {}
        for idx, item in enumerate(retrieved_old_memory):
            temp_uuid_mapping[str(idx)] = item["id"]
            retrieved_old_memory[idx]["id"] = str(idx)
        logger.info(
            f"{sid} | extract | update info: {json.dumps(dict(exist_mem=retrieved_old_memory, new_mem=new_retrieved_facts), ensure_ascii=False)}")
        # update
        new_memories_with_actions = {"memory": []}
        if new_retrieved_facts:
            function_calling_prompt = get_update_memory_messages(retrieved_old_memory, new_retrieved_facts, mtype)

            try:
                response: str = self.llm.generate_response(
                    messages=[{"role": "user", "content": function_calling_prompt}],
                    response_format={"type": "json_object"},
                )
                if RUN_MODE == "debug":
                    update_info = dict(messages=[{"role": "user", "content": function_calling_prompt}], response=response, type='update')
                    logger.info(f'{sid} | extract | update:{json.dumps(update_info, ensure_ascii=False)}')
            except Exception as e:
                logger.error(f"{sid} | extract | Error in new memory actions response: {e}")
                response = ""

            try:
                response = remove_code_blocks(response)
                new_memories_with_actions = json.loads(response)
            except Exception as e:
                logger.error(f"{sid} | extract | Invalid JSON response: {e}")
                new_memories_with_actions = {}
        update_result = dict(exist_mem=retrieved_old_memory, new_mem=new_retrieved_facts,
                             update=new_memories_with_actions)
        logger.info(f"{sid} | update result:{json.dumps(update_result, ensure_ascii=False)}")

        returned_memories = []
        try:
            for resp in new_memories_with_actions.get("memory", []):
                # logger.info(resp)
                try:
                    action_text = resp.get("text")
                    if not action_text:
                        logger.info(f"{sid} | extract | Skipping memory entry because of empty `text` field.")
                        continue

                    event_type = resp.get("event")
                    if event_type == "ADD":
                        memory_id = self._create_memory(
                            data=action_text,
                            existing_embeddings=new_message_embeddings,
                            metadata=deepcopy(metadata),
                        )
                        returned_memories.append({"id": memory_id, "memory": action_text, "event": event_type, "type": mtype})
                    elif event_type == "UPDATE":
                        self._update_memory(
                            memory_id=temp_uuid_mapping[resp.get("id")],
                            data=action_text,
                            existing_embeddings=new_message_embeddings,
                            metadata=deepcopy(metadata),
                        )
                        returned_memories.append(
                            {
                                "id": temp_uuid_mapping[resp.get("id")],
                                "memory": action_text,
                                "type": mtype,
                                "event": event_type,
                                "previous_memory": resp.get("old_memory"),
                            }
                        )
                    elif event_type == "DELETE":
                        self._delete_memory(memory_id=temp_uuid_mapping[resp.get("id")])
                        returned_memories.append(
                            {
                                "id": temp_uuid_mapping[resp.get("id")],
                                "memory": action_text,
                                "event": event_type,
                                "type": mtype
                            }
                        )
                    elif event_type == "NONE":
                        logger.info(f"{sid} | extract | NOOP for Memory.")
                except Exception as e:
                    logger.error(f"{sid} | extract | Error processing memory action: {resp}, Error: {e}")
        except Exception as e:
            logger.error(f"{sid} | extract | Error iterating new_memories_with_actions: {e}")

        return returned_memories

    def _add_to_graph(self, messages, filters):
        added_entities = []
        if self.enable_graph:
            if filters.get("user_id") is None:
                filters["user_id"] = "user"

            data = "\n".join([msg["content"] for msg in messages if "content" in msg and msg["role"] != "system"])
            added_entities = self.graph.add(data, filters)

        return added_entities

    def get(self, memory_id):
        """
        Retrieve a memory by ID.

        Args:
            memory_id (str): ID of the memory to retrieve.

        Returns:
            dict: Retrieved memory.
        """
        memory = self.vector_store.get(vector_id=memory_id)
        if not memory:
            return None

        promoted_payload_keys = [
            "user_id",
            "agent_id",
            "run_id",
            "actor_id",
            "role",
        ]

        core_and_promoted_keys = {"data", "hash", "created_at", "updated_at", "id", *promoted_payload_keys}

        result_item = MemoryItem(
            id=memory.id,
            memory=memory.payload["data"],
            hash=memory.payload.get("hash"),
            created_at=memory.payload.get("created_at"),
            updated_at=memory.payload.get("updated_at"),
        ).model_dump()

        for key in promoted_payload_keys:
            if key in memory.payload:
                result_item[key] = memory.payload[key]

        additional_metadata = {k: v for k, v in memory.payload.items() if k not in core_and_promoted_keys}
        if additional_metadata:
            result_item["metadata"] = additional_metadata

        return result_item

    def get_all(
        self,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ):
        """
        List all memories.

        Args:
            user_id (str, optional): user id
            agent_id (str, optional): agent id
            run_id (str, optional): run id
            filters (dict, optional): Additional custom key-value filters to apply to the search.
                These are merged with the ID-based scoping filters. For example,
                `filters={"actor_id": "some_user"}`.
            limit (int, optional): The maximum number of memories to return. Defaults to 100.

        Returns:
            dict: A dictionary containing a list of memories under the "results" key,
                  and potentially "relations" if graph store is enabled. For API v1.0,
                  it might return a direct list (see deprecation warning).
                  Example for v1.1+: `{"results": [{"id": "...", "memory": "...", ...}]}`
        """

        _, effective_filters = _build_filters_and_metadata(
            user_id=user_id, agent_id=agent_id, run_id=run_id, input_filters=filters
        )

        if not any(key in effective_filters for key in ("user_id", "agent_id", "run_id")):
            raise ValueError("At least one of 'user_id', 'agent_id', or 'run_id' must be specified.")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_memories = executor.submit(self._get_all_from_vector_store, effective_filters, limit)
            future_graph_entities = (
                executor.submit(self.graph.get_all, effective_filters, limit) if self.enable_graph else None
            )

            concurrent.futures.wait(
                [future_memories, future_graph_entities] if future_graph_entities else [future_memories]
            )

            all_memories_result = future_memories.result()
            graph_entities_result = future_graph_entities.result() if future_graph_entities else None

        if self.enable_graph:
            return {"results": all_memories_result, "relations": graph_entities_result}

        if self.api_version == "v1.0":
            warnings.warn(
                "The current get_all API output format is deprecated. "
                "To use the latest format, set `api_version='v1.1'` (which returns a dict with a 'results' key). "
                "The current format (direct list for v1.0) will be removed in mem0ai 1.1.0 and later versions.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return all_memories_result
        else:
            return {"results": all_memories_result}

    def _get_all_from_vector_store(self, filters, limit, sid=None):
        t0 = time.time()
        memories_result = self.vector_store.list(filters=filters, limit=limit)
        actual_memories = (
            memories_result[0] if isinstance(memories_result, tuple) and len(memories_result) > 0 else memories_result
        )

        promoted_payload_keys = [
            "user_id",
            "agent_id",
            "run_id",
            "actor_id",
            "role",
        ]
        core_and_promoted_keys = {"data", "hash", "created_at", "updated_at", "id", *promoted_payload_keys}

        formatted_memories = []
        for mem in actual_memories:
            memory_item_dict = MemoryItem(
                id=mem.id,
                memory=mem.payload["data"],
                hash=mem.payload.get("hash"),
                created_at=mem.payload.get("created_at"),
                updated_at=mem.payload.get("updated_at"),
            ).model_dump(exclude={"score"})

            for key in promoted_payload_keys:
                if key in mem.payload:
                    memory_item_dict[key] = mem.payload[key]

            additional_metadata = {k: v for k, v in mem.payload.items() if k not in core_and_promoted_keys}
            if additional_metadata:
                memory_item_dict["metadata"] = additional_metadata

            formatted_memories.append(memory_item_dict)
        t1 = time.time()
        logger.info(f'{sid} | _get_all_from_vector_store | time_cost:{round(t1 - t0, 2)}s')
        return formatted_memories

    def search(
        self,
        query: str,
        *,
        sid: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """
        Searches for memories based on a query
        Args:
            query (str): Query to search for.
            sid (str, optional): ID of the request. Default to None.
            user_id (str, optional): ID of the user to search for. Defaults to None.
            agent_id (str, optional): ID of the agent to search for. Defaults to None.
            run_id (str, optional): ID of the run to search for. Defaults to None.
            limit (int, optional): Limit the number of results. Defaults to 100.
            filters (dict, optional): Filters to apply to the search. Defaults to None..

        Returns:
            dict: A dictionary containing the search results, typically under a "results" key,
                  and potentially "relations" if graph store is enabled.
                  Example for v1.1+: `{"results": [{"id": "...", "memory": "...", "score": 0.8, ...}]}`
        """
        _, effective_filters = _build_filters_and_metadata(
            user_id=user_id, agent_id=agent_id, run_id=run_id, input_filters=filters
        )

        if not any(key in effective_filters for key in ("user_id", "agent_id", "run_id")):
            raise ValueError("At least one of 'user_id', 'agent_id', or 'run_id' must be specified.")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_memories = executor.submit(self._search_vector_store, query, effective_filters, limit)
            future_graph_entities = (
                executor.submit(self.graph.search, query, effective_filters, limit) if self.enable_graph else None
            )

            concurrent.futures.wait(
                [future_memories, future_graph_entities] if future_graph_entities else [future_memories]
            )

            original_memories = future_memories.result()
            graph_entities = future_graph_entities.result() if future_graph_entities else None

        if self.enable_graph:
            return {"results": original_memories, "relations": graph_entities}

        if self.api_version == "v1.0":
            warnings.warn(
                "The current search API output format is deprecated. "
                "To use the latest format, set `api_version='v1.1'`. "
                "The current format will be removed in mem0ai 1.1.0 and later versions.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return {"results": original_memories}
        else:
            return {"results": original_memories}

    def _search_vector_store(self, query, filters, limit):
        embeddings = self.embedding_model.embed(query, "search")
        memories = self.vector_store.search(query=query, vectors=embeddings, limit=limit, filters=filters)

        promoted_payload_keys = [
            "user_id",
            "agent_id",
            "run_id",
            "actor_id",
            "role",
        ]

        core_and_promoted_keys = {"data", "hash", "created_at", "updated_at", "id", *promoted_payload_keys}

        original_memories = []
        for mem in memories:
            memory_item_dict = MemoryItem(
                id=mem.id,
                memory=mem.payload["data"],
                hash=mem.payload.get("hash"),
                created_at=mem.payload.get("created_at"),
                updated_at=mem.payload.get("updated_at"),
                score=mem.score,
            ).model_dump()

            for key in promoted_payload_keys:
                if key in mem.payload:
                    memory_item_dict[key] = mem.payload[key]

            additional_metadata = {k: v for k, v in mem.payload.items() if k not in core_and_promoted_keys}
            if additional_metadata:
                memory_item_dict["metadata"] = additional_metadata

            original_memories.append(memory_item_dict)

        return original_memories

    def update(self, memory_id, data):
        """
        Update a memory by ID.

        Args:
            memory_id (str): ID of the memory to update.
            data (dict): Data to update the memory with.

        Returns:
            dict: Updated memory.
        """
        existing_embeddings = {data: self.embedding_model.embed(data, "update")}

        self._update_memory(memory_id, data, existing_embeddings)
        return {"message": "Memory updated successfully!"}

    def delete(self, memory_id):
        """
        Delete a memory by ID.

        Args:
            memory_id (str): ID of the memory to delete.
        """
        self._delete_memory(memory_id)
        return {"message": "Memory deleted successfully!"}

    def delete_all(self, user_id: Optional[str] = None, agent_id: Optional[str] = None, run_id: Optional[str] = None):
        """
        Delete all memories.

        Args:
            user_id (str, optional): ID of the user to delete memories for. Defaults to None.
            agent_id (str, optional): ID of the agent to delete memories for. Defaults to None.
            run_id (str, optional): ID of the run to delete memories for. Defaults to None.
        """
        filters: Dict[str, Any] = {}
        if user_id:
            filters["user_id"] = user_id
        if agent_id:
            filters["agent_id"] = agent_id
        if run_id:
            filters["run_id"] = run_id

        if not filters:
            raise ValueError(
                "At least one filter is required to delete all memories. If you want to delete all memories, use the `reset()` method."
            )

        memories = self.vector_store.list(filters=filters)
        for memory in memories:
            self._delete_memory(memory.id)

        logger.info(f"Deleted {len(memories)} memories")

        if self.enable_graph:
            self.graph.delete_all(filters)

        return {"message": "Memories deleted successfully!"}

    def history(self, memory_id):
        """
        Get the history of changes for a memory by ID.

        Args:
            memory_id (str): ID of the memory to get history for.

        Returns:
            list: List of changes for the memory.
        """
        pass

    def _create_memory(self, data, existing_embeddings, metadata=None):
        # logger.debug(f"Creating memory with {data=}")
        if data in existing_embeddings:
            embeddings = existing_embeddings[data]
        else:
            embeddings = self.embedding_model.embed(data, memory_action="add")
        memory_id = str(uuid.uuid4())
        metadata = metadata or {}
        metadata["data"] = data
        metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
        metadata["created_at"] = datetime.now(pytz.timezone("US/Pacific")).isoformat()

        self.vector_store.insert(
            vectors=[embeddings],
            ids=[memory_id],
            payloads=[metadata],
        )
        return memory_id

    def _update_memory(self, memory_id, data, existing_embeddings, metadata=None):
        logger.info(f"Updating memory with {data=}")

        try:
            existing_memory = self.vector_store.get(vector_id=memory_id)
        except Exception:
            logger.error(f"Error getting memory with ID {memory_id} during update.")
            raise ValueError(f"Error getting memory with ID {memory_id}. Please provide a valid 'memory_id'")

        prev_value = existing_memory.payload.get("data")

        new_metadata = deepcopy(metadata) if metadata is not None else {}

        new_metadata["data"] = data
        new_metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
        new_metadata["created_at"] = existing_memory.payload.get("created_at")
        new_metadata["updated_at"] = datetime.now(pytz.timezone("US/Pacific")).isoformat()

        if "user_id" in existing_memory.payload:
            new_metadata["user_id"] = existing_memory.payload["user_id"]
        if "agent_id" in existing_memory.payload:
            new_metadata["agent_id"] = existing_memory.payload["agent_id"]
        if "run_id" in existing_memory.payload:
            new_metadata["run_id"] = existing_memory.payload["run_id"]
        if "actor_id" in existing_memory.payload:
            new_metadata["actor_id"] = existing_memory.payload["actor_id"]
        if "role" in existing_memory.payload:
            new_metadata["role"] = existing_memory.payload["role"]

        if data in existing_embeddings:
            embeddings = existing_embeddings[data]
        else:
            embeddings = self.embedding_model.embed(data, "update")

        self.vector_store.update(
            vector_id=memory_id,
            vector=embeddings,
            payload=new_metadata,
        )
        logger.info(f"Updating memory with ID {memory_id=} with {data=}")

        return memory_id

    def _delete_memory(self, memory_id):
        logger.info(f"Deleting memory with {memory_id=}")
        existing_memory = self.vector_store.get(vector_id=memory_id)
        prev_value = existing_memory.payload["data"]
        self.vector_store.delete(vector_id=memory_id)

        return memory_id

    def reset(self):
        """
        Reset the memory store by:
            Deletes the vector store collection
            Resets the database
            Recreates the vector store with a new client
        """
        logger.warning("Resetting all memories")

        if hasattr(self.vector_store, "reset"):
            self.vector_store = VectorStoreFactory.reset(self.vector_store)
        else:
            logger.warning("Vector store does not support reset. Skipping.")
            self.vector_store.delete_col()
            self.vector_store = VectorStoreFactory.create(
                self.config.vector_store.provider, self.config.vector_store.config
            )

    def chat(self, query):
        raise NotImplementedError("Chat function not implemented yet.")


