"""Tests for the configuration object."""
from src.config import Config
from docker import DockerClient


class TestConfig():
    """Tests for the configuration object."""
    def test_client(self):
        """Be sure that the docker client interface is properly configured."""
        assert isinstance(Config.client, DockerClient)
        assert Config.client.version()['ApiVersion'] == '1.37'
