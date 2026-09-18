# Dochucat FastAPI Backend

A Python/FastAPI recreation of the backend structure shown in the reference Express.js project.

## Architecture

```text
Request
   ↓
Routes
   ↓
Controllers
   ↓
Services
   ↓
Repositories
   ↓
Database
```

## Project structure

```text
dochucat_fastapi_backend/
├── config/
│   └── settings.py
├── controllers/
│   └── health_controller.py
├── middleware/
│   └── auth.py
├── repositories/
│   └── database.py
├── routes/
│   └── routes.py
├── services/
│   ├── health_service.py
│   ├── order_service.py
│   ├── payment_service.py
│   └── product_service.py
├── server.py
└── requirements.txt
```

## Installation

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Start the server

```bash
python server.py
```

The server runs at:

```text
http://localhost:3000
```

## Test the API

Open:

```text
http://localhost:3000/
```

You should receive:

```json
{
  "message": "Hello World"
}
```

## Automatic API documentation

FastAPI automatically provides Swagger UI:

```text
http://localhost:3000/docs
```

and ReDoc:

```text
http://localhost:3000/redoc
```

## Equivalent to the original Express code

Original:

```typescript
const express = require("express");
const app = express();

app.use(express.json());

app.get("/", (req, res) => {
    res.send("Hello World!");
});

app.listen(3000, () => {
    console.log("Server is running on port 3000");
});
```

FastAPI equivalent:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "Hello World"}
```

The project keeps the additional controller, service, repository, middleware, and config folders so it can grow into a real backend rather than being only a single-file demo.
