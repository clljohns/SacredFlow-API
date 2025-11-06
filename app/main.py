from fastapi import FastAPI\n\napp = FastAPI(title="SacredFlow API")\n\n@app.get("/")\ndef root():\n    return {"message": "SacredFlow API is alive 🔮"}
