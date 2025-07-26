from fastapi import FastAPI, Query
from pydantic import BaseModel
from llama_cpp import Llama
import os

app = FastAPI()

# === モデルファイルのパス一覧 ===
MODEL_PATHS = {
    "shisa": "./models/shisa8b-q4.gguf",
}

# === モデルインスタンスのキャッシュ ===
MODELS = {}

def get_model(model_name: str) -> Llama:
    if model_name not in MODELS:
        if model_name not in MODEL_PATHS:
            raise ValueError(f"Unknown model: {model_name}")
        print(f"🔄 Loading model: {model_name}")
        MODELS[model_name] = Llama(
            model_path=MODEL_PATHS[model_name],
            n_ctx=4096,
            n_threads=os.cpu_count(),  # すべてのCPUスレッド使う
            n_batch=64
        )
    return MODELS[model_name]

# === リクエスト形式 ===
class CompletionRequest(BaseModel):
    prompt: str
    model: str = "shisa"
    max_tokens: int = 128
    temperature: float = 0.7

# === レスポンス形式 ===
class CompletionResponse(BaseModel):
    response: str

@app.post("/v1/completions", response_model=CompletionResponse)
def complete(req: CompletionRequest):
    llm = get_model(req.model)

    full_prompt = f"{req.prompt}"
    print(f"📝 {req.model}: {req.prompt}")

    result = llm(
        full_prompt,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        echo=False
    )

    text = result["choices"][0]["text"]
    return {"response": text.strip()}

