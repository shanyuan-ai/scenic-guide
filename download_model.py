# download_model.py
"""下载 RAG 模型权重到本地 models/ 目录。

默认从 ModelScope(魔搭,国内访问快)拉取;若失败可改用 HuggingFace 镜像。
下载完成后,vector_service 会自动检测 models/ 下的本地权重并启用向量检索。
"""
import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / 'models'

# (ModelScope 模型 ID, 本地子目录名)
MODELS = [
    ('Xorbits/bge-m3', 'bge-m3'),
    ('BAAI/bge-reranker-v2-m3', 'bge-reranker-v2-m3'),
]


def download_from_modelscope(model_id: str, local_dir: Path):
    """从 ModelScope 下载模型到指定目录。"""
    from modelscope import snapshot_download

    target = str(local_dir)
    print(f'[ModelScope] 下载 {model_id} -> {target}')
    # cache_dir 用临时目录,下载完成后文件已在 local_dir
    snapshot_download(
        model_id=model_id,
        local_dir=target,
        ignore_patterns=['*.pth', '*.onnx', 'openvino*', '*.mlmodel', 'pytorch_model.bin'],  # safetensors 已够用,跳过冗余 pytorch 权重
    )


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print('开始下载 RAG 模型,请耐心等待...')
    print(f'目标目录: {MODELS_DIR}\n')

    failures = []
    for model_id, dir_name in MODELS:
        local_dir = MODELS_DIR / dir_name
        try:
            download_from_modelscope(model_id, local_dir)
            print(f'[OK] {model_id} 下载完成\n')
        except Exception as exc:
            print(f'[失败] {model_id}: {exc}\n')
            failures.append(model_id)

    if failures:
        print(f'以下模型下载失败,可重试或改用 HuggingFace 镜像: {failures}')
        print('提示: 设置 HF_ENDPOINT=https://hf-mirror.com 后运行备用脚本,或手动放置权重到 models/')
    else:
        print('全部模型下载完成。')


if __name__ == '__main__':
    main()
