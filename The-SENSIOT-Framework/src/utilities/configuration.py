import json
import os


class ConfigurationReader:

    @staticmethod
    def get():
        try:
            # Fetch the CONFIG environment variable
            configuration = os.environ['CONFIG']

            # If CONFIG is a file path, load it as JSON
            if os.path.isfile(configuration):
                with open(configuration, "r") as file:
                    config = json.load(file)
                    return config

            # If CONFIG is a JSON string, parse it
            print(configuration)
            config = json.loads(configuration.replace("True", "true").replace("False", "false").replace("\'", "\""))
            return config

        except KeyError:
            # Handle case where CONFIG is not set
            raise EnvironmentError(
                "CONFIG environment variable is not set. Please set it to a valid file path or JSON string.")

        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            raise ValueError(f"Invalid JSON in CONFIG: {e}")

        except Exception as e:
            # Handle all other exceptions
            raise RuntimeError(f"Error loading configuration: {e}")
