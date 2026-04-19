from openai import AsyncOpenAI


def make_openai_embed(api_key: str, model: str = "text-embedding-3-small"):
    client = AsyncOpenAI(api_key=api_key)
    async def embed(texts: list[str]) -> list[list[float]]:
        resp = await client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]
    return embed
