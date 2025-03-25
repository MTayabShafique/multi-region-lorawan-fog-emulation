
# LoRaWAN-Fog Integration Thesis

## Thesis Title
**An Investigation on the Integration of LoRaWAN into Fog Computing Systems**

## Overview
This thesis explores how LoRaWAN networks can be integrated with fog computing to enable IoT data processing closer to the edge. The system utilizes ChirpStack for LoRaWAN management, EMQX for MQTT messaging, dynamically created fog nodes, and SensIoT components for data handling and persistence.

## Technologies Used

- **LoRaWAN Stack:** Multi Region ChirpStack (App Server, Network Server, Gateway Bridge)
- **Message Broker:** EMQX (multi-node MQTT cluster with HAProxy load balancing)
- **Fog Layer:** Multi Region Fog Nodes
- **Data Layer:** SensIoT (MQTT-based) with InfluxDB 2.x, Prometheus and Memcached buffer
- **Visualization:** Grafana
- **Simulation:** LWN Simulator (simulated devices & gateways)
- **Containerization:** Docker Compose

## Project Structure

```
code/
├── chirpstack-docker/        # ChirpStack Setup
├── fog-nodes/                # Regional Fog Nodes Setup
├── The-SENSIOT-Framework/    # Modified SensIoT stack
├── LoRaWANSimulator/         # LWN simulator
├── Visualization/            # Grafana dashboards
└── README.md
```

## How to Run the System

### 1. Start ChirpStack Stack
```bash
cd chirpstack-docker
docker-compose build automated-metrics
docker compose up -d
```

### 2. Start Fog Node System
```bash
cd ../fog-nodes
docker build -t myorg/fog-node:latest ./fog-node
docker-compose build
docker-compose up -d
```

### 3. Start SensIoT Stack
```bash
cd ../The-SENSIOT-Framework
docker build -t sensiot_image .
docker-compose build
docker-compose up -d
```

### 4. Start Visualization Stack
```bash
cd ../Visualization
docker-compose up -d
```

### 5. Start Simulator
```bash
cd ../LoRaWANSimulator
cd LWN-Simulator_eu868
# Install dependencies
make install-dep
# Build simulator
make build
# Run simulator
./bin/lwnsimulator  # For Linux

# Repeat above steps for each LWN-Simulator_{Region}
```

## Access Web Interfaces

### ChirpStack
- **ChirpStack UI:** http://localhost:8080
- **EMQX Dashboard (ChirpStack):** http://localhost:18083
- **InfluxDB (LoRa Metrics):** http://localhost:8087

### Visualization
- **Grafana:** http://localhost:3005
- **Prometheus:** http://localhost:9091

### LWN Simulators
- **EU868:** http://localhost:9008
- **US915:** http://localhost:9005
- **IN865:** http://localhost:9001
- **RU864:** http://localhost:9003

### Fog Nodes
- **EMQX Dashboard:** http://localhost:18084

### SensIoT Framework
- **InfluxDB:** http://localhost:8086
- **Grafana:** http://localhost:3000
- **Prometheus:** http://localhost:9090/targets

> Default credentials are usually in the `.env` files or official documentation.

## Docker Networks

| Component        | Docker Network Name                  |
|------------------|--------------------------------------|
| ChirpStack       | `chirpstack-docker_lorawan`          |
| Fog Nodes        | `fog-nodes_fog-netwrok`              |
| SensIoT + Fog    | `fog-sensiot_network` (must create)  |
| SensIoT Internal | `the-sensiot-framework_backend`      |

To create the bridge network between SensIoT and Fog Nodes:
```bash
docker network create fog-sensiot_network
```

