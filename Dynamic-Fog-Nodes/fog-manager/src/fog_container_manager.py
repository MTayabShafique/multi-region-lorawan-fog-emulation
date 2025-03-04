import docker
import os
import time

class FogContainerManager:
    def __init__(self, image_name, mqtt_publisher=None):
        self.docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock', version='auto')
        self.image_name = image_name
        # Make sure this network name matches the external network declared in your docker-compose.
        self.network_name = "fog-sensiot_network"
        self.running_containers = {}
        self.mqtt_publisher = mqtt_publisher

    def get_running_container(self, region):
        container_name = f"fog_node_{region}"
        existing = self.docker_client.containers.list(all=True, filters={"name": container_name})
        if existing:
            container = existing[0]
            if container.status == "running":
                print(f"✅ Fog node {container_name} is already running.")
                return container
            else:
                print(f"🔄 Restarting stopped container {container_name}...")
                container.start()
                return container
        return None

    def ensure_container_network(self, container):
        container.reload()
        networks = container.attrs['NetworkSettings']['Networks']
        if self.network_name not in networks:
            print(f"⚠️ Container {container.name} not attached to {self.network_name}. Attaching...")
            try:
                network = self.docker_client.networks.get(self.network_name)
                network.connect(container)
                print(f"✅ Container {container.name} attached to {self.network_name}.")
            except docker.errors.APIError as e:
                print(f"❌ Error attaching container {container.name} to network {self.network_name}: {e}")
        else:
            print(f"✅ Container {container.name} is attached to {self.network_name}.")

    def start_fog_node(self, region):
        container_name = f"fog_node_{region}"
        running_container = self.get_running_container(region)
        if running_container:
            self.running_containers[region] = running_container
            self.ensure_container_network(running_container)
            return running_container

        print(f"🚀 Creating fog node container for region: {region}")
        try:
            container = self.docker_client.containers.run(
                self.image_name,
                detach=True,
                environment={
                    "FOG_REGION": region,
                    "MQTT_BROKER": os.getenv("MQTT_BROKER", "haproxy_fog"),
                    "MQTT_PORT": os.getenv("MQTT_PORT", "1883"),
                    "DOCKER_HOST": "unix:///var/run/docker.sock"
                },
                name=container_name,
                labels={"region": region},
                restart_policy={"Name": "on-failure"},
                network=self.network_name,
                volumes={
                    "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}
                }
            )
            time.sleep(2)
            print(f"✅ Fog node container {container_name} started successfully.")
        except docker.errors.APIError as e:
            print(f"❌ Error creating container {container_name}: {e}")
            return None

        self.running_containers[region] = container
        self.ensure_container_network(container)
        return container

    def route_message(self, region, message):
        if region not in self.running_containers:
            print(f"⚠️ No active fog node for region {region}, checking container status...")
            self.start_fog_node(region)
        container = self.running_containers.get(region)
        if container:
            print(f"📨 Routing message to fog node {container.name} for region {region}: {message}")
            if self.mqtt_publisher:
                self.mqtt_publisher.route_message(region, message)

    def stop_fog_node(self, region):
        if region in self.running_containers:
            container = self.running_containers[region]
            print(f"🛑 Stopping and removing fog node container for region: {region}")
            container.stop()
            container.remove()
            del self.running_containers[region]
