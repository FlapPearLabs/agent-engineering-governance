"""Deliberately broken adoption fixture; copy to an isolated demo repository."""
import asyncio


class FeedClient:
    def __init__(self, transport):
        self.transport = transport

    async def fetch(self):
        return await self.transport()


async def count_records(client):
    return len(client.fetch())


async def run(transport):
    return await count_records(FeedClient(transport))


async def sample_transport():
    return [{"id": "first"}, {"id": "second"}]


if __name__ == "__main__":
    print(asyncio.run(run(sample_transport)))
