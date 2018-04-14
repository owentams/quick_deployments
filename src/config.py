from docker import DockerClient

class Config():
    """Configuration values. Static object."""
    client = DockerClient('unix://var/run/docker.sock', version='1.37')

Config.client.version()['ApiVersion']
