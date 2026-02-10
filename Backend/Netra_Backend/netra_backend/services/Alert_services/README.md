# NETR Alerting System

This system monitors telemetry data and generates alerts based on predefined thresholds.

##  Setup Instructions

### 1. Start External Dependencies
This system integrates with the **Cosmos** project. Ensure the following are running before starting the alerting system:

*   **Cosmos Docker Containers**: Start the Docker containers for the Cosmos project.
*   **Backend Services**: Ensure the backend of the Cosmos project is up and running.

### 2. Start the Alerting System
From the root of `NETR_ALERTING_SYSTEM`, run:
```powershell
docker-compose up --build -d
```

### 3. Testing with Sample Data
To trigger alerts for testing, you need to run the `pub_test.py`/ `pub.py` script located in the backend of the Cosmos project.

**Command:**
```powershell
# Navigate to your backend directory and run:
python pub_test.py / python pub.py
```
*(Common path: `..\MOS_V2\MOS_V2_Backend\pub_test.py` / `..\MOS_V2\MOS_V2_Backend\pub.py`)*

##  Project Structure
*   **`Alert_services/`**: Contains the core microservices that power the alerting pipeline:
    *   **`alert_builder`**: The first stage of the pipeline. It subscribes to raw telemetry data, evaluates it against the threshold rules defined in `config/TM_alert_config.json`, and "builds" alert objects when breaches are detected.
    *   **`alert_worker`**: The orchestration and persistence layer. It receives alerts from the builder, saves them to the PostgreSQL database for historical tracking, and coordinates the hand-off to the notification system.
    *   **`notifier`**: The final stage of the pipeline. It monitors for new alerts and handles the delivery of notifications to end-users (e.g., via Email/SMTP), ensuring mission operators are informed in real-time.
*   **`config/`**: Contains `TM_alert_config.json` where you can define alert thresholds and packet metrics.
*   **`docker-compose.yml`**: Orchestrates the multi-container setup.

