import docker
import os
import time

# Remove any conflicting Docker environment variables
#for key in list(os.environ.keys()):
    #if key.startswith('DOCKER_'):
        #del os.environ[key]


class FogContainerManager:
    def __init__(self, image_name, mqtt_publisher=None):
        """
        image_name: The Docker image name to create fog node containers.
        mqtt_publisher: optional reference to an MQTT publisher (e.g. FogMQTTRouter).
        """
        self.docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock', version='auto')
        self.image_name = image_name
        self.network_name = "dynamic_fog_network"
        self.running_containers = {}
        self.mqtt_publisher = mqtt_publisher

    def ensure_network(self):
        """Ensure the Docker network exists and avoid re-creation conflicts."""
        networks = self.docker_client.networks.list()
        existing_networks = [net.name for net in networks]

        if self.network_name in existing_networks:
            print(f"✅ Network {self.network_name} already exists, skipping creation.")
            return

        print(f"🚀 Creating network {self.network_name}...")
        self.docker_client.networks.create(self.network_name, driver="bridge")

    def get_running_container(self, region):
            """Check if a fog node container already exists and is running."""
            container_name = f"fog_node_{region}"
            existing = self.docker_client.containers.list(all=True, filters={"name": container_name})

            if existing:
                container = existing[0]  # Get first found
                if container.status == "running":
                    print(f"✅ Fog node {container_name} is already running.")
                    return container
                else:
                    print(f"🔄 Restarting stopped container {container_name}...")
                    container.start()
                    return container
            return None

    def start_fog_node(self, region):
        """Ensure a fog node is running for the given region."""
        container_name = f"fog_node_{region}"
        self.ensure_network()

        # Check if already running
        running_container = self.get_running_container(region)
        if running_container:
            self.running_containers[region] = running_container
            return running_container

        print(f"🚀 Creating fog node container for region: {region}")
        try:
            container = self.docker_client.containers.run(
                self.image_name,
                detach=True,
                environment={
                    "FOG_REGION": region,
                    "MQTT_BROKER": "mqtt",
                    "MQTT_PORT": "1883",
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
        return container

    def route_message(self, region, message):
        """Route messages to the appropriate fog node and publish via MQTT."""
        if region not in self.running_containers:
            print(f"⚠️ No active fog node for region {region}, checking container status...")
            self.start_fog_node(region)

        container = self.running_containers.get(region)
        if container:
            print(f"📨 Routing message to fog node {container.name} for region {region}: {message}")

            # If we have an MQTT publisher, also publish this message to the relevant topic
            if self.mqtt_publisher is not None:
                self.mqtt_publisher.route_message(region, message)

    def stop_fog_node(self, region):
        """Stop and remove a fog node container for a region."""
        if region in self.running_containers:
            container = self.running_containers[region]
            print(f"🛑 Stopping and removing fog node container for region: {region}")
            container.stop()
            container.remove()
            del self.running_containers[region]

# Create a global instance for use in your application.
fog_manager = FogContainerManager(image_name="myorg/fog-node:latest")
