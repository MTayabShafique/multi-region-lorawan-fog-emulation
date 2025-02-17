import docker
import os

# Nuclear option: Wipe all Docker-related environment variables
for key in list(os.environ.keys()):
    if key.startswith('DOCKER_'):
        del os.environ[key]

class FogContainerManager:
    def __init__(self, image_name):
        # Use low-level APIClient with explicit configuration
        self.client = docker.APIClient(
            base_url='unix://var/run/docker.sock',  # 2 slashes after unix:
            version='auto',
            timeout=60
        )
        self.docker_client = docker.DockerClient(
            base_url='unix://var/run/docker.sock',
            version='auto'
        )
        self.image_name = image_name
        self.running_containers = {}

    def start_fog_node(self, region):
        if region in self.running_containers:
            print(f"Fog node for region {region} is already running.")
            return self.running_containers[region]

        container_name = f"fog_node_{region}"

        # Check if a container with the desired name already exists.
        existing = self.docker_client.containers.list(all=True, filters={"name": container_name})
        if existing:
            container = existing[0]
            print(f"Container {container_name} already exists. Ensuring it is running.")
            if container.status != "running":
                try:
                    container.start()
                    print(f"Container {container_name} started.")
                except Exception as e:
                    print(f"Error starting existing container {container_name}: {e}")
                    # Optionally, remove and recreate if needed:
                    container.remove(force=True)
                    container = None
            if container:
                self.running_containers[region] = container
                return container

        print(f"Starting fog node container for region: {region}")
        try:
            container = self.docker_client.containers.run(
                self.image_name,
                detach=True,
                environment={"REGION": region},
                name=container_name,
                labels={"region": region},
                restart_policy={"Name": "on-failure"}
            )
        except docker.errors.APIError as e:
            print(f"Error creating container {container_name}: {e}")
            raise
        self.running_containers[region] = container
        return container

    def route_message(self, region, message):
        container = self.running_containers.get(region)
        if not container:
            container = self.start_fog_node(region)
        print(f"Routing message to fog node container for {region}: {message}")
        # Here you can forward the message to the container (e.g., via an HTTP API).

    def stop_fog_node(self, region):
        if region in self.running_containers:
            container = self.running_containers[region]
            print(f"Stopping fog node container for region: {region}")
            container.stop()
            container.remove()
            del self.running_containers[region]

# Create a global instance for use in your application.
fog_manager = FogContainerManager(image_name="myorg/fog-node:latest")
