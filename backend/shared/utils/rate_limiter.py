from slowapi import Limiter
from slowapi.util import get_remote_address
from core.config.settings import settings

# Initialize the limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis.url
)
