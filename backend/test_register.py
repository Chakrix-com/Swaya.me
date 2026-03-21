import asyncio
import httpx

async def test_register():
    url = "http://localhost:8000/api/v1/auth/register"
    # Need new random email to avoid duplicate error
    import uuid
    rand_id = str(uuid.uuid4())[:8]
    payload = {
        "email": f"testuser_{rand_id}@example.com",
        "password": "Password123!",
        "full_name": "Test User"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(test_register())
