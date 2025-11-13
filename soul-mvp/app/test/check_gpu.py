#!/usr/bin/env python
"""
GPU检测脚本
"""
import torch

def check_gpu():
    """检测GPU可用性"""
    print("="*60)
    print("GPU Detection Report")
    print("="*60)
    
    # PyTorch版本
    print(f"PyTorch Version: {torch.__version__}")
    print()
    
    # CUDA可用性
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        # GPU数量
        gpu_count = torch.cuda.device_count()
        print(f"GPU Count: {gpu_count}")
        
        # 详细GPU信息
        for i in range(gpu_count):
            print(f"\nGPU {i}:")
            print(f"  Name: {torch.cuda.get_device_name(i)}")
            print(f"  Memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
            print(f"  CUDA Capability: {torch.cuda.get_device_properties(i).major}.{torch.cuda.get_device_properties(i).minor}")
        
        # CUDA版本
        print(f"\nCUDA Version: {torch.version.cuda}")
        print(f"cuDNN Version: {torch.backends.cudnn.version()}")
        
    else:
        print("\nNo GPU detected")
        print("Your system will use CPU for computations")
    
    print("="*60)

if __name__ == "__main__":
    check_gpu()

