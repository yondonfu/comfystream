import av
import json
import time
import torch
import logging
import asyncio
import argparse
import numpy as np

from comfystream.client import ComfyStreamClient

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


def create_dummy_video_frame(width, height):
    frame = av.VideoFrame()
    dummy_tensor = torch.randn(1, height, width, 3)
    frame.side_data.input = dummy_tensor
    return frame


async def main():
    parser = argparse.ArgumentParser(description="Benchmark ComfyStreamClient workflow execution.")
    parser.add_argument("--workflow-path", default="./workflows/comfystream/tensor-utils-example-api.json", help="Path to the workflow JSON file.")
    parser.add_argument("--num-requests", type=int, default=100, help="Number of requests to send.")
    parser.add_argument("--fps", type=float, default=None, help="Frames per second for FPS-based benchmarking.")
    parser.add_argument("--cwd", default="/workspace/ComfyUI", help="Current working directory for ComfyStreamClient.")
    parser.add_argument("--width", type=int, default=512, help="Width of dummy video frames.")
    parser.add_argument("--height", type=int, default=512, help="Height of dummy video frames.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging (shows progress for each request).")
    parser.add_argument("--warmup-runs", type=int, default=5, help="Number of warm-up runs before benchmarking.")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    with open(args.workflow_path, "r") as f:
        prompt = json.load(f)

    client = ComfyStreamClient(cwd=args.cwd)
    await client.set_prompts([prompt])

    logger.info(f"Starting benchmark with workflow: {args.workflow_path}, requests: {args.num_requests}, resolution: {args.width}x{args.height}, warmup runs: {args.warmup_runs}")

    if args.warmup_runs > 0:
        logger.info(f"Running {args.warmup_runs} warm-up runs...")
        for _ in range(args.warmup_runs):
            frame = create_dummy_video_frame(args.width, args.height)
            client.put_video_input(frame)
            await client.get_video_output()
        logger.info("Warm-up complete.")

    if args.fps is None:
        logger.info("Running sequential benchmark...")
        start_time = time.time()
        round_trip_times = []

        for i in range(args.num_requests):
            frame = create_dummy_video_frame(args.width, args.height)
            request_start_time = time.time()
            client.put_video_input(frame)
            await client.get_video_output()
            request_end_time = time.time()
            round_trip_times.append(request_end_time - request_start_time)
            logger.debug(f"Request {i+1}/{args.num_requests} completed in {round_trip_times[-1]:.4f} seconds")

        end_time = time.time()
        total_time = end_time - start_time
        output_fps = args.num_requests / total_time if total_time > 0 else float('inf')

        # Calculate percentiles for sequential mode
        p50_rtt = np.percentile(round_trip_times, 50)
        p75_rtt = np.percentile(round_trip_times, 75)
        p90_rtt = np.percentile(round_trip_times, 90)
        p95_rtt = np.percentile(round_trip_times, 95)
        p99_rtt = np.percentile(round_trip_times, 99)

        print("\n" + "="*40)
        print("FPS Results:")
        print("="*40)
        print(f"Total requests: {args.num_requests}")
        print(f"Total time:     {total_time:.4f} seconds")
        print(f"Actual Output FPS:{output_fps:.2f}")
        print(f"Total requests:   {args.num_requests}")
        print(f"Total time:       {total_time:.4f} seconds")
        print("\n" + "="*40)
        print("Latency Results:")
        print("="*40)
        print(f"Average: {np.mean(round_trip_times):.4f}")
        print(f"Min:     {np.min(round_trip_times):.4f}")
        print(f"Max:     {np.max(round_trip_times):.4f}")
        print(f"P50:     {p50_rtt:.4f}")
        print(f"P75:     {p75_rtt:.4f}")
        print(f"P90:     {p90_rtt:.4f}")
        print(f"P95:     {p95_rtt:.4f}")
        print(f"P99:     {p99_rtt:.4f}")


    else:
        # This is mainly used to stress test the ComfyUI client, gives us a good idea on how frame skipping etc is working on the client end.
        logger.info(f"Running FPS-based benchmark at {args.fps} FPS...")
        frame_interval = 1.0 / args.fps
        start_time = time.time()

        received_frames_count = 0
        last_output_receive_time = None

        async def collect_outputs_task():
            nonlocal received_frames_count, last_output_receive_time
            while True:
                try:
                    async with asyncio.timeout(5):
                        await client.get_video_output()

                    last_output_receive_time = time.time()
                    received_frames_count += 1
                    logger.debug(f"Received output frame {received_frames_count} at {last_output_receive_time - start_time:.4f} seconds")
                except asyncio.TimeoutError:
                    logger.debug(f"Output collection task timed out after waiting for 5 seconds.")
                    break
                except Exception as e:
                    logger.debug(f"Output collection task finished due to exception: {e}")
                    break

        output_collector_task = asyncio.create_task(collect_outputs_task())

        for i in range(args.num_requests):
            frame = create_dummy_video_frame(args.width, args.height)

            elapsed = time.time() - start_time
            expected_elapsed = i * frame_interval
            sleep_time = expected_elapsed - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            request_send_time = time.time()
            client.put_video_input(frame)

            logger.debug(f"Sent request {i+1}/{args.num_requests} at {request_send_time - start_time:.4f} seconds")

        await output_collector_task

        if last_output_receive_time is not None and last_output_receive_time > start_time:
            total_duration_for_fps = last_output_receive_time - start_time
            output_fps = received_frames_count / total_duration_for_fps
        elif received_frames_count == 0:
            output_fps = 0.0
        else:
             output_fps = float('inf')

        print("\n" + "="*40)
        print("FPS Results:")
        print("="*40)
        print(f"Target Input FPS: {args.fps:.2f}")
        print(f"Actual Output FPS:{output_fps:.2f} ({received_frames_count} frames received)")
        print(f"Total requests:   {args.num_requests}")
        print(f"Total time:       {last_output_receive_time - start_time:.4f} seconds")


if __name__ == "__main__":
    asyncio.run(main())