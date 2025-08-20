# server/server.py
import asyncio
import websockets
import json

PORT = 8765
clients = set()

async def handler(ws, path):
    clients.add(ws)
    try:
        async for message in ws:
            data = json.loads(message)
            broadcast = json.dumps(data)
            await asyncio.gather(*[c.send(broadcast) for c in clients if c != ws])
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(ws)

if __name__ == "__main__":
    print(f"Starting server on ws://localhost:{PORT}")
    start_server = websockets.serve(handler, "0.0.0.0", PORT)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
