from fastapi import FastAPI
from routes.routes import router

app = FastAPI(title="Dochucat Backend", version="1.0.0")

# Register application routes(telling the server to use the routes that have been created somewhere)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)
