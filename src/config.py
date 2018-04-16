"""Configuration values for the project."""
from docker import DockerClient
from os import sep as root
from os.path import join
from nmap.nmap import PortScanner

class Config():
    """Configuration values. Static object."""
    @property
    @staticmethod
    def client() -> DockerClient:
        return DockerClient('unix://var/run/docker.sock', version='1.37')
    @property
    @staticmethod
    def default_nginx_webroot() -> str:
        return join(
            root, 'usr', 'share', 'quick_deployments', 'nginx_default', 'webroot'
        )
    @property
    @staticmethod
    def default_nginx_config() -> str:
        return join(
            root,
            'usr',
            'share',
            'quick_deployments',
            'nginx_default',
            'configuration'
        )
    @property
    @staticmethod
    def scanner():
        return PortScanner()
