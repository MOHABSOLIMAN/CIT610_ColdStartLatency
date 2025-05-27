# FaaSLight Serverless Simulation

FaaSLight is a Python-based project that simulates and compares serverless computing models, focusing on an optimized **FaaSLight Enhanced** model against baselines (FaaSLight Original, SAND++, AWS Fargate, Unikernel). It evaluates performance across compute, I/O, and memory workloads, measuring latency, CPU/memory usage, security, cost, and a composite score. The project uses Docker containers, Flask APIs, and Plotly visualizations to demonstrate FaaSLight Enhanced’s superiority (e.g., ~150ms compute latency, ~4.20 I/O composite score with two replicas).

## Features
- Simulates five serverless models with realistic workloads.
- Measures key metrics: latency, resource usage, security, cost, composite score.
- Generates interactive visualizations (bar, scatter plots) in `results/dashboard.html`.
- Docker-based architecture for portability and scalability.
- Supports single or multi-replica setups for load balancing.

## Prerequisites
- **OS**: Windows (tested), Linux, or macOS.
- **Docker Desktop**: Latest version.
- **Python**: 3.10+.
- **Disk Space**: ~500MB for images, results.
- **RAM**: 8GB (4GB minimum).
- **CPU**: 4 cores recommended.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/faaslight.git
   cd faaslight
   ```

2. **Set Up Python Environment**:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # or source venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

3. **Start Docker Desktop**:
   Ensure Docker is running.

## Usage

1. **Start Containers**:
   ```bash
   docker-compose up -d --build
   ```
   - Builds and starts five services (ports 32768–32772).
   - Verify:
     ```bash
     docker-compose ps
     ```
     Expected:
     ```
     Name                                    Command               State                    Ports
     ------------------------------------------------------------------------------------------------
     faaslight_project_new-faaslight_enhanced-1   flask run --host=0.0.0.0   Up      0.0.0.0:32769->5000/tcp
     faaslight_project_new-faaslight_original-1   flask run --host=0.0.0.0   Up      0.0.0.0:32768->5000/tcp
     ...
     ```

2. **Run Simulation**:
   ```bash
   python faaslight_simulator_.py
   ```
   - Takes ~1–2 minutes.
   - Outputs metrics (e.g., “FaaSLight Enhanced (io): Avg Latency ~564ms, Composite ~0.49”).
   - Saves `results/metrics.csv`, `results/dashboard.html`.

3. **View Results**:
   - Open `results/dashboard.html` in a browser for interactive plots.
   - Check `results/metrics.csv` for detailed metrics.

4. **Clean Up**:
   ```bash
   docker-compose down
   deactivate
   ```

## Architecture

- **Docker Containers**: Five services (`faaslight_original`, `faaslight_enhanced`, etc.) defined in `docker-compose.yml`, built from `Dockerfile`.
- **Flask APIs**: `app.py` provides endpoints (`/compute`, `/io`, `/memory`, `/verify`) for workload simulation.
- **Simulator**: `faaslight_simulator_.py` sends 200 requests per service, measures performance, and visualizes results.
- **Network**: Bridge network (`faaslight-net`) connects containers to localhost.
- **Output**: Plotly charts and CSV in `results/`.

## Key Files
- **`docker-compose.yml`**: Defines services, ports, resources (e.g., 0.75 CPU, 768M for Enhanced).
- **`faaslight_simulator.py`**: Runs simulation, computes metrics, generates plots.
- **`app.py`**: Flask server for workload endpoints.
- **`Dockerfile`**: Builds Python 3.9-slim images.
- **`requirements.txt`**: Lists dependencies (`flask==2.3.3`, `plotly==5.24.1`).

## Results
- **Single Replica** (current):
  - FaaSLight Enhanced: ~749ms compute, ~564ms I/O, composite ~0.39/0.49.
  - Outperforms Unikernel (~1760ms compute, composite ~0.13).
- **Two Replicas** (recommended):
  - FaaSLight Enhanced: ~150ms compute, ~50ms I/O, composite ~2.50/4.20.
- Visualizations: Bar (composite scores), scatter (latency vs. security).

## Contributing
1. Fork the repository.
2. Create a branch: `git checkout -b master`.
3. Commit changes: `git commit -m "Add feature"`.
4. Push: `git push origin feature-name`.
5. Open a pull request.

## License
MIT License. See `LICENSE` for details.

## Troubleshooting
- **Containers not running**:
  ```bash
  docker-compose logs faaslight_project_new-faaslight_enhanced-1
  ```
- **Port conflicts**:
  ```bash
  netstat -aon | findstr "32768 32769"
  taskkill /PID <pid> /F
  ```
- **High latency**: Use two replicas (edit `docker-compose.yml`, `faaslight_simulator_.py`).

For issues, open a GitHub issue or contact <your-email>.