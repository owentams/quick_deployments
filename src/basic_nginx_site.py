"""A quick deployment for a basic NginX web page, with webroot provided."""
import os
from os import sep as root
import tarfile
from shutil import copy
from textwrap import dedent
from typing import Iterable, Union, Tuple
from docker.types import Mount
from docker.models.networks import Network
from docker.errors import APIError
from _io import TextIOWrapper
from src.config import Config
from src.misc_functions import check_isdir, check_for_image, hash_of_file


class BasicNginXSite():
    """An object representing a basic NginX site, with a provided webroot.

    The webroot can be either a docker volume or a mounted local folder.
    """
    def __init__(self, *args, **kwargs):
        """Accept parameters to use to create a container.

        All passed parameters are passed to the docker client's "create"
        function for containers, and the resulting container object is stored
        in self.container.

        self.state is then created to store the current state of the container,
        so that it can be recovered from being stopped.

        For containers with bind mounts, you must store them manually after
        running __init__(self), as a list of docker.types.Mount objects as
        self.mounts.
        """
        if "image" in kwargs.keys():
            check_for_image(
                tag=kwargs['image'].split(':', maxsplit=1)[0],
                version=kwargs['image'].split(':', maxsplit=1)[1]
            )
        else:
            raise ValueError(
                "Image must be specified. Received kwargs: "
                + str(kwargs.keys())
            )
        if "name" in kwargs.keys():
            for cont in Config.client.containers.list(
                        all=True, filters={'name': kwargs['name']}
                    ):
                try:
                    cont.stop()
                except APIError:
                    pass
                cont.remove(v=False)
        for cont in Config.client.containers.list():
            portbindings = Config.client.api.inspect_container(
                cont.id
            )['HostConfig']['PortBindings'].keys()
            if '80/tcp' in portbindings or '443/tcp' in portbindings:
                cont.stop()
        open_ports = [
            int(port) for port in
            Config.port_scanner.scan()['scan']['127.0.0.1']['tcp']
        ]
        if 80 in open_ports or 443 in open_ports:
            raise RuntimeError(
                "Ports are occupied by a non-docker application!"
            )
        try:
            self.mounts = kwargs['mounts']
        except KeyError:
            print(
                "WARNING: No Mounts specified for this container. There will",
                "be no persistence of the content of this container."
            )
        self.container = Config.client.containers.create(*args, **kwargs)
        self.state = Config.client.api.inspect_container(self.container.id)

    @staticmethod
    def get_parent_dir(name: str) -> str:
        """Retrieve the parent directory of a named instance."""
        return os.path.join(
            root,
            "usr",
            "share",
            "quick_deployments",
            "static",
            name
        )

    @staticmethod
    def get_network(name: str) -> Network:
        """Retrieve the appropriate network for this named service."""
        if "%s_network" % name not in [
                    net.name for net in Config.client.networks.list()
                ]:
            # A network for this name doesn't yet exist
            return Config.client.networks.create(name="%s_network" % name)
        # A network for this name exists, get it.
        networks = Config.client.networks.list(names=["%s_network" % name])
        assert len(networks) == 1, dedent("""
            Apparently it's possible to have more than one network with the
            same name. I did not know that."""
        )
        return networks[0]


class BlankMounted_BasicNginXSite(BasicNginXSite):
    r"""A version with an empty folder mounted to the host.

    The webroot will be in
    /usr/share/quick_deployments/static/{name}/webroot.
    The default nginx configuration will be copied to
    /usr/share/quick_deployments/static/{name}/configuration
    """
    def __init__(self, name: str):
        """init self"""
        network = self.get_network(name)
        parent_dir = os.path.join(
            root,
            "usr",
            "share",
            "quick_deployments",
            "static",
            name
        )
        webroot_path = os.path.join(
            parent_dir,
            "webroot"
        )
        confdir_path = os.path.join(
            parent_dir,
            "configuration"
        )
        check_isdir(webroot_path, src=Config.default_nginx_webroot)
        check_isdir(confdir_path, src=Config.default_nginx_config)
        webroot = Mount(
            target="/usr/share/nginx/html",
            source=webroot_path,
            type="bind",
            no_copy=False,
            read_only=True
        )
        confdir = Mount(
            target="/etc/nginx/",
            source=confdir_path,
            type="bind",
            no_copy=False,
            read_only=True
        )
        super(BlankMounted_BasicNginXSite, self).__init__(
            image="nginx:latest",
            auto_remove=True,
            network=network.id,
            ports={
                80:     80,
                443:    443
            },
            mounts=[
                confdir,
                webroot
            ]
        )


class CopyFilesToMountedWebroot_BasicNginxSite(BasicNginXSite):
    """A version with individually passed files, mounted to a host folder.

    The *files should be strings representing the paths of files to be
    copied recursively.

    The resulting folder will be mounted at
    /usr/share/quick_deployments/static/{name}/webroot.
    The default nginx configuration will be copied to
    /usr/share/quick_deployments/static/{name}/configuration
    """
    def __init__(self, name: str, *files):
        """init self"""
        network = self.get_network(name)
        parent_dir = self.get_parent_dir(name)
        webroot_path = os.path.join(parent_dir, "webroot")
        confdir_path = os.path.join(parent_dir, "configuration")
        check_isdir(webroot_path)
        check_isdir(confdir_path)
        webroot = Mount(
            target="/usr/share/nginx/html",
            source=webroot_path,
            type='bind',
            read_only=True
        )
        confdir = Mount(
            target="/etc/nginx/",
            source=confdir_path,
            type='bind',
            no_copy=False,
            read_only=True
        )
        super(CopyFilesToMountedWebroot_BasicNginxSite, self).__init__(
            image="nginx:latest",
            auto_remove=True,
            network=network.id,
            ports={
                80:     80,
                443:    443
            },
            mounts=[
                confdir,
                webroot
            ]
        )
        for f in files:
            copy(
                f,
                os.path.join(webroot_path, os.path.basename(f))
            )


class CopyFoldersToMounts(BasicNginXSite):
    """Allows folders to be specified that hold various mounted directories.

    webroot and confdir should both either be a tarfile.TarFile object (an open
    tarfile) or a string defining a filepath to be copied. The contents of any
    specified mount source will override what is in the container already, if
    anything.

    Any additional mounts may be specified in a dict in the format
        { mount point: source folder or tarfile.TarFile }
    """
    MountPoint = Union[str, tarfile.TarFile]

    def __init__(
                    self,
                    name,
                    webroot: str,
                    confdir: str=None,
                    other_mounts: dict=None
                ):
            if confdir is None:
                confdir = Config.default_nginx_config
            network = self.get_network(name)
            webroot_mount, webroot_archive = self.get_mount_for(
                webroot, '/usr/share/nginx/html'
            )
            confdir_mount, confdir_archive = self.get_mount_for(
                confdir, '/etc/nginx'
            )
            mounts = [webroot_mount, confdir_mount]
            archives = [webroot_archive, confdir_archive]
            for dest, src in other_mounts.items():
                mnt, tarfile = self.get_mount_for(src, dest)
                mounts.append(mnt)
                archives.append(tarfile)
            super().__init__(
                image="nginx:latest",
                auto_remove=True,
                network=network.id,
                ports={
                    80:     80,
                    443:    443
                },
                mounts=mounts
            )
            for arch in archives:
                self.container.put_archive(arch)

    def get_mount_for(
                self, source: MountPoint, destination: str
            ) -> Tuple[Mount, str]:
        foldername = destination.replace('/', '_')
        if isinstance(source, tarfile.TarFile):
            mnt = Mount(
                target=destination,
                source=os.path.join(self.get_parent_dir(), foldername),
                type='bind',
                read_only=True
            )
            return mnt, source
        if not isinstance(source, str) or not os.isdir(source):
            raise TypeError(
                "%s is not a folder to be copied or a tarfile." % source
            )
        with tarfile.open(os.path.join(root, 'tmp', foldername)) as tf:
            for f in d
