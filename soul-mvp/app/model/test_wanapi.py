from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope
import os

# 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
# 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
# api_key = os.getenv("DASHSCOPE_API_KEY")
api_key = os.getenv("DASHSCOPE_API_KEY", "sk-dd7ca82994dd4b2e8f83d2ca0945d29d")

def sample_async_call_t2v():
    # call async api, will return the task information
    # you can get task status with the returned task id.
    rsp = VideoSynthesis.async_call(api_key=api_key,
                                    model='wan2.5-t2v-preview',
                                    prompt='人设：李哲，MBTI人格为INTJ（内向、直觉、思考、判断）。他是一名30岁的数据分析师，性格理性、战略性强，喜欢独处和深度思考。穿衣打扮上，他偏好简约而专业的风格：身穿一件深灰色修身西装外套，内搭白色纯棉衬衫，搭配黑色修身长裤和一双抛光皮革皮鞋。他的配饰包括一块银色智能手表和一副黑框眼镜，整体造型干净利落，体现了他对效率和秩序的追求。他的发型是整齐的短发，没有多余装饰，强调功能性和低调的优雅。场景介绍：一个安静的私人画室，室内光线柔和，墙上挂满了抽象画作，画架上摆着一幅未完成的油画。空气中弥漫着松节油和颜料的气味，环境静谧，适合专注创作。叙事：李哲走进画室，目光冷静地扫过画架上的作品。他并非来作画，而是受朋友之托分析画作的构图数据。他戴上手套，拿出平板电脑记录色彩分布，手指轻点屏幕，计算着黄金比例是否适用。当一位陌生画家热情地邀请他尝试挥笔时，李哲微微摇头，用平静的语气解释：“艺术需要感性，但我更擅长用逻辑解构美。”他继续专注于数据，仿佛整个空间只是他思考的延伸，没有丝毫情感波动。',
                                    size='832*480',
                                    duration=5,
                                    negative_prompt="",
                                    # audio=True,
                                    prompt_extend=True,
                                    watermark=False,
                                    seed=12345)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))
                           
    # get the task information include the task status.
    status = VideoSynthesis.fetch(rsp, api_key=api_key)
    if status.status_code == HTTPStatus.OK:
        print(status.output.task_status)  # check the task status
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (status.status_code, status.code, status.message))

    # wait the task complete, will call fetch interval, and check it's in finished status.
    rsp = VideoSynthesis.wait(rsp, api_key=api_key)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_async_call_t2v()