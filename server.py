from fastapi import FastAPI, Depends
from routes.routes import router

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db


app = FastAPI(title="Docuchat Backend", version="1.0.0")

# Register application routes(telling the server to use the routes that have been created somewhere)
app.include_router(router)

@app.get("/")
def home():
    return {
        "message": "FastAPI server is working"
    }


@app.get("/database-test")
def database_test(
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("SELECT 1")
    )

    return {
        "database": result.scalar()
    }



# @app.get("/users/{user_id}")
# def get_user(
#     user_id: str,
#     db: Session = Depends(get_db),
# ):
#     user = user_repository.find_by_id(
#         db,
#         user_id,
#     )

#     if not user:
#         return {
#             "message": "User not found"
#         }

#     return {
#         "id": user.id,
#         "name": user.name,
#         "email": user.email,
#     }










if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)
