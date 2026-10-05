from datetime import datetime, timedelta, timezone

import jwt

from utils.jwt import JWT_ACCESS_SECRET


expired_token = jwt.encode(
    {
        "sub": "e922b2d6-60b8-41d3-9d9a-b4910796528e",
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    },
    JWT_ACCESS_SECRET,
    algorithm="HS256",
)

print("Expired access token:")
print(expired_token)