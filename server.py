import asyncio
import pika
import threading
import websockets
import subprocess
import json
import csv
import os

# RabbitMQ connection settings
RABBITMQ_HOST = '10.216.172.152'
RABBITMQ_USER = 'admin'
RABBITMQ_PASSWORD = 'Infobell@123'
QUEUE_NAMES = ['VA_AMD', 'VA_INTEL']

ws_queue = asyncio.Queue()
start_event = asyncio.Event()
stop_event = threading.Event()
connected_clients = set()
consumer_threads = []
subprocess_ref = None  # Reference to subprocess running start.sh

# Purge or create queues
def purge_rabbitmq_queues():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
    channel = connection.channel()

    for queue_name in QUEUE_NAMES:
        try:
            channel.queue_declare(queue=queue_name, durable=True)
            channel.queue_purge(queue=queue_name)
            print(f"🧹 Purged queue: {queue_name}")
        except pika.exceptions.ChannelClosedByBroker as e:
            print(f"⚠ Could not purge {queue_name}: {e}")
            channel = connection.channel()

    connection.close()

# RabbitMQ Consumer
def rabbitmq_consumer(loop, queue_name):
    def on_message(channel, method_frame, header_frame, body):
        if stop_event.is_set():
            channel.stop_consuming()
            return

        message = f"[{queue_name}] {body.decode()}"
        print(f"Received from RabbitMQ: {message}")

        try:
            full_data = json.loads(body.decode())
            inner_data = list(full_data.values())[0]
            inner_data['Video_id'] = os.path.basename(inner_data.get('Video_id', ''))
            file_name = f"{queue_name}.csv"
            file_exists = os.path.isfile(file_name)
            fieldnames = ['Video_id', 'time_taken', 'timestamp']

            with open(file_name, mode='a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(inner_data)
            print(f"✅ Saved to CSV: {file_name}")
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")

        asyncio.run_coroutine_threadsafe(ws_queue.put(message), loop)
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_consume(queue=queue_name, on_message_callback=on_message)

    print(f"🔁 Starting RabbitMQ consumer for queue: {queue_name}")
    try:
        while not stop_event.is_set():
            channel.connection.process_data_events(time_limit=1)
        channel.stop_consuming()
    except Exception as e:
        print(f"❌ Consumer error ({queue_name}): {e}")
    finally:
        connection.close()
        print(f"🛑 Consumer for {queue_name} stopped.")

# WebSocket server handler
async def websocket_handler(websocket):
    global subprocess_ref
    print(f"Client connected: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Received from client: {message}")
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send("❌ Invalid JSON command")
                continue

            if "start" in data:
                if data["start"] is True:
                    if not start_event.is_set():
                        print("✅ START command received. Starting consumers and publisher...")
                        purge_rabbitmq_queues()
                        stop_event.clear()
                        start_event.set()

                        for queue_name in QUEUE_NAMES:
                            thread = threading.Thread(target=rabbitmq_consumer, args=(asyncio.get_running_loop(), queue_name), daemon=True)
                            thread.start()
                            consumer_threads.append(thread)

                        subprocess_ref = subprocess.Popen(["bash", "./start.sh"])
                        await websocket.send("✅ Consumers and publishers started.")
                    else:
                        await websocket.send("ℹ System already running.")
                elif data["start"] is False:
                    if start_event.is_set():
                        print("🛑 STOP command received. Stopping consumers and running stop.sh...")
                        stop_event.set()
                        start_event.clear()

                        try:
                            subprocess.run(["bash", "./stop.sh"], check=True)
                            print("✅ stop.sh executed")
                        except subprocess.CalledProcessError as e:
                            print(f"❌ Error running stop.sh: {e}")

                        await websocket.send("🛑 System stopped.")
                    else:
                        await websocket.send("ℹ System already stopped.")
                else:
                    await websocket.send("❌ Invalid value for 'start'")
            else:
                await websocket.send("❌ Unknown command")

    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
    finally:
        connected_clients.remove(websocket)

# Broadcaster task
async def ws_broadcaster():
    while True:
        message = await ws_queue.get()
        stale_clients = set()
        for client in connected_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                stale_clients.add(client)
        connected_clients.difference_update(stale_clients)

# Main function
async def main():
    print("🚀 Starting WebSocket Server on ws://0.0.0.0:8768")
    await websockets.serve(websocket_handler, '0.0.0.0', 8768)
    asyncio.create_task(ws_broadcaster())
    print("⏳ Waiting for START command from client...")
    await asyncio.Future()  # Keeps the server running

if __name__ == '__main__':
    asyncio.run(main())
