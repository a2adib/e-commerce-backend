import time
from collections import defaultdict
from fastapi import Request
from src.common.exceptions import APIError
from src.common.redis import get_redis_client

# Local in-memory sliding window fallback
_memory_store: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60, prefix: str = "rl"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    async def __call__(self, request: Request):
        # Identify caller via Client IP or Authorization Header
        client_ip = request.client.host if request.client else "unknown"
        key = f"{self.prefix}:{request.url.path}:{client_ip}"

        redis = await get_redis_client()
        now = time.time()

        if redis:
            try:
                # Redis sliding window using sorted sets
                pipe = redis.pipeline()
                pipe.zremrangebyscore(key, 0, now - self.window_seconds)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, self.window_seconds)
                _, _, count, _ = await pipe.execute()

                if count > self.max_requests:
                    raise APIError(
                        status_code=429,
                        detail="Too many requests. Please try again later.",
                        code="RATE_LIMIT_EXCEEDED",
                    )
                return
            except APIError:
                raise
            except Exception:
                pass  # Fall back to in-memory rate limiting if Redis fails

        # In-memory fallback
        window_start = now - self.window_seconds
        timestamps = _memory_store[key]
        _memory_store[key] = [t for t in timestamps if t > window_start]

        if len(_memory_store[key]) >= self.max_requests:
            raise APIError(
                status_code=429,
                detail="Too many requests. Please try again later.",
                code="RATE_LIMIT_EXCEEDED",
            )
        _memory_store[key].append(now)
