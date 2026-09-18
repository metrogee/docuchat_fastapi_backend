from services.health_service import get_health_message

async def health_check():
    return get_health_message()
