import asyncio
import websockets
import json
import argparse

# Change this to match your server host and port
WEBSOCKET_URI = "ws://localhost:8768"

async def send_command(start: bool):
    async with websockets.connect(WEBSOCKET_URI) as websocket:
        command = {"start": start}
        print(f"Sending: {command}")
        await websocket.send(json.dumps(command))

        try:
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"Response: {response}")
        except asyncio.TimeoutError:
            print("No more messages received. Closing connection.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger start/stop WebSocket command")
    parser.add_argument('--start', action='store_true', help='Send {"start": true} command')
    parser.add_argument('--stop', action='store_true', help='Send {"start": false} command')
    args = parser.parse_args()

    if args.start:
        asyncio.run(send_command(True))
    elif args.stop:
        asyncio.run(send_command(False))
    else:
        print("Please use --start or --stop")
