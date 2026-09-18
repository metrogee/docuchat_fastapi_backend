from fastapi import APIRouter
from controllers.health_controller import health_check

router = APIRouter()

router.add_api_route("/", health_check, methods=["GET"])
