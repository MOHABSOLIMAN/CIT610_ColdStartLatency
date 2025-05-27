from flask import Flask, jsonify, request
import time
import numpy as np
import hashlib
import random

app = Flask(__name__)

# Simulate compute-intensive task (matrix multiplication)
@app.route('/compute', methods=['GET'])
def compute():
    size = request.args.get('size', default=500, type=int)
    matrix_a = np.random.rand(size, size)
    matrix_b = np.random.rand(size, size)
    start = time.time()
    _ = np.dot(matrix_a, matrix_b)
    latency = time.time() - start
    return jsonify({"type": "compute", "latency": latency, "timestamp": time.time()})

# Simulate I/O-bound task (network delay)
@app.route('/io', methods=['GET'])
def io():
    delay = random.uniform(0.01, 0.05)  # 10-50ms
    time.sleep(delay)
    return jsonify({"type": "io", "latency": delay, "timestamp": time.time()})

# Simulate memory-heavy task (sorting large list)
@app.route('/memory', methods=['GET'])
def memory():
    size = request.args.get('size', default=1000000, type=int)
    data = [random.random() for _ in range(size)]
    start = time.time()
    data.sort()
    latency = time.time() - start
    return jsonify({"type": "memory", "latency": latency, "timestamp": time.time()})

# Security check endpoint
@app.route('/verify', methods=['GET'])
def verify():
    data = str(time.time()).encode()
    hash_value = hashlib.sha256(data).hexdigest()
    time.sleep(0.01)  # Simulate verification overhead
    return jsonify({"hash": hash_value, "timestamp": time.time()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)