import asyncio
import websockets

connected_clients = set()

async def handler(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # Broadcast the encrypted message to all clients
            for client in connected_clients:
                if client != websocket:
                    await client.send(message)
    except websockets.ConnectionClosed:
        connected_clients.remove(websocket)

start_server = websockets.serve(handler, "127.0.0.1", 8000)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()