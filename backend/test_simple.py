from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"TESTING": "NEW_BACKEND_IS_WORKING", "version": "test-123"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)