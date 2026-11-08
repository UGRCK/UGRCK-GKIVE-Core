import asyncio
import time
import random
import httpx

TARGET_URL = 'http://127.0.0.1:8080/api/v1/kernel/execute'
TOTAL_CONCURRENT_REQUESTS = 5000
MAX_PARALLEL_WORKERS = 100

async def send_flux_pulse(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, request_id: int) -> dict:
    is_violation = random.random() < 0.20  # Inject 20% boundary breach attempts
    
    if is_violation:
        payload = {
            "target_system": {
                "identifier": f"Node_Breach_{request_id}",
                "domain": "Natural_Biophysical",
                "state": [0.00, 0.85, 0.90, 0.95],
                "flows": {"stream_1": [0.0, 0.1, 0.1, 0.1]},
                "lower_bounds": [1e-9, 1e-9, 1e-9, 1e-9],
                "temporal_horizon": 50
            },
            "control_vectors": {
                "gradient": [1.0, 1.0, 1.0, 1.0],
                "dynamic_matrix": [1.0, 1.0, 1.0, 1.0]
            }
        }
    else:
        payload = {
            "target_system": {
                "identifier": f"Node_Valid_{request_id}",
                "domain": "Conscious_Capability",
                "state": [0.88, 0.92, 0.85, 0.90],
                "flows": {"stream_1": [0.05, 0.05, 0.05, 0.05]},
                "lower_bounds": [1e-9, 1e-9, 1e-9, 1e-9],
                "temporal_horizon": 50
            },
            "control_vectors": {
                "gradient": [1.0, 1.0, 1.0, 1.0],
                "dynamic_matrix": [1.0, 1.0, 1.0, 1.0]
            }
        }

    async with semaphore:
        start_time = time.perf_counter()
        try:
            response = await client.post(TARGET_URL, json=payload, timeout=10.0)
            latency = (time.perf_counter() - start_time) * 1000
            
            if response.status_code == 200:
                return {'success': True, 'state': 'GREEN_STATUS', 'latency': latency}
            elif response.status_code == 400:
                return {'success': True, 'state': 'RED_BOLT', 'latency': latency}
            return {'success': False, 'error': f'Status {response.status_code}', 'latency': latency}
        except Exception as e:
            return {'success': False, 'error': str(e), 'latency': (time.perf_counter() - start_time) * 1000}

async def execute_systemic_load_test():
    semaphore = asyncio.Semaphore(MAX_PARALLEL_WORKERS)
    limits = httpx.Limits(max_keepalive_connections=MAX_PARALLEL_WORKERS, max_connections=MAX_PARALLEL_WORKERS)
    
    print(f"[🔥 STRESS ENGINE ACTIVE] Injecting {TOTAL_CONCURRENT_REQUESTS} parallel flux pulses into UGRCK Gateway...")
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [send_flux_pulse(client, semaphore, i) for i in range(TOTAL_CONCURRENT_REQUESTS)]
        results = await asyncio.gather(*tasks)
        
    successful_calls = [r for r in results if r.get('success')]
    red_bolts = [r for r in successful_calls if r['state'] == 'RED_BOLT']
    print(f"-> Total Flux Packets Processed: {len(results)}")
    print(f"-> Successfully Contained RED_BOLT Violations: {len(red_bolts)}")

if __name__ == '__main__':
    asyncio.run(execute_systemic_load_test())
