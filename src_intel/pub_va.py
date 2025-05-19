import time
import os
import time
import requests
import csv
import json
import pika
from datetime import datetime
from zoneinfo import ZoneInfo
from multiprocessing import Pool

# Configuration
ENDPOINT = "http://localhost:8000/v1/chat/completions"
TRANSCRIPTS_DIR = "/home/amd/Sarthak/transcripts1"
SUMMARIES_DIR = "summaries"
LOG_FILE = "summary_log.csv"

def get_connection():
    # print("Making connection with rabbitmq.....................................")
    RABBITMQ_HOST = "10.216.179.127"
    RABBITMQ_USER = "admin"
    RABBITMQ_PASSWORD = "Infobell@123"
    CREDENTIALS = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    CONNECTION_PARAMS = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=CREDENTIALS)

    connection_obj = pika.BlockingConnection(CONNECTION_PARAMS)
    channel_obj = connection_obj.channel()

    return connection_obj, channel_obj

def send_message(channel, msg):
      queue_name = os.getenv("RABBITMQ_QUEUE", "VA_INTEL")
      channel.queue_declare(queue=queue_name, durable=True)
      channel.basic_publish(exchange='', routing_key=queue_name, body=msg)
    #   print(f"Sent: {msg} to Queue: {queue_name}")

_, channel = get_connection()

def build_payload(transcript: str) -> dict:
    prompt = f"""
You are an intelligent assistant designed to summarize spoken transcripts concisely and accurately.

Below is the transcript of an audio file:

--- Transcript Start ---
{transcript}
--- Transcript End ---

Your task:
1. Summarize the entire transcript in **no more than 128 words**.
2. Summary should be in **English Language only**.
3. Capture the main ideas clearly and concisely, avoiding repetition or filler content.
4. Provide **only** the summary and a list of **5 to 6 relevant keywords** — nothing else.
5. Do **not** include any internal thoughts, explanation of steps, or formatting outside the structure shown below.

Return your output in exactly the following format (no extra text before or after):

Summary:
<your 128-word summary here>

Keywords:
<comma-separated list of 5-6 keywords>
"""


    return {
        "model": "/app/models/DeepSeek-R1-Distill-Qwen-1.5B",
        "messages": [{"role": "system", "content": prompt}],
        "temperature": 0,
        "max_tokens": 512
    }

def summarize_file(value_in) :
    all_files = sorted([
       os.path.join(TRANSCRIPTS_DIR, f)
       for f in os.listdir(TRANSCRIPTS_DIR)
       if f.endswith(".txt")
    ])
    # print(all_files)

    if not all_files:
        print("❌ No transcript files found.")
        return

    total_loops = 1000
    while (total_loops >= 0):

        for file in all_files:
            # print(file)
            # file_name = os.path.basename(file)
            # summary_path = os.path.join(SUMMARIES_DIR, file_name.replace(".txt", "_summary.txt"))

            try:
                with open(file, "r", encoding="utf-8") as f:
                    transcript = f.read()

                payload = build_payload(transcript)
                start_time = time.perf_counter()
                response = requests.post(ENDPOINT, json=payload)
                duration = round(time.perf_counter() - start_time, 2)
                timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

                if response.status_code == 200:
                    summary = response.json()["choices"][0]["message"]["content"]
                    # with open(summary_path, "w", encoding="utf-8") as out:
                    #     out.write(summary)

                    report_data = {
                        "VA_INTEL":{
                        "Video_id": str(file),
                        "time_taken": f"{duration:.2f}",
                        "timestamp": timestamp
                        }
                    }

                    # print("sending the data...........................")
                    send_message(channel, json.dumps(report_data))

                else:
                    error = f"HTTP {response.status_code}: {response.text}"
                    continue
            except Exception as e:
                return {
                    "video_id": str(file),
                    "status": "Failed",
                    "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
                    "time_taken": 0,
                    "error": str(e)
                }

        total_loops = total_loops - 1

    return "SUCCESS"

def append_single_log(result):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "video_id", "status", "time_taken", "error"])
        writer.writerow([
            result["timestamp"],
            result["video_id"],
            result["status"],
            result["time_taken"],
            result.get("error", "")
        ])

# def process_all_transcripts():
# #     all_files = sorted([
# #        os.path.join(TRANSCRIPTS_DIR, f)
# #        for f in os.listdir(TRANSCRIPTS_DIR)
# #        if f.endswith(".txt")
# #    ])
#     # print(all_files)
#     all_files = ["./transcripts2/049_JOYSDqJdiro.txt"]
#
#     input_files = NUM_PARALLEL*all_files
#
#     if not all_files:
#         print("❌ No transcript files found.")
#         return
#
#     # for v1 in all_files:
#     #     print(v1)
#     #     input_files = NUM_PARALLEL*v1
#     with Pool(processes=NUM_PARALLEL) as pool:
#         for result in pool.map(summarize_file, input_files):
#             append_single_log(result)
#             print(result)
#             if result["status"] == "Success":
#                 print(f"[✓] {result['video_id']} done in {result['time_taken']}s")
#             else:
#                 print(f"[✗] {result['video_id']} failed: {result.get('error', 'Unknown Error')}")

def main():
    os.makedirs(SUMMARIES_DIR, exist_ok=True)

    amd=23
    intel=15

    # CHANGE only here
    parallelization = intel

    #amd
    inputs = list(range(parallelization))  # Sample input data

    #intel
    # inputs = list(range(intel))  # Sample input data

    # Create a pool with 16 parallel workers
    with Pool(processes=parallelization) as pool:
        # Map the function to the input list
        results = pool.map(summarize_file, inputs)
        #parallel process worker_function(0), worker_function(1)

    print("Results:", results)


if __name__ == "__main__":
    main()
