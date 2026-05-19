# download_model.py
import os

from huggingface_hub import snapshot_download

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

MODELS = [
    ("BAAI/bge-m3", "./models/bge-m3"),
    ("BAAI/bge-reranker-v2-m3", "./models/bge-reranker-v2-m3"),
]


def main():
    print("开始下载 RAG 模型，请耐心等待...")
    for repo_id, local_dir in MODELS:
        print(f"下载 {repo_id} -> {local_dir}")
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            resume_download=True,
            local_files_only=False,
        )
    print("模型下载完成")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"下载失败: {exc}")
