
import time
import json
import requests
import re
from loguru import logger

SERVER_BASE_URL = 'http://localhost:8000/'
add_url = SERVER_BASE_URL + 'add'
search_url = SERVER_BASE_URL + 'search'
get_memories_url = SERVER_BASE_URL + 'memories'
delete_memories_url = SERVER_BASE_URL + 'memories'


def add(agent_id, user_id, messages, memory_type):
    query_json = {
        "agent_id": agent_id,
        "user_id": user_id,
        "messages": messages,
        "memory_type": memory_type
    }
    try:
        t_start = time.time()
        res = requests.post(add_url, json=query_json, headers={"Content-Type": "application/json"}, timeout=30)
        if res.status_code != 200:
            raise Exception(f'mem server error:{res.text}')
        result = json.loads(res.text)
        logger.info(f'add result|{result}, cost|{round(time.time() - t_start, 3)}s')
    except Exception as e:
        result = None
        logger.exception(f'MemoryMgr::add|error:{str(e)}')
    return result


def search(agent_id, user_id, query):
    query_json = {
        "agent_id": agent_id,
        "user_id": user_id,
        "query": query
    }
    results = []
    try:
        t_start = time.time()
        res = requests.post(search_url, json=query_json, headers={"Content-Type": "application/json"}, timeout=5)
        if res.status_code != 200:
            raise Exception(f'mem server error search:{res.text}')

        temp = json.loads(res.text)
        print(json.dumps(temp, ensure_ascii=False, indent=4))

        vec_results = json.loads(res.text).get('results', [])
        for item in vec_results:
            memory = item.get('memory', '')
            if len(memory) > 0:
                memory = memory.replace('用户', '玩家')
                results.append(memory)
        logger.info(f'search result|{results}, cost|{round(time.time() - t_start, 3)}s')

    except Exception as e:
        logger.exception(f'MemoryMgr::search|error:{str(e)}')
    return results


def _unify_name(text):
    """统一替换--user/用户-> 玩家； 助手/assistant -> NPC"""

    text = re.sub(r'用户|user', '玩家', text)
    text = re.sub(r'助手|assistant', 'NPC', text)
    return text


def get_memories(user_id):
    results = {}
    try:
        query_json = {'user_id': user_id}
        res = requests.get(get_memories_url, params=query_json, headers={"Content-Type": "application/json"},
                           timeout=20)

        temp = json.loads(res.text)
        print(json.dumps(temp, ensure_ascii=False, indent=4))

        vec_results = json.loads(res.text).get('results', [])
        profile = []
        facts = []
        summary = []
        for item in vec_results:
            memory = item.get('memory', '')
            memory = _unify_name(memory)
            metadata = item.get('metadata', {})
            created_at = item.get('created_at', '').split('T')[0]
            mem_type = metadata.get('type', '')
            if len(memory) == 0:
                continue

            if mem_type == 'summary':
                summary_unify = _unify_name(metadata.get('summary', ''))
                metadata.update({'summary': summary_unify, 'created_at': created_at})
                summary.append(metadata)
            elif mem_type == 'profile':
                profile.append(memory)
            elif mem_type == 'facts':
                facts.append(memory)

        results = dict(profile=profile, facts=facts, summary=summary)
    except Exception as e:
        logger.exception(f'MemoryMgr::ger_memories|error:{str(e)}')
    return results


def delete_memories(user_id):
    results = {}
    try:
        query_json = {'user_id': user_id}
        res = requests.delete(delete_memories_url, params=query_json, headers={"Content-Type": "application/json"},
                              timeout=20)
        results = json.loads(res.text)
        logger.warning(f'delete_memories|{user_id}, {results}')
    except Exception as e:
        logger.exception(f'MemoryMgr::delete_memories|error:{str(e)}')
    return results


def test_add():
    user_id = 'test-003'
    agent_id = 'xiaoming'
    messages = []
    # messages.append({"role": "user", "content": '我是小明，今年十岁，喜欢跑步'})
    # messages.append({"role": "assistant", "content": '你可以尝试做番茄沙拉、意大利面酱、番茄汤等。'})
    # messages.append({"role": "user", "content": '去年冬天，我报名了西餐厨师培训班呢'})
    # messages.append({"role": "assistant", "content": '真的吗？那你学会了吗？'})
    # messages.append({"role": "user", "content": '刚入门呢，我的师傅他在一次交通事故受伤了，所以我就么有继续学习了。'})
    # messages.append({"role": "assistant", "content": '好吧，那你可以换个地方，继续学习呢。'})

    messages.append({"role": "user", "content": '不好听'})
    messages.append({"role": "assistant", "content": '（思索后温柔道）那我叫你婉儿如何？希望这个名字你会喜欢。'})
    messages.append({"role": "user", "content": '我喜欢钓鱼'})
    messages.append({"role": "assistant", "content": '（憨厚一笑）婉这个字取其温婉之意，希望能符合你的气质。若是不喜欢，你给我起个名字也行'})
    messages.append({"role": "user", "content": '好吧，哥哥既然喜欢，那就这个也无妨。'})
    messages.append({"role": "assistant", "content": '好吧，那你可以换个地方，继续学习呢。'})

    result = add(agent_id, user_id, messages, memory_type='vector')
    print(result)
    # result = add(agent_id, user_id, messages, memory_type='summary')
    # print(result)


def test_search():
    user_id = 'test-003'
    agent_id = 'xiaoming'
    query = '你知道我有什么特长吗'
    result = search(agent_id, user_id, query)
    print(result)


def test_memories():
    user_id = 'test-001'
    result = get_memories(user_id)
    print(result)


def test_delete():
    user_id = 'test-001'
    result = delete_memories(user_id)
    print(result)


if __name__ == "__main__":
    test_add()
    test_search()
    test_memories()
    test_delete()
