from typing import Optional, List, Dict, Any, Tuple, Union
import numpy as np
import requests


def embedding(
        input: Union[str, List[str]],
        model_name: str = "mem-embed-qwen3",  #  "multilingual-e5-large-instruct", # "mem-embed-qwen3",
    ) -> List[float]:
    """文本到embedding 的 api"""

    url = 'http://embedding-mem-hzailab-iserving.tmax.netease.com/v1/embeddings'
    headers = {"Content-Type": "application/json"}

    body = {
        "input": input,
        "model": model_name,
        "encoding_format": "float",
        "dimensions": 1024
      }
    r = requests.post(url, json=body, headers=headers, timeout=5)
    try:
        a = r.json()["data"][0]
    except Exception as e:
        print(r.json())
        return []

    if isinstance(input, str):
        return r.json()["data"][0]["embedding"]
    else:
        return [r.json()["data"][i]["embedding"] for i in range(len(input))]


if __name__ =="__main__":
    text = '你好啊啊，好久不见！'
    result = embedding([text, text, text])
    for ele in result:
        print(ele)