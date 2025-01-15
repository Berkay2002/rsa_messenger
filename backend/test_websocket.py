import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:5000/socket.io"
    async with websockets.connect(uri) as websocket:
        # Register user
        await websocket.send(json.dumps({"type": "register", "username": "user1"}))
        print(await websocket.recv())

        # Send message
        await websocket.send(json.dumps({
            "type": "send_message",
            "sender": "user1",
            "recipient": "user2",
            "message": "encrypted_message"
        }))
        print(await websocket.recv())

asyncio.run(test_websocket())
