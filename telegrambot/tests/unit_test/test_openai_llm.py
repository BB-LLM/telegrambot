import os
from mem.llms.configs import BaseLlmConfig
from mem.llms.openai_llm import OpenAILLM


def test_llm():
    llm_config = {
            "api_key": "8b2dce0f-ed36-4d2b-898a-14845cc496c1",
            "model": "doubao-1-5-pro-32k-character-250715",
            "openai_base_url": "https://ark.cn-beijing.volces.com/api/v3"
    }
    config = BaseLlmConfig(model=llm_config.get('model'),
                           api_key=llm_config.get('api_key'),
                           openai_base_url=llm_config.get('openai_base_url'),
                           temperature=0.7, max_tokens=100, top_p=1.0)
    llm = OpenAILLM(config)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    response = llm.generate_response(messages)

    print(response)


if __name__ == "__main__":
    test_llm()
