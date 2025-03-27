
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
docker build -t myorg/fog-node:latest .
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
| SensIoT Internal | `the-sensiot-framework_backend`      |

---

## Important Steps for Testbed Configuration

# LoRaWAN Simulation Setup using LWN Simulator & ChirpStack

This README provides complete instructions to set up and integrate **LWN Simulator** with **ChirpStack** for simulating end-to-end LoRaWAN communication with virtual gateways and devices.

---

## LWN Simulator Setup

###  Create a Virtual Device

1. Go to `Devices > Add new device`.
2. In the **General** tab:
   - ✅ Check **Active**
   - Set a **Name** (e.g., `Test-dev-01`)
   - Click the 🔄 icon to generate a **DevEUI**
   - Select a **Region** (e.g., `EU868`)
   - Click **Save**

3. In the **Activation** tab:
   - ✅ Check **OTAA supported**
   - Click 🔄 to generate the **AppKey**
   - (Other fields like `DevAddr`, `NwkSKey`, `AppSKey` are auto-filled or unused for OTAA)

4. In **Frame’s settings**:
   - `Data Rate`: 0
   - `FPort`: 1
   - `Retransmission`: 1
   - `FCnt`: 1
   - ✅ Disable `FCntDown` validation

5. In **Features**:
   - ✅ Enable ADR
   - `Range Antenna`: 10000

6. In the **Payload** tab:
   - `Uplink Interval`: `10` seconds
   - Select `ConfirmedDataUp`
   - Payload:
     ```json
     {"temperature": 30, "humidity": 10}
     ```

---

###  Create a Virtual Gateway

1. Go to `Gateways > Add Gateway`
2. Ensure **Virtual Gateway** tab is selected
3. Fill in:
   - ✅ Active
   - **Name**: e.g., `Dev-Gateway-1`
   - **MAC Address**: e.g., `a365de9c7bea8e5b` (must match what you’ll use in ChirpStack)
   - **KeepAlive**: 30 (default)
   - (Optional) Set location via the map or coordinates

4. Click **Save**

---

# ChirpStack Integration

To mirror your simulated devices and gateways in ChirpStack, follow the steps below:

---


# Creating Device Profiles: EU868/US915/RU864/IN865

The following device profile is configured for the LoRaWAN regions using ChirpStack.

## General Settings for EU868 

| Field                           | Value                      | Description                                                             |
|---------------------------------|----------------------------|-------------------------------------------------------------------------|
| **Name**                        | `Device-Profile-EU868`     | Descriptive name for this device profile.                               |
| **Region**                      | `EU868`                    | Specifies the LoRaWAN frequency plan (EU868).                           |
| **Region configuration**        | (leave blank if not used)  | Used for custom regional settings.                                      |
| **MAC version**                 | `LoRaWAN 1.0.3`            | LoRaWAN MAC specification version.                                      |
| **Regional parameters revision**| `A`                        | LoRaWAN Regional Parameters revision.                                   |
| **ADR algorithm**               | `Default ADR algorithm`    | Adaptive Data Rate algorithm used (LoRa only).                          |
| **Flush queue on activate**     | `Enabled`                  | Clears any queued downlinks when the device (re)joins.                  |
| **Expected uplink interval**    | `3600` (seconds)           | Expected interval between uplinks in seconds.                           |
| **Device-status request freq.** | `1` (req/day)              | Number of status requests sent daily to the device.                     |
| **Allow roaming**               | `Disabled`                 | Determines whether the device can roam between different networks.      |
| **RX1 Delay**                   | `0` (system default)       | Receive window delay (in seconds) after uplink transmission.            |

## Usage

1. **Create or select** this device profile in ChirpStack.
2. **Assign** the profile to any devices operating in the EU868 region with LoRaWAN 1.0.3.

---

### Configuring ChirpStack Device Profiles

To enable **LoRa metrics processing** and **message decoding**, configure **Device Profiles** correctly for each region.

---

#### Step 1: Add the JavaScript Decoder Function

1. Open **ChirpStack UI** at [http://localhost:8080](http://localhost:8080).
2. Navigate to **Device Profiles**.
3. Edit or create the Device Profile for your region (e.g., `EU868`, `US915_0`, etc.).
4. Go to the **"CODEC"** tab.
5. Choose **JavaScript functions** as the codec type.
6. Paste the following into the **Uplink decoder**:

```javascript
function decodeUplink(input) {
  var bytes = input.bytes;
  var fPort = input.fPort;
  
  // Convert byte array to string
  var text = String.fromCharCode.apply(null, bytes);
  var decoded = {};
  var warnings = [];
  var errors = [];

  // Try parsing as standard JSON first
  try {
    decoded = JSON.parse(text);
  } catch (e) {
    // If parsing fails, try replacing single quotes with double quotes
    warnings.push("Initial JSON.parse failed, attempting to replace single quotes with double quotes.");
    var modified = text.replace(/'/g, '"');
    try {
      decoded = JSON.parse(modified);
    } catch (e2) {
        errors.push("Failed to parse JSON even after modifying quotes: " + e2);
    }
  }

  return {
    data: decoded,
    warnings: warnings,
    errors: errors
  };
}
```

7. Click **Submit** to save.

---

#### Step 2: Add Region Tag

1. In the same **Device Profile**, scroll to the **Tags** section.
2. Add the following tag:

| Key         | Value     |
|-------------|-----------|
| region_name | eu868 / us915_0 / ru864 / in865 |

Repeat for each region with the appropriate value.

---

#### Summary: Regional Device Profiles

| Region      | Device Profile Name | region_name Tag |
|-------------|----------------------|------------------|
| EU868       | EU868 Profile         | eu868           |
| US915_0     | US915 Profile         | us915_0         |
| RU864       | RU864 Profile         | ru864           |
| IN865       | IN865 Profile         | in865           |

---

### Step 2: Create Gateway in ChirpStack

1. Go to **Gateways > Add Gateway**
2. Fill in:

| Field           | Value                         |
|-----------------|-------------------------------|
| **Gateway ID**  | `a365de9c7bea8e5b` (same as LWN) |
| **Name**        | `Dev-Gateway-1`               |
| **Network Server** | (your default server)      |

3. (Optional) Set coordinates or description
4. Click **Submit**

---

###  Step 3: Create Application

1. Navigate to **Applications**
2. Click **Add Application**
3. Set:
   - **Name**: `simulated-app`
   - **Service Profile**: Default or custom
   - Leave **Payload Codec** as `None`
4. Click **Submit**

---

### Step 4: Add Devices Under Application

1. Open your application → click **Add Device**
2. Fill in:

| Field          | Value                     |
|----------------|---------------------------|
| **Device EUI** | Same as in LWN Simulator  |
| **Device Name**| `Test-dev-01`             |
| **Device Profile** | `Device-Profile-EU868` |

3. In the **Keys (OTAA)** tab:
   - Paste the **AppKey** used in LWN Simulator

4. Click **Submit**

---

## Verifying Operation

- Start the device in **LWN Simulator**
- Check ChirpStack under:
  - **Device Data** for application payloads
  - **Live LoRaWAN Frames**
  - **Gateways > Last Seen**

Uplink messages from LWN Simulator should now be visible in ChirpStack.

---

# Gateway Bridge Configuration (**EMQX Dashboard (ChirpStack):** http://localhost:18083)

This describes the minimal settings needed to bridge local MQTT messages to a remote MQTT broker.

## Basic Bridge Settings

| Field                   | Value                            | Description                                                   |
|-------------------------|----------------------------------|---------------------------------------------------------------|
| **Name**               | `gateway-bridge`                 | A descriptive name for this gateway bridge.                  |
| **MQTT Broker**         | `fog-nodes_haproxy_1:1883`       | Hostname (or IP) and port of the remote MQTT broker.         |
| **MQTT Version**        | `v3.1.1`                         | MQTT protocol version.                                       |
| **Keep Alive**          | `300 (seconds)`                  | Interval at which the client PINGs the broker.               |
| **Message Retry Interval** | `15 (seconds)`                | Retry interval for message delivery failures.                |
| **Clean start**         | `Enabled`                        | Clear session state on reconnect.                            |
| **Enable TLS**          | `Disabled`                       | Toggle TLS if secure connections are required.               |
| **Bridge Mode**         | `Disabled`                       | Controls dynamic bridging rules (set to your needs).         |

## Egress Setup

| Field           | Value                                         | Description                                                                   |
|-----------------|-----------------------------------------------|-------------------------------------------------------------------------------|
| **Egress**      | `Enabled`                                     | Forwards messages from the local broker to the remote broker.                 |
| **Local Topic** | `application/+/device/+/event/up`            | Topic on the local broker to capture and forward.                             |
| **Remote Topic**| `region/${payload.regionConfigId}/${topic}`   | Dynamically builds the remote topic using the payload’s `regionConfigId`.     |
| **QoS**         | `0`                                           | “At most once” delivery.                                                      |
| **Retain**      | `false`                                       | Do not retain messages on the remote broker.                                  |
| **Payload**     | `${payload}`                                  | Forwards the entire original message payload.                                 |

---



