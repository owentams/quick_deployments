"""A quick deployment for a basic NginX web page, with webroot provided."""
import os
from os import sep as root
import tarfile
from shutil import copy
from textwrap import dedent
from typing import Union, Tuple, Dict, Optional
from strict_hint import strict
from docker.types import Mount
from docker.models.networks import Network
from docker.errors import APIError
from src.config import Config
from src.misc_functions import check_isdir, check_for_image, list_recursively
from src.misc_functions import hash_of_str
MountPoint = Union[str, Dict[str, tarfile.TarFile]]
OtherMount = Dict[str, Dict[str, str]]


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
    """

    def __init__(
                self,
                name,
                webroot: str,
                confdir: Union[MountPoint, None]=None,
                other_mounts: Optional[OtherMount]=None
            ):
        """Allows folders to be specified that hold various mounted directories.

        webroot and confdir should both be a mapping of a string representing
        the host mount point to either a tarfile.TarFile object (an
        open tarfile) or a string defining a filepath to be copied. The
        contents of any specified mount source will override what is in the
        container already, if anything.

        Any additional mounts may be specified in a dict in the format
            (Dict){
                mount point on host: {
                    "destination": mount point in container,
                    "incoming_data": filepath of folder to be copied
                }
            }
        """
        if len(webroot) > 1:
            raise ValueError(
                "The webroot mapping must have a length of one, it has %d"
                % len(webroot)
            )
        if len(confdir) > 1:
            raise ValueError(
                "The confdir mapping must have a length of one, it has %d"
                % len(confdir)
            )
        if confdir is None:
            confdir = Config.default_nginx_config
        network = self.get_network(name)
        webroot_mount, webroot_archive = self.get_mount_for(
            source=webroot.values()[0],
            destination=webroot.keys()[0],
            mount_point='/usr/share/nginx/html'
        )
        confdir_mount, confdir_archive = self.get_mount_for(
            confdir.keys()[0], '/etc/nginx',
        )
        mounts = {
            webroot_mount: webroot_archive,
            confdir_mount: confdir_archive
        }
        try:
            for host_mnt, container_config in other_mounts.items():
                mnt, tarfile = self.get_mount_for(
                    source=container_config['incoming_data'],
                    mount_point=host_mnt,
                    destination=container_config['destination']
                )
                mounts.update({mnt: tarfile})
        except AttributeError:
            if other_mounts is not None:
                # other_mounts is an optional argument, and errors caused by
                # its lack of presence should simply be ignored.
                raise
        super().__init__(
            image="nginx:latest",
            auto_remove=True,
            network=network.id,
            ports={
                80:     80,
                443:    443
            },
            mounts=mounts.keys()
        )
        for mount_point, archive in mounts.items():
            self.container.put_archive(path=mount_point, data=archive)

    @strict
    def get_mount_for(
                self,
                source: Union[str, tarfile.TarFile],
                destination: str,
                mount_point: str
            ) -> Tuple[Mount, str]:
        """Return a mount and the location of a tarfile to put in that mount.

        source should be the location of the source files
        destination should be the mount point inside the container
        mount_point should be the host mount point.
        """
        if isinstance(source, str):
            with tarfile.open(os.path.join(
                        root,
                        'tmp',
                        'quick_deployments',
                        '%s.tar' % hash_of_str(mount_point)[:15]
                    ), 'w') as tf:
                for f in list_recursively(source):
                    tf.add(f)
        else:
            tmpstore = os.path.join(
                root, 'tmp', 'quick_deployments', 'tmpstore'
            )
            os.makedirs(tmpstore)
            # Extract the received tarfile into a temporary storage.
            source.extractall(tmpstore)
            # then write the temporary storage to a new archive.
            with tarfile.open(os.path.join(
                        root,
                        'tmp',
                        'quick_deployments',
                        '%s.tar' % hash_of_str(mount_point)[:15]
                    ), 'w') as tf:
                for f in list_recursively(tmpstore):
                    tf.add(f)
            for f in list_recursively(tmpstore):
                os.remove(f)
            os.removedirs(tmpstore)
        mnt = Mount(
            target=destination,
            source=mount_point,
            type='bind',
            read_only=True
        )
        return mnt, os.path.join(
            root,
            'tmp',
            'quick_deployments',
            '%s.tar' % hash_of_str(mount_point)[:15]
        )
