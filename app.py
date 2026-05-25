from fastapi import FastAPI
from main import run_pipeline

app = FastAPI()


@app.get("/")
def home():
    return {"message": "AI Backend Compiler Pipeline Running"}


@app.post("/generate")
def generate(prompt: str):

    result = run_pipeline(prompt)

    return result.model_dump()