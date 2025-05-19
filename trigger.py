import asyncio
import websockets
import json

async def send_trigger(command: str):
    async with websockets.connect("ws://localhost:8768") as websocket:
        if command == "start":
            await websocket.send(json.dumps({"start": True}))
        elif command == "stop":
            await websocket.send(json.dumps({"stop": True}))
        response = await websocket.recv()
        print("Server Response:", response)

# Example usage:
#asyncio.run(send_trigger("start"))
asyncio.run(send_trigger("stop"))
