# __The SENSIOT Framework__
[![CircleCI](https://circleci.com/gh/uniba-ktr/The-SENSIOT-Framework.svg?style=svg)](https://circleci.com/gh/uniba-ktr/The-SENSIOT-Framework)
[![License](https://img.shields.io/github/license/uniba-ktr/The-SENSIOT-Framework.svg?style=popout)]()
[![](https://images.microbadger.com/badges/version/unibaub/sensiot:latest.svg)](https://microbadger.com/images/unibaub/sensiot:latest "Get your own version badge on microbadger.com")
[![](https://images.microbadger.com/badges/image/unibaub/sensiot:latest.svg)](https://microbadger.com/images/unibaub/sensiot:latest "Get your own image badge on microbadger.com")

[![Docker Stars](https://img.shields.io/docker/stars/unibaub/sensiot.svg?logo=docker)](https://hub.docker.com/r/unibaub/sensiot/)
[![Docker Pulls](https://img.shields.io/docker/pulls/unibaub/sensiot.svg?logo=docker)](https://hub.docker.com/r/unibaub/sensiot/)

## Generalization of a Sensor Monitoring Framework for the Internet-of-Things (Bachelor Thesis)
> Based on: _Environmental Monitoring of Libraries with [MonTreAL](http://dx.doi.org/10.1007/978-3-319-67008-9_52)_

An ever-increasing amount of devices connected over the Internet pave the road towards the realization of the ‘Internet of Things’ (IoT) idea. With IoT, endangered infrastructures can easily be enriched with low-cost, energy-efficient monitoring solutions, thus alerting is possible before severe damage occurs. With _the SENSIOT Framework_, a sensor monitoring framework which runs on commodity single board computers. In addition, our primary objectives are to enable flexible data collection among a computing cluster by migrating virtualization approaches of data centers to IoT infrastructures.

## Repository Structure
Beside the source code this repository automatically builds and pushes new versions to the registry and it includes the _swarm setup_, which contains the whole procedure to deploy the SENSIOT Framework.

## Supported Architectures
This multiarch image supports `amd64`, `i386`, `arm32v6`, `arm64v8`, and `ppc64le` on Linux.

## How to use
### Test Setup (amd64)
Mostly for testing purposes this repository contains a docker compose file to just run the SENSIOT Framework out of the box with a sensor mock as sensor.
```
docker-compose -p sensiot up -d
```

### Run the SENSIOT Framework (amd64/arm)
This repository contains the whole procedure to start the SENSIOT Framework in swarm mode.
```
docker swarm init
cd swarm-setup
make
```
Sensor devices can be added afterwards. Files in `swarm-setup/` can be adjusted to get an individual setup.



## Flow

```
                           o- NsqReader - InfluxDBWriter   - InfluxDB   -o- Chronograf, (Kapacitor)
                           |                                              \
                           |                                               o- Grafana
        USB                |                                              /
         |                 o- NsqReader - PrometheusWriter - Prometheus -o- (Alertmanager)
       Sensor              |
         |                 o- NsqReader - SensorList -o
    SocketWriter           |                          |- memcached - Web
         |                 o- NsqReader - SensorData -o
        [|]                |
         |                 o- NsqAdmin, NsqCli, etc.
    SocketReader           |
         |                 |\
  MetaDataAppender         | NsqLookup
         |                 |/
      NsqWriter --------- Nsq

                                                        (____): not implemented yet
```

## Sensor Configuration
> Notice: only the following sensor drivers are currently implemented

### Temperature And Humidity

#### Sensor Mock
    "mock": {
      "service": "temperature_humidity_sensor",
      "type": "mock",
      "image": "unibaub/sensiot",
      "device": [],
      "command": "",
      "configuration": {
        "sensor_count": <int>,
        "temperature": <float>,
        "humidity": <float>,
        "interval": <int>
      }
    }

#### [ASH2200](https://www.elv.de/elv-funk-aussensensor-ash-2200-fuer-z-b-usb-wde-1-ipwe-1.html)
    "ash2200": {
      "service": "temperature_humidity_sensor",
      "type": "ash2200",
      "image": "unibaub/sensiot",
      "device": ["/dev/ttyUSB0"],
      "command": "",
      "configuration": {
        "device": "/dev/ttyUSB0",
        "baudrate": "9600",
        "timeout": <int>
      }
    }

#### [DHT11/DHT22/AM2302](https://learn.adafruit.com/dht/overview)
    "dht": {
      "service": "temperature_humidity_sensor",
      "type": "dht",
      "image": "unibaub/sensiot",
      "devices": ["/dev/mem"],
      "command": "",
      "configuration": {
        "id": <int>,
        "gpio": <int>,
        "short_type": <11 or 22>,
        "interval": <int>
      }
    }

#### [OpenWeatherMap](https://openweathermap.org/)
    "open_weather_map": {
      "service": "temperature_humidity_sensor",
      "type": "openweathermap",
      "image": "unibaub/sensiot",
      "devices": [],
      "command": "",
      "configuration": {
        "id": <int>,
        "key": <string>,
        "city": <string>,
        "country": <string>,
        "interval": <int>
      }
    }
