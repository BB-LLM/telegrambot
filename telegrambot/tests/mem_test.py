
import sys
import time
import os
sys.path.append(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../')))

import json
import copy
import tqdm
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from mem.memory.memory import Memory
from mem.memory.configs import MemoryConfig

model_regester = {
        'qwen3-30b-moe': {'api_server_url': 'http://test-qwen3-30b-moe-test-dep364-iserving.tmax.netease.com/v1',
                      'model': 'qwen3-30b-moe-test'},
        'qwen3-32b': {'api_server_url': 'http://test-qwen3-32b-dep364-iserving.tmax.netease.com/v1',
                      'model': 'qwen3-32b-test'},
        'qwen3-14b': {'api_server_url': 'http://test-qwen3-14b-dep364-iserving.tmax.netease.com/v1',
                      'model': 'qwen3-14b-test'},
        'qwen3-8b': {'api_server_url': 'http://test-qwen3-8b-dep364-iserving.tmax.netease.com/v1',
                      'model': 'qwen3-8b-test'},
        'qwen3-4b': {'api_server_url': 'http://test-qwen3-4b-dep364-iserving.tmax.netease.com/v1',
                      'model': 'qwen3-4b-test'},

        'doubao': {'api_server_url': 'https://openai.nie.netease.com/v1',
                    'api_key': "o3yaok5v-to05-pw.j4t4aglthmp70im6hepchd7xjt8ysx1d",
                    'model': 'doubao-1.5-pro-32k-character'},
        'deepseek-r1': {'api_server_url': 'https://openai.nie.netease.com/v1',
                        'api_key': "o3yaok5v-to05-pw.j4t4aglthmp70im6hepchd7xjt8ysx1d",
                        'model': 'deepseek-r1-250120'},
        'deepseek-v3': {'api_server_url': 'https://openai.nie.netease.com/v1',
                        'api_key': "o3yaok5v-to05-pw.j4t4aglthmp70im6hepchd7xjt8ysx1d",
                        'model': 'deepseek-v3-latest'},
        'qwen2.5-72b': {'api_server_url': 'https://openai.nie.netease.com/v1',
                        'api_key': "o3yaok5v-to05-pw.j4t4aglthmp70im6hepchd7xjt8ysx1d",
                        'model': 'qwen2.5-72b-instruct'},
    }


def init_memory(model='deepseek-v3'):

    model_config = model_regester.get(model, None)
    assert model_config is not None

    config = {
        # "vector_store": {
        #     "provider": "qdrant",
        #     "config": {
        #         "host": "7.34.73.70",
        #         "port": 6333,
        #         "collection_name": "memory_demo",
        #         "embedding_model_dims": 1024
        #     }
        # },
        "vector_store": {
            "provider": "milvus",
            "config": {
                "url": "http://7.53.23.160:19530",
                "collection_name": "memory_demo",
                "embedding_model_dims": 1024
            }
        },
        # "llm": {
        #     "provider": "openai",
        #     "config": {
        #         "api_key": "None",
        #         "model": "qwen",
        #         "openai_base_url": "http://7.34.76.212:8908/v1"
        #         }
        # },
        "llm": {
            "provider": "openai",
            "config": {
                "api_key": model_config.get('api_key', 'test'),
                "model": model_config.get('model', ''),
                "openai_base_url": model_config.get('api_server_url', ''),
            }
        },
        # "embedder": {
        #     "provider": "openai",
        #     "config": {
        #         "api_key": "xxx",
        #         "model": "multilingual-e5-large-instruct",
        #         "openai_base_url": "http://7.34.73.70:7997",
        #         "embedding_dims": 1024
        #     }
        # },
        "embedder": {
            "provider": "openai",
            "config": {
                "api_key": "xxx",
                "model": "multilingual-e5-large-instruct",
                "openai_base_url": "http://7.34.73.80:6039/v1",
                "embedding_dims": 1024
            }
        },
        # "graph_store": {
        #     "provider": "neo4j",
        #     "config": {
        #         "url": "neo4j://7.34.73.70:7687",
        #         "username": "neo4j",
        #         "password": "12345678"
        #     }
        # },
        "history_db_path": "./history.db",
        "version": "v1.1",
        "custom_prompt": ""
    }
    print(config)
    config = MemoryConfig(**config)
    memory_inst = Memory(config)
    return memory_inst


def add_test():
    user_id = 'test-001'
    messages = []
    # messages.append({"role": "role", "content": '你叫什么名字'})
    # messages.append({"role": "assistant", "content": '我是小明，你不记得我了吗？'})

    # messages.append({"role": "user", "content": '我在找一些以新鲜番茄为主要原料的食谱创意'})
    # messages.append({"role": "assistant", "content": '你可以尝试做番茄沙拉、意大利面酱、番茄汤等。'})
    messages =[
            {
                "role": "user",
                "content": "不好听"
            },
            {
                "role": "assistant",
                "content": "（思索后温柔道）那我叫你婉儿如何？希望这个名字你会喜欢。"
            },
            {
                "role": "user",
                "content": "婉这个字从何而来"
            },
            {
                "role": "assistant",
                "content": "（憨厚一笑）婉这个字取其温婉之意，希望能符合你的气质。若是不喜欢，你给我起个名字也行。"
            },
            {
                "role": "user",
                "content": "好吧，哥哥既然喜欢，那就这个也无妨。"
            },
            {
                "role": "assistant",
                "content": "（开心笑道）那真是太好了，婉儿。今后我会更加留意，不让你失望。"
            },
            {
                "role": "user",
                "content": "哥哥，明天再来，你还会记得我吗（低下头有些失落）其实，我们并不是第一次见面。"
            },
            {
                "role": "assistant",
                "content": "（轻轻抬起她的下巴，目光温柔）婉儿，我当然记得你。不论何时何地，你对我而言都是特别的存在。别难过。"
            },
            {
                "role": "user",
                "content": "哥哥真是…（脸红，眼里泛着泪）你若不记得，我便日日来寻你，可好？"
            },
            {
                "role": "assistant",
                "content": "（心中感动，声音低沉而坚定）婉儿，我不但记得你，还盼着每日都能见到你。不必日日来找我，我知道你会常来的。"
            },
            {
                "role": "user",
                "content": "从此山高不阻其志，涧深不断其行，流年不毁其意，风霜不掩其情。哥哥，我对你的心意就是这样的。"
            },
            {
                "role": "assistant",
                "content": "（握住手，眼神深情）婉儿，你的情意我收下了。从今往后，不论风雨，我都陪你一同走过。"
            },
            {
                "role": "user",
                "content": "哥哥，我真的很高兴。你能不能说几句夸我的话，让我更高兴呢（期待）"
            },
            {
                "role": "assistant",
                "content": "（微笑，真诚地）婉儿聪慧又体贴，对我如此情深意重，怎不让人欢喜。有你在身边真好。"
            }
    ]
    # model = 'qwen3-32b'
    model = 'deepseek-v3'
    memory_inst = init_memory(model)
    new_memory = memory_inst.add(messages, user_id=user_id)
    print(new_memory)


def get_test():
    user_id = 'mem_test:1'
    params = {k: v for k, v in {"user_id": user_id, "run_id": None, "agent_id": None}.items() if v is not None}
    memory_inst = init_memory()
    results = memory_inst.get_all(**params)
    print(results)



def search_test():  
    user_id = 'test-001'
    query = '我们去海边玩吧。'
    memory_inst = init_memory()
    relevant_memories = memory_inst.search(query=query, user_id=user_id, limit=3)
    print(relevant_memories)

    memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories["results"])
    print(memories_str)


def delete_test():
    user_id = 'test-001'
    params = {k: v for k, v in {"user_id": user_id, "run_id": None, "agent_id": None}.items() if v is not None}
    memory_inst = init_memory()
    results = memory_inst.delete_all(**params)
    print(results)


def summary_test():
    user_id = 'test-001'

    # messages = []
    # messages.append({"role": "role", "content": '你叫什么名字'})
    # messages.append({"role": "assistant", "content": '我是小明，你不记得我了吗？'})
    # messages.append({"role": "user", "content": '我在找一些以新鲜番茄为主要原料的食谱创意'})
    # messages.append({"role": "assistant", "content": '你可以尝试做番茄沙拉、意大利面酱、番茄汤等。'})
    messages = [
            {
                "role": "user",
                "content": "害"
            },
            {
                "role": "assistant",
                "content": "(无奈)相公,咱们换个话题吧,有些事还是不要太随便。"
            },
            {
                "role": "user",
                "content": "你居然说我随便，可怜我只是太爱你"
            },
            {
                "role": "assistant",
                "content": "(惊讶)相公言重了,我怎敢这么说。你身体可有大碍?我们需要正经些。"
            },
            {
                "role": "user",
                "content": "我一直都很正经"
            },
            {
                "role": "assistant",
                "content": "(理解)相公,我知道你心急,但我们还需讲究分寸。若真有伤,快告诉我何处不适。"
            },
            {
                "role": "user",
                "content": "我觉得，我们之间怎么干都不过分"
            },
            {
                "role": "assistant",
                "content": "(严肃)相公,这话可就不妥了。咱们还是按规矩来,有事说事,别闹了。"
            },
            {
                "role": "user",
                "content": "害，规矩害的人还不多吗"
            },
            {
                "role": "assistant",
                "content": "(摇头)规矩虽严,却能护人周全。咱们别开玩笑,有事就说事吧。"
            },
            {
                "role": "user",
                "content": "我真没开玩笑"
            },
            {
                "role": "assistant",
                "content": "(凝重)相公,有些玩笑不宜开。我们还是聊聊正事吧,你身体可有哪里真的不舒服?"
            },
            {
                "role": "user",
                "content": "我的大腿上部"
            },
            {
                "role": "assistant",
                "content": "(关切)大腿上部怎了?需不需要查看一下,或者叫大夫来瞧一瞧?"
            },
            {
                "role": "user",
                "content": "你看看吧"
            },
            {
                "role": "assistant",
                "content": "(谨慎)好的,让我帮你看看。请告诉我具体是如何不适的。"
            },
            {
                "role": "user",
                "content": "痛"
            },
            {
                "role": "assistant",
                "content": "(认真)痛吗?让我看一下。若是伤得很重,还得请大夫来诊治。"
            },
            {
                "role": "user",
                "content": "没事，"
            },
            {
                "role": "assistant",
                "content": "(放心)若是无大碍就好,以后遇伤要及时说,别忍着。"
            },
            {
                "role": "user",
                "content": "好的"
            },
            {
                "role": "assistant",
                "content": "(微笑)那就好,有任何不适随时告诉我。"
            },
            {
                "role": "user",
                "content": "以后记得叫我什么"
            },
            {
                "role": "assistant",
                "content": "(挠头)少东家,我总是这样叫您的。有什么特别想让人叫的名讳吗？"
            }
    ]

    # prompt = '请基于以下聊天记录生成总结'
    memory_inst = init_memory()
    results = memory_inst.summary(messages, user_id=user_id)
    print(results)



def parser_mem(vec_results):
    profile = []
    facts = []
    summary = []
    vec_results = vec_results.get('results', [])
    # print(vec_results)
    # print(isinstance(vec_results, list))
    for item in vec_results:
        memory = item.get('memory', '')
        memory = memory.replace('用户', '玩家')
        memory = memory.replace('user', '玩家')
        memory = memory.replace('助手', 'NPC')
        memory = memory.replace('assistant', 'NPC')
        metadata = item.get('metadata', None)
        created_at = item.get('created_at', '').split('T')[0]
        if len(memory) == 0:
            continue

        if metadata:
            metadata.update({'created_at': created_at})
            summary.append(metadata)
        elif memory.startswith('fact'):
            memory = memory.split(':')[-1].strip()
            facts.append(memory)
        else:
            memory = memory.split(':')[-1].strip()
            profile.append(memory)
                

    results = dict(profile=profile, facts=facts, summary=summary)
    return results


def run_test(model='qwen', in_file='./data/test_in.json'):
    """
    model 指定选择的模型
    in_file 输入测试用例， json格式
    """
    # 提取间隔
    profile_intervals = 25
    summary_intervals = 50
    exp = f'_exp61_{profile_intervals}_'
    out_file = in_file.replace('.json', '_' + model + exp + 'out.jsonl')
    with open(in_file, 'r', encoding='utf-8') as fi:
        test_data = json.load(fi)
    test_data = test_data[:10]

    memory_inst = init_memory(model=model)
    fo = open(out_file, 'w', encoding='utf-8')
    for i in tqdm.tqdm(range(len(test_data)), desc='run'):
        ele = test_data[i]
        session_id = ele['session_id']
        messages = copy.deepcopy(ele['messages'])
        
        meta_results = []
        user_id = session_id
        # profile
        for i in range(0, len(messages), profile_intervals):
            split_messages = messages[i:i+profile_intervals]
            try:
                
                memory_results = memory_inst.add(split_messages, user_id=user_id)
                if memory_results:
                    format_result = {'new_memory': memory_results.get('results', []), "graph_memory": memory_results.get("relations", {})}
                    meta_results.append(format_result)
            except Exception as e:
                print(f'generate meme error:{split_messages}')
        
        # summary
        for i in range(0, len(messages), summary_intervals):
            split_messages = messages[i:i+summary_intervals]
            summary_result = memory_inst._create_summary(split_messages, user_id=user_id)

        # get mem
        params = {k: v for k, v in {"user_id": user_id, "run_id": None, "agent_id": None}.items() if v is not None}
        vec_results = memory_inst.get_all(**params)
        final_results = parser_mem(vec_results)

        x = memory_inst.delete_all(**params)
        one_data = dict(session_id=session_id, messages=ele['messages'], meta_results=meta_results, final_results=final_results)

        print(one_data)
        fo.write(json.dumps(one_data, ensure_ascii=False) + '\n')
        fo.flush()

    # convert to json.
    out_data = []
    with open(out_file, 'r', encoding='utf-8') as fi:
        for one_line in fi:
            one_item = json.loads(one_line)
            out_data.append(one_item)

    with open(out_file.replace('.jsonl', '.json'), 'w', encoding='utf-8') as fo:
        json.dump(out_data, fo, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    # delete_test()
    add_test()
    # summary_test()
    # get_test()
    # delete_test()
    # get_test()
    # search_test()
    # run_test()

    # qwen2.5-72b
    # run_test(model='deepseek-v3', in_file='./data/awm_cases.json')
    # run_test(model='qwen3-32b', in_file='./data/awm_cases.json')
    # run_test(model='qwen2.5-72b', in_file='./data/awm_cases.json')
    # run_test(model='doubao', in_file='./data/awm_cases.json')
    # run_test(model='qwen3-14b', in_file='./data/test_cases_20250416.json')
    # run_test(model='qwen3-32b', in_file='./data/test_cases_20250416.json')
    # run_test(model='deepseek-v3', in_file='./data/test_cases_20250416.json')
    # run_test(model='doubao', in_file='./data/test_cases_20250416.json')

