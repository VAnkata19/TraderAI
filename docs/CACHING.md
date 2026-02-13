# Caching Architecture

## Overview

TraderAI uses a **unified caching infrastructure** that consolidates three separate cache implementations into a single, extensible pattern. This enables consistent TTL management, easier testing, and simpler addition of new cache backends (Redis, memcached, etc.).

## Cache Providers

### Base Interface (`core/cache/base.py`)

All cache implementations inherit from `CacheProvider`:

```python
class CacheProvider(ABC):
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None: ...
    def clear(self) -> None: ...
    def get_or_fetch(self, key: str, fetch_fn: Callable, ttl: Optional[timedelta] = None) -> Any: ...
```

### Implementations

#### InMemoryCache (`core/cache/memory.py`)
- Thread-safe in-memory cache with TTL support
- Automatically expires entries based on configured TTL
- Default for CLI/background operations

```python
from core.cache import InMemoryCache, CACHE_TTL_QUOTE

cache = InMemoryCache()
price = cache.get_or_fetch(
    key="price_AAPL",
    fetch_fn=lambda: get_latest_price("AAPL"),
    ttl=CACHE_TTL_QUOTE  # 30 seconds
)
```

#### StreamlitCache (`core/cache/streamlit.py`)
- Wraps Streamlit's `@st.cache_data` decorator
- Delegates to `st.session_state` when available
- Falls back to in-memory cache outside Streamlit
- Useful for persistent caching across dashboard reruns

```python
from core.cache import StreamlitCache

cache = StreamlitCache()
# Works in both Streamlit and non-Streamlit contexts
```

### Global Cache Instance

The default cache instance can be accessed and modified:

```python
from core.cache import get_cache, set_cache

# Use default cache
cache = get_cache()

# Switch to custom implementation
set_cache(StreamlitCache())
```

## TTL Configuration

All TTL constants are defined in `core/cache/config.py`:

```python
CACHE_TTL_QUOTE = timedelta(seconds=30)              # Real-time market data
CACHE_TTL_ACCOUNT = timedelta(seconds=30)            # Account data
CACHE_TTL_POSITIONS = timedelta(seconds=60)          # Position data
CACHE_TTL_HISTORICAL = timedelta(seconds=300)        # 5 minutes
CACHE_TTL_TICKER_INFO = timedelta(seconds=3600)      # 1 hour
```

## Integration Points

### Alpaca API Cache (`core/alpaca/cache.py`)

The Alpaca module uses the unified cache with rate limiting:

```python
from core.alpaca.cache import get_cached_or_fetch
from core.cache.config import CACHE_TTL_QUOTE

price = get_cached_or_fetch(
    key="price_AAPL",
    fetch_fn=get_latest_trade,
    ttl=CACHE_TTL_QUOTE
)
```

**Rate Limiting:** The `AlpacaRateLimiter` prevents hitting the free plan's 200 requests/minute limit by:
1. Tracking request timestamps
2. Refusing new requests when approaching the limit
3. Returning stale cached data instead

### Provider Chains (`core/providers/chains.py`)

Pre-configured provider chains automatically fallback between data sources:

```python
from core.providers.chains import get_ticker_info_chain

chain = get_ticker_info_chain()
# Uses Alpaca (if enabled) → falls back to yfinance
info = chain.get_ticker_info("AAPL")
```

### Dashboard Integration (`dashboard/utils/data.py`)

Dashboard functions use provider chains with Streamlit's native caching:

```python
@st.cache_data(ttl=60)
def get_ticker_info(ticker: str) -> dict | None:
    chain = get_ticker_info_chain()
    return chain.get_ticker_info(ticker)
```

## Best Practices

### 1. Use Appropriate TTLs

```python
# Real-time data: short TTL
price = get_cached_or_fetch(key, fetch_fn, CACHE_TTL_QUOTE)

# Historical data: longer TTL (rarely changes)
bars = get_cached_or_fetch(key, fetch_fn, CACHE_TTL_HISTORICAL)
```

### 2. Cache Key Naming Convention

```python
# Good: Includes all parameters that affect the result
f"bars_{ticker}_{period}_{interval}"
f"price_{ticker}"

# Bad: Too generic (collisions possible)
"price"
"data"
```

### 3. Graceful Failure with Fallbacks

```python
# Use get_or_fetch for automatic fetch-on-miss
cached = cache.get_or_fetch(
    key="expensive_operation",
    fetch_fn=lambda: expensive_operation(),
    ttl=timedelta(minutes=5)
)

# Or handle separately
if not (cached := cache.get(key)):
    cached = expensive_operation()
    cache.set(key, cached, ttl=timedelta(minutes=5))
```

## Migration Guide

### From Old Pattern (AlpacaDataCache)

**Before:**
```python
from core.alpaca_broker import get_current_price_cached
price = get_current_price_cached("AAPL")  # Cache built-in, seconds-based
```

**After:**
```python
from core.alpaca.historical import get_current_price_cached
from core.cache.config import CACHE_TTL_QUOTE
price = get_current_price_cached("AAPL")  # Cache built-in, timedelta-based
```

### From Manual Caching

**Before:**
```python
if "ticker_info" not in st.session_state:
    st.session_state.ticker_info = get_ticker_info("AAPL")
info = st.session_state.ticker_info
```

**After:**
```python
from core.cache import StreamlitCache
cache = StreamlitCache()
info = cache.get_or_fetch("ticker_info", get_ticker_info, CACHE_TTL_TICKER_INFO)
```

## Testing Cache Behavior

```python
from core.cache import InMemoryCache
from datetime import timedelta

cache = InMemoryCache()

# Test cache hit
cache.set("key", "value", ttl=timedelta(seconds=10))
assert cache.get("key") == "value"

# Test cache miss after expiry
import time
time.sleep(11)
assert cache.get("key") is None

# Test get_or_fetch convenience method
result = cache.get_or_fetch(
    "new_key",
    lambda: expensive_operation(),
    ttl=timedelta(seconds=5)
)
```

## Performance Impact

- **Cache hits:** ~1ms (in-memory lookup)
- **Cache misses:** Depends on backend (Alpaca: ~100-500ms, yfinance: ~500-2000ms)
- **TTL expiry overhead:** <1ms per expired entry
- **Rate limit checking:** <1ms

Expected improvement with caching:
- Without cache: 30 API calls × 200ms = 6 seconds per analysis
- With cache (80% hit rate): 6 API calls × 200ms + 24 × 1ms = ~1.2 seconds per analysis
- **5x performance improvement**

## Future Enhancements

1. **Redis backend** for distributed caching across workers
2. **Prometheus metrics** for cache hit rate monitoring
3. **Automatic cache warming** before market open
4. **Cache statistics** API for debugging and optimization
5. **Compression** for large cached objects (historical bars)
