import numpy as np
import json
from sentence_transformers import SentenceTransformer

def init_embeder():
    model_path = '/storage06/users/kongxiangxing/models/bge-large-zh-v1.5'
    # model_path = "/storage03/users/kongxiangxing/projects/danzai/text_cluster/models/distiluse-base-multilingual-cased-v1"
    embeder = SentenceTransformer(model_path)
    return embeder
embeder = init_embeder()


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    cosine = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return cosine


def test_sbert():
    sentences = ["我爱北京", "北京天安门是我的家"]
    embeddings = embeder.encode(sentences)
    print(embeddings)
    print(type(embeddings))

    similar_score = cosine_similarity(embeddings[0], embeddings[1])
    print(similar_score)


def cal_relate_text(corpus_a=None, corpus_b=None):
    """两个集合，计算之间每个文本的相似度
    """
    if corpus_a is None and corpus_b is None:
        corpus_a = ['觉得语法比较容易掌握', '认为记单词比较费劲']
        corpus_b =["用户认为语法还算容易", "用户觉得记单词比较费劲"]

    input_texts = corpus_a + corpus_b
    split_num = len(corpus_a)

    embeddings = embeder.encode(input_texts, convert_to_tensor=True, normalize_embeddings=True)

    scores = (embeddings[:split_num] @ embeddings[split_num:].T) * 100
    # print(corpus_a)
    # print(corpus_b)
    # print(scores.tolist())

    return scores


def extract_metric(extract_file):
    hype_file = './data/test_hype_20250416_refine.json'
    # extract_file = './data/test_cases_20250416_qwen3-32b_exp3_out.json'
    # extract_file = './data/test_cases_20250416_deepseek-v3_exp3_out.json'
    eval_file = extract_file.replace('.json', '_eval_bge.json')


    with open(hype_file, 'r', encoding='utf-8') as fi:
        hype_data = json.load(fi)

    with open(extract_file, 'r', encoding='utf-8') as fi:
        extract_data = json.load(fi)

    
    id2hype = {x['session_id']: x['hype'] for x in hype_data}

    extract_format_list = []
    for ele in extract_data:
        session_id = ele['session_id']
        extract = ele['final_results']
        extract_vec = extract.get('profile', []) + extract.get('facts', [])
        extract_graph = []
        for x in extract.get('relations', []):
            source = x['source']
            relationship = x['relationship']
            target = x['source']
            if source.find('mem_test') != -1 or source.find('user_id') != -1:
                source = '用户'
            if target.find('mem_test') != -1 or target.find('user_id') != -1:
                target = '用户'
            
            relate_str = source + "->" + relationship + '->' + target
            extract_graph.append(relate_str)
        extract_format_list.append(dict(session_id=session_id, extract_vec=extract_vec, extract_graph=extract_graph))

    score_thred = 60
    out = []
    extracts_match_num = 0  # 抽取被命中的数目
    hypes_match_num = 0     # 标注被命中的数据
    extracts_num = 0        # 抽取总数
    hypes_num = 0           # 标注总数
    for ele in extract_format_list:
        session_id = ele['session_id']
        extracts = ele['extract_vec']
        hypes = id2hype.get(session_id)
        scores = cal_relate_text(extracts, hypes)
        extract_hit = []
        extract_error = [] 
        hype_hit = []
        hit_info = []
        for i in range(len(scores)):
            group_score = scores[i].tolist()
            score_max = max(group_score)
            score_index = group_score.index(score_max)
            extract_str = extracts[i]
            match_hype_str = hypes[score_index]
            print(f'score_max: {score_max}, score_index: {score_index}, extract: {extract_str}, match_hype: {match_hype_str}')

            if score_max > score_thred:
                extract_hit.append(extract_str)
                hype_hit.append(match_hype_str)
                hit_info.append(extract_str + "==" + match_hype_str)
            else:
                extract_error.append(extract_str)

        extract_unhit = [item for item in extracts if item not in set(extract_hit)]
        hype_unhit = [item for item in hypes if item not in set(hype_hit)]

        ele.update({'hypes': hypes, 'hit_info': hit_info, 'extract_unhit': extract_unhit, 'hype_unhit': hype_unhit})
        out.append(ele)

        extracts_match_num += len(set(extract_hit))
        hypes_match_num += len(set(hype_hit))
        hypes_num += len(hypes)
        extracts_num += len(extracts)

    print(extract_file)
    print(f'recall: {round(hypes_match_num/hypes_num, 3)}')
    print(f'acc: {round(extracts_match_num/extracts_num, 3)}')

    with open(eval_file.replace('.jsonl', '.json'), 'w', encoding='utf-8') as fo:
        json.dump(out, fo, ensure_ascii=False, indent=4)
            

if __name__ == "__main__":
    # test_sbert()
    # cal_relate_text()
    extract_file = './data/test_cases_20250416_qwen3-14b_exp51_out.json'
    # extract_file = './data/test_cases_20250416_qwen3-32b_exp51_out.json'
    # extract_file = './data/test_cases_20250416_deepseek-v3_exp51_out.json'
    extract_metric(extract_file)

"""
./data/test_cases_20250416_qwen3-32b_exp3_out.json
recall: 0.729
acc: 0.905


./data/test_cases_20250416_deepseek-v3_exp3_out.json
recall: 0.75
acc: 0.925


update -> 
./data/test_cases_20250416_qwen3-14b_exp41_out.json
recall: 0.767
acc: 0.873

./data/test_cases_20250416_qwen3-32b_exp41_out.json
recall: 0.767
acc: 0.895

./data/test_cases_20250416_deepseek-v3_exp41_out.json
recall: 0.783
acc: 0.939

./data/test_cases_20250416_qwen3-14b_exp51_out.json
recall: 0.682
acc: 0.917

./data/test_cases_20250416_qwen3-32b_exp51_out.json
recall: 0.628
acc: 0.918

./data/test_cases_20250416_deepseek-v3_exp51_out.json
recall: 0.721
acc: 0.944

"""
