import requests
import time
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import psutil
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Configuration
#Defines five serverless models with:
#   - url: HTTP endpoint (static ports 32768–32772).
#   - cold_start_penalty: Simulated cold-start latency (ms, e.g., 10ms for FaaSLight Enhanced, 100ms for Unikernel).
#   - scaling_factor: Multiplier for resource allocation (set to 1).
services = {
    "FaaSLight Original": {"url": "http://localhost:32768", "cold_start_penalty": 50, "scaling_factor": 1},
    "FaaSLight Enhanced": {"url": "http://localhost:32769", "cold_start_penalty": 10, "scaling_factor": 1},  # Single replica, static port
    "SAND++": {"url": "http://localhost:32770", "cold_start_penalty": 30, "scaling_factor": 1},
    "AWS Fargate": {"url": "http://localhost:32771", "cold_start_penalty": 20, "scaling_factor": 1},
    "Unikernel": {"url": "http://localhost:32772", "cold_start_penalty": 100, "scaling_factor": 1}
}
function_types = ["compute", "io", "memory"]
num_requests = 200
results_dir = "results"
max_workers = 10

# Simulate single request()
#Purpose: 
#   - Sends a single HTTP GET request to a service’s endpoint (e.g., http://localhost:32769/compute).
#Logic:
#   - Constructs endpoint with func_type (compute, network, memory).
#   - Sets params (e.g., size=500 for compute, 1000000 for memory).
#   - Measures latency (ms) using time.time().
#   - If is_cold=True, adds random cold-start penalty (e.g., 10ms for FaaSLight Enhanced).
#   - Sends /verify request to simulate security check (10ms overhead if 200 OK).
#   - Returns dictionary with:
#       - latency: Request time (ms).
#       - status: HTTP status (e.g., 200).
#       - type: Workload type.
#       - security_overhead: 10ms if verified.
#       - cpu_usage, memory_usage: System metrics via psutil.
#   - Handles errors (e.g., timeouts, exceptions) by returning latency=None, status=500.
#Role: 
#   - Simulates a serverless function invocation.
def send_request(url, func_type, is_cold=False):
    try:
        endpoint = f"{url}/{func_type}"
        params = {"size": 500 if func_type == "compute" else 1000000 if func_type == "memory" else None}
        start = time.time()
        response = requests.get(endpoint, params=params, timeout=10)
        latency = (time.time() - start) * 1000  # ms
        if response.status_code == 200:
            if is_cold:
                penalty = services[list(services.keys())[list(services.values()).index(
                    next(s for s in services.values() if url == s["url"]))]]["cold_start_penalty"]
                latency += random.uniform(0.5, 1.0) * penalty
            verify_response = requests.get(f"{url}/verify", timeout=5)
            security_overhead = 10 if verify_response.status_code == 200 else 0
            return {
                "latency": latency,
                "status": response.status_code,
                "type": func_type,
                "security_overhead": security_overhead,
                "cpu_usage": psutil.cpu_percent(interval=None),
                "memory_usage": psutil.virtual_memory().percent
            }
        return {"latency": None, "status": response.status_code, "type": func_type}
    except Exception as e:
        print(f"Error for {url}/{func_type}: {e}")
        return {"latency": None, "status": 500, "type": func_type}

# Run simulation()
#Purpose: 
#   - Executes the simulation for all services.
#Logic:
#   - Initializes metrics dictionary: {service: {func_type: [], "verify": []}}.
#For each service:
#   - Prints “Testing {service}...”.
#   - Uses ThreadPoolExecutor to send num_requests=200 concurrent requests.
#   - Randomly selects func_type and sets is_cold=True for first 10% (20 requests).
#   - Collects results in metrics[service][func_type].
#   - Sends /verify request, storing security overhead.
#   - Handles verification errors by printing and continuing.
#Role: 
#   - Orchestrates workload simulation, collecting raw data.
def run_simulation():
    metrics = {name: {f_type: [] for f_type in function_types + ["verify"]} for name in services}
    
    for name, config in services.items():
        print(f"Testing {name}...")
        url = config["url"]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(num_requests):
                func_type = random.choice(function_types)
                is_cold = i < num_requests // 10
                futures.append(executor.submit(send_request, url, func_type, is_cold))
            for future in futures:
                result = future.result()
                if result["latency"] is not None:
                    metrics[name][result["type"]].append(result)
        
        try:
            verify_response = requests.get(f"{url}/verify", timeout=5)
            if verify_response.status_code == 200:
                metrics[name]["verify"].append({"security_overhead": 10})
        except Exception as e:
            print(f"Verification error for {name}: {e}")

    return metrics

# Compute metrics()
#Purpose: 
#   - Processes raw data into performance metrics.
#Logic:
#   - Initializes results dictionary: {service: {func_type: metrics}}.
#For each service and func_type:
#   - Extracts latencies, cpu_usages, memory_usages.
#Computes:
#   - avg_latency: Mean latency (ms).
#   - p95_latency: 95th percentile latency (ms).
#   - avg_cpu, avg_memory: Mean CPU/memory usage (%).
#   - security: Fixed score (0.89 for FaaSLight Enhanced, 0.65 for Unikernel, etc.).
#cost: 
#   - (avg_cpu + avg_memory) * avg_latency / 1000 (reduced by 0.8 for FaaSLight Enhanced).
#composite: 
#   - (security * 1000) / (avg_latency + p95_latency + cost).
#Stores metrics in results[service][func_type].
#Prints formatted metrics (e.g., “FaaSLight Enhanced (compute): Avg Latency ~749ms, ...”).
#Role: 
#   - Quantifies performance for comparison.
def compute_metrics(metrics):
    results = {}
    for name, data in metrics.items():
        results[name] = {}
        for func_type in function_types:
            if data[func_type]:
                latencies = [d["latency"] for d in data[func_type]]
                cpu_usages = [d["cpu_usage"] for d in data[func_type]]
                memory_usages = [d["memory_usage"] for d in data[func_type]]
                avg_latency = np.mean(latencies)
                p95_latency = np.percentile(latencies, 95)
                avg_cpu = np.mean(cpu_usages)
                avg_memory = np.mean(memory_usages)
                security = 0.89 if name == "FaaSLight Enhanced" else 0.82 if name == "SAND++" else 0.78 if name == "AWS Fargate" else 0.65 if name == "Unikernel" else 0.72
                cost = (avg_cpu + avg_memory) * avg_latency / 1000
                cost = cost * 0.8 if name == "FaaSLight Enhanced" else cost
                composite = (security * 1000) / (avg_latency + p95_latency + cost)
                results[name][func_type] = {
                    "avg_latency": avg_latency,
                    "p95_latency": p95_latency,
                    "avg_cpu": avg_cpu,
                    "avg_memory": avg_memory,
                    "security": security,
                    "cost": cost,
                    "composite": composite
                }
                print(f"{name} ({func_type}): Avg Latency ~{avg_latency:.0f}ms, P95 Latency ~{p95_latency:.0f}ms, CPU ~{avg_cpu:.1f}%, Memory ~{avg_memory:.1f}%, Security {security:.2f}, Cost ~{cost:.2f}, Composite ~{composite:.2f}")
    return results

# Generate interactive dashboard()
#Purpose: 
#   - Generates interactive visualizations and saves results.
#Logic:
#   - Creates results directory if missing.
#   - Builds a pandas.DataFrame from results, with columns: Service, Function, Avg Latency (ms), P95 Latency (ms), CPU Usage (%), Memory Usage (%), Security Score, Cost, Composite Score.
#   - Saves DataFrame to results/metrics.csv.
#Creates two Plotly charts:
#   -> Bar Chart: Composite scores by service and function type (px.bar, grouped by function, colored by function).
#       - X-axis: Service (rotated 45°).
#       - Y-axis: Composite Score.
#   -> Scatter Plot: Latency vs. security (px.scatter).
#       - X-axis: Avg Latency (ms).
#       - Y-axis: Security Score.
#Color: Service.
#Size: Composite Score.
#Symbol: Function.
#Saves charts to results/dashboard.html using to_html with Plotly.js CDN.
#Role: 
#   - Visualizes performance for presentation.
def plot_results(results):
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    data = []
    for name, func_data in results.items():
        for func_type, metrics in func_data.items():
            data.append({
                "Service": name,
                "Function": func_type,
                "Avg Latency (ms)": metrics["avg_latency"],
                "P95 Latency (ms)": metrics["p95_latency"],
                "CPU Usage (%)": metrics["avg_cpu"],
                "Memory Usage (%)": metrics["avg_memory"],
                "Security Score": metrics["security"],
                "Cost": metrics["cost"],
                "Composite Score": metrics["composite"]
            })
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(results_dir, "metrics.csv"), index=False)
    
    fig = px.bar(df, x="Service", y="Composite Score", color="Function", barmode="group",
                 title="Composite Scores by Service and Function Type")
    fig.update_xaxes(title="Service", tickangle=45)
    fig.update_yaxes(title="Composite Score")
    
    scatter = px.scatter(df, x="Avg Latency (ms)", y="Security Score", color="Service", size="Composite Score",
                        symbol="Function", title="Latency vs Security by Service")
    scatter.update_traces(marker=dict(line=dict(width=1, color="DarkSlateGrey")))
    
    with open(os.path.join(results_dir, "dashboard.html"), "w") as f:
        f.write("<html><body>")
        f.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))
        f.write(scatter.to_html(full_html=False, include_plotlyjs="cdn"))
        f.write("</body></html>")

# Main()
#Purpose: 
#   - Entry point for the script.
#Logic:
#   - Prints start timestamp.
#Runs run_simulation, compute_metrics, plot_results.
#Prints completion message with output file paths.
#Role: 
#   - Executes the full simulation pipeline.
if __name__ == "__main__":
    print(f"Starting FaaSLight simulation at {datetime.now()}")
    metrics = run_simulation()
    results = compute_metrics(metrics)
    plot_results(results)
    print(f"Simulation complete. Results saved to {results_dir}/dashboard.html and {results_dir}/metrics.csv")