from mem.embeddings.configs import BaseEmbedderConfig
from mem.embeddings.openai_em import OpenAIEmbedding


def test_embed():
    em_config = {
        'model': 'doubao-embedding-text-240715',
        'api_key': '8b2dce0f-ed36-4d2b-898a-14845cc496c1',
        'openai_base_url': 'ark',
        'embedding_dims': 2560
        }
    config = BaseEmbedderConfig(model=em_config.get('model'),
                                api_key=em_config.get('api_key'),
                                openai_base_url=em_config.get('openai_base_url'),
                                embedding_dims=em_config.get('embedding_dims'))
    embedder = OpenAIEmbedding(config)
    text = '你好啊，好久不见~'
    result = embedder.embed(text)
    print(result)


if __name__ == "__main__":
    test_embed()