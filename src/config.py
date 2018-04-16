"""Configuration values for the project."""
from docker import DockerClient
from os import sep as root
from os.path import join
from nmap.nmap import PortScanner

class Config():
    """Configuration values. Static object."""
    client = DockerClient('unix://var/run/docker.sock', version='1.37')
    default_nginx_webroot = join(
        root, 'usr', 'share', 'quick_deployments', 'nginx_default', 'webroot'
    )
    default_nginx_config = join(
        root,
        'usr',
        'share',
        'quick_deployments',
        'nginx_default',
        'configuration'
    )
    scanner = PortScanner()
