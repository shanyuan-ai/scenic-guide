# download_model.py
import os

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download

print("开始下载模型，请耐心等待...")
print("模型大小约 471MB，预计 5-10 分钟")

try:
    snapshot_download(
        repo_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        local_dir="./models/paraphrase-multilingual-MiniLM-L12-v2",
        resume_download=True,
        local_files_only=False,
    )
    print("✅ 模型下载完成！")
except Exception as e:
    print(f"下载失败: {e}")
# download_model.py
