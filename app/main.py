from fastapi import FastAPI
from app.routes import system, square, slack, analytics
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)

app.state.secret_key = settings.SECRET_KEY

app.include_router(system.router)
app.include_router(square.router, prefix="/square")
app.include_router(slack.router, prefix="/slack")
app.include_router(analytics.router, prefix="/analytics")

@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} is alive 🔮"}

