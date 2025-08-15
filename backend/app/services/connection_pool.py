"""HTTP connection pool manager for improved performance"""

from typing import Optional

import httpx
from openai import AsyncOpenAI

from ..config import Settings


class ConnectionPoolManager:
    """Singleton class for managing HTTP connection pools"""

    _instance: Optional['ConnectionPoolManager'] = None

    def __init__(self):
        if ConnectionPoolManager._instance is not None:
            raise Exception("ConnectionPoolManager is a singleton class")

        settings = Settings()

        # Create reusable HTTP client with optimized settings
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,  # Connection timeout: 5 seconds
                read=10.0,    # Read timeout: 10 seconds
                write=5.0,    # Write timeout: 5 seconds
                pool=5.0      # Pool timeout: 5 seconds
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,  # Keep 10 connections alive
                max_connections=20,            # Max 20 concurrent connections
                keepalive_expiry=30.0         # Keep connections alive for 30 seconds
            ),
            # HTTP/2 disabled to avoid dependency issues in tests
            http2=False,
            # Retry configuration
            transport=httpx.HTTPTransport(
                retries=2  # Retry failed requests up to 2 times
            )
        )

        # Create OpenAI client with default HTTP client to avoid compatibility issues
        # OpenAI client will use its own optimized HTTP client internally
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=5.0  # Set timeout directly on OpenAI client
        )

        ConnectionPoolManager._instance = self
        print("✅ ConnectionPoolManager initialized with optimized settings")

    @classmethod
    def get_instance(cls) -> 'ConnectionPoolManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = ConnectionPoolManager()
        return cls._instance

    def get_http_client(self) -> httpx.AsyncClient:
        """Get the shared HTTP client"""
        return self.http_client

    def get_openai_client(self) -> AsyncOpenAI:
        """Get the shared OpenAI client"""
        return self.openai_client

    async def close(self):
        """Close all connections"""
        if self.http_client:
            await self.http_client.aclose()
            print("🔌 HTTP connection pool closed")


# Global instance getter
def get_connection_pool() -> ConnectionPoolManager:
    """Get the global connection pool manager instance"""
    return ConnectionPoolManager.get_instance()
