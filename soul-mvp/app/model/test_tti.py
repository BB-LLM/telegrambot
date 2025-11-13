from diffusers import StableDiffusionXLPipeline
import torch

# 检查设备
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用设备: {device}")

# 统一使用float32避免数据类型冲突
pipeline = StableDiffusionXLPipeline.from_single_file(
    r"D:\app\vscode\project\soul\app\model\sdXL_v10VAEFix.safetensors",
    torch_dtype=torch.float32  # 强制使用float32
)

pipeline.to(device)

prompt = "a beautiful girl, in the style of anime"
negative_prompt = "blurry, low quality, realistic, photorealistic, dark, scary"
num_inference_steps = 20
seed = 42

image = pipeline(prompt, negative_prompt, num_inference_steps=num_inference_steps, seed=seed).images[0]
image.save("test_tti.png")
print("图像生成完成！")