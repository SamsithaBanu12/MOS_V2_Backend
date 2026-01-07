# OD Service

Orbit Determination (OD) Service providing ADCS position/velocity data access and satellite tracking capabilities.

## Features

- **OD Data API**: Query position and velocity data from PostgreSQL
- **Satellite Tracking API**: Convert TLE files to WGS84 coordinates for UI tracking
- **Automated Scheduler**: Daily cron job for data export and OD executable processing
- **Real-time Logs**: Stream executable output in real-time

## Project Structure

```
OD_service/
├── api/                        # API route modules
│   ├── od_data.py             # OD data endpoints
│   └── satellite.py           # Satellite tracking endpoints
├── db/                        # Database configuration
│   └── db.py                  # Database connection and config
├── utils/                     # Utility modules
│   ├── od_data_handler.py     # Data fetching and CSV export
│   ├── tle/                   # TLE conversion utilities
│   │   └── tle_converter.py   # TLE to WGS84 converter
│   └── scheduler/             # Scheduled jobs
│       └── scheduler.py       # Daily OD export scheduler
├── main.py                    # FastAPI application
└── requirements.txt           # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd Backend/Netra_Backend1/netra_backend/services/OD_service
pip install -r requirements.txt
```

### 2. Configure Database

Set environment variables (optional, defaults provided):

```bash
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=centraDB
DB_USER=root
DB_PASSWORD=root
```

### 3. Start the Server

```bash
python main.py
```

Server will start on `http://localhost:8030`

## API Endpoints

### Root Endpoints

**GET /** - Root endpoint with API overview
**GET /health** - Health check
**GET /docs** - Interactive API documentation (Swagger UI)

### OD Data Endpoints

**GET /od/data**

Fetch position and velocity data within a time range.

**Query Parameters:**
- `start_time` (required) - ISO format timestamp (e.g., `2026-03-01T10:00:00`)
- `end_time` (required) - ISO format timestamp

**Example:**
```bash
curl "http://localhost:8030/od/data?start_time=2026-03-01T10:00:00&end_time=2026-03-01T12:00:00"
```

**Response:**
```json
{
  "position": [...],
  "velocity": [...],
  "csv_exported": "path/to/measurement.csv",
  "record_count": {
    "position": 6771,
    "velocity": 6771
  },
  "executable_result": {
    "success": true,
    "return_code": 0
  }
}
```

### Satellite Tracking Endpoints

**GET /satellite/track**

Get satellite tracking data from TLE files converted to WGS84 coordinates.

**Query Parameters:**
- `tle_file` (optional) - Path to specific TLE file (auto-detects latest if not provided)
- `time_points` (optional, default: 100) - Number of position points (10-1000)
- `duration_hours` (optional, default: 24) - Propagation duration (1-168 hours)

**Example:**
```bash
# Use latest TLE with default settings
curl "http://localhost:8030/satellite/track"

# Custom time points and duration
curl "http://localhost:8030/satellite/track?time_points=200&duration_hours=48"
```

**Response:**
```json
{
  "success": true,
  "satellite_name": "OD_TLE_20260302T120000",
  "time_points": 100,
  "duration_hours": 24,
  "positions": [
    {
      "timestamp": "2025-12-18T10:00:00Z",
      "latitude": 45.123,
      "longitude": -122.456,
      "altitude_km": 550.0,
      "velocity_km_s": {
        "x": 7.5,
        "y": 0.2,
        "z": -0.1
      }
    }
  ],
  "metadata": {
    "line1": "1 99999U DST-01...",
    "line2": "2 99999  97.2776...",
    "generated_at": "2025-12-18T10:00:00Z"
  }
}
```

## Scheduler

Automated daily data export at 12:00 AM UTC.

### Run Scheduler

```bash
cd utils/scheduler

# Daily schedule (runs at midnight UTC)
python scheduler.py

# Immediate one-time run
python scheduler.py --now

# Custom time range
python scheduler.py --now --start-time "2026-03-01 10:00:00" --end-time "2026-03-02 12:00:00"

# Test mode (runs every minute)
python scheduler.py --test
```

### Scheduler Features

- ✅ Automatic last 24-hour data export
- ✅ OD executable auto-run after CSV creation
- ✅ Real-time log streaming
- ✅ Configurable time ranges
- ✅ Error handling and reporting

## Components

### Database Module (`db/db.py`)

- `DatabaseConfig` - Centralized DB configuration
- `DatabaseConnection` - Connection management
- `Tables` - Table name constants

### Data Handler (`utils/od_data_handler.py`)

- `fetch_data()` - Query data from PostgreSQL
- `write_measurements_csv()` - Export data to CSV
- `run_od_executable()` - Run OD_V2.0.0.exe with real-time logs
- `fetch_od_data()` - Orchestrate data fetch, export, and processing

### TLE Converter (`utils/tle/tle_converter.py`)

- `parse_tle_file()` - Parse TLE file format
- `tle_to_wgs84()` - Convert TLE to WGS84 using SGP4
- `find_latest_tle()` - Auto-detect latest TLE file
- `get_satellite_track()` - Generate satellite tracking data

## Development

### Testing the API

Visit `http://localhost:8030/docs` for interactive API documentation.

### Project Dependencies

- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **psycopg2-binary** - PostgreSQL adapter
- **APScheduler** - Job scheduling
- **pytz** - Timezone handling
- **sgp4** - Satellite propagation
- **numpy** - Numerical operations

## Notes

- Data filtering uses the `epoch` column (actual measurement timestamp)
- CSV files are exported to `utils/OD/OD-Release/measurement.csv`
- OD executable runs automatically after CSV creation
- TLE files are auto-detected from `utils/OD/OD-Release/Outputs_Tests/tle/`
- Logs stream in real-time with UTF-8 encoding support

## Troubleshooting

**Import errors**: Ensure you're in the OD_service directory when running scripts

**Database connection**: Check environment variables and PostgreSQL service

**TLE file not found**: Ensure TLE files exist in the expected directory

**Unicode errors**: Already handled with UTF-8 encoding in subprocess calls
