 curl https://ark.cn-beijing.volces.com/api/v3/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 8b2dce0f-ed36-4d2b-898a-14845cc496c1" \
  -d $'{
    "encoding_format": "float",
    "input": [
        " 天很蓝",
        "海很深"
    ],
    "model": "doubao-embedding-text-240715"
}'