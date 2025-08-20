# client/src/network.py
import asyncio
import websockets
import json

SERVER = "ws://localhost:8765"

async def run():
    async with websockets.connect(SERVER) as ws:
        # envoyer un message d'exemple pour rejoindre
        await ws.send(json.dumps({"type":"join", "player":"player1"}))
        async for message in ws:
            data = json.loads(message)
            # TODO : traiter les mises à jour (positions, actions des autres joueurs)
            print("Received:", data)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run())
