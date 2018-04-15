"""A quick deployment for a basic NginX web page, with webroot provided."""
import os
from os import sep as root
import tarfile
from shutil import copy
from textwrap import dedent
from docker.types import Mount
from docker.models.networks import Network
from _io import TextIOWrapper
from src.config import Config
from src.misc_functions import check_isdir, check_for_image


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
            raise ValueError("Image must be specified.")
        if "name" in kwargs.keys():
            for cont in Config.client.containers.list(
                        all=True, filters={'name': kwargs['name']}
                    ):
                cont.remove(v=False)
        try:
            self.mounts = kwargs['mounts']
        except KeyError:
            print(
                "WARNING: No Mounts specified for this container. There will",
                "be no persistence of the content of this container."
            )
        self.container = Config.client.containers.create(*args, **kwargs)
        self.state = Config.client.api.inspect_container(self.container.id)

    @classmethod
    def blank_mounted(cls, name: str):
        r"""A version with an empty folder mounted to the host.

        The webroot will be in
        /usr/share/quick_deployments/static/{name}/webroot.
        The default nginx configuration will be copied to
        /usr/share/quick_deployments/static/{name}/configuration
        """
        network = cls.get_network(name)
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
        obj = cls(
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
        return obj

    @classmethod
    def folder_copied_to_volume(cls, name: str, webroot: str):
        """A version with docker volumes, from a provded webroot folder.

        "webroot" should be a string representing a filepath to a directory
            containing the webroot to be recursively copied into the "webroot"
            docker volume mounted to the resulting container.
        """
        pass

    @classmethod
    def specified_files_copied_to_volume(cls, name, *files):
        """A version with individually passed files, mounted to a docker volume.

        The files should be either strings or file-like objects, or a mixture.
        """
        network = cls.get_network(name)
        webroot_files = tarfile.open(
            os.path.join(
                root,
                "tmp",
                "%s_webroot.tar" % name
            ),
            'w'
        )
        if "%s_webroot_vol" % name in [
                    v.name for v in Config.client.volumes.list()
                ]:
            for f in files:
                if f not in os.listdir(Config.client.api.inspect_volume(
                            "%s_webroot_vol"
                        )['Mountpoint']):
                    if isinstance(f, str):
                        webroot_files.add(f)
                    elif isinstance(f, TextIOWrapper):
                        webroot_files.addfile(f)
        else:
            for f in files:
                if isinstance(f, str):
                    webroot_files.add(f)
                elif isinstance(f, TextIOWrapper):
                    webroot_files.addfile(f)
        webroot_files.close()
        webroot = Mount(
            target=os.path.join(root, 'usr', 'share', 'nginx', 'html'),
            source="%s_webroot_vol" % name,
            type="volume",
            read_only=True
        )
        confdir = Mount(
            target=os.path.join(root, 'etc', 'nginx'),
            source="%s_configuration_vol" % name,
            type="volume",
            read_only=True
        )
        obj = cls(
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
        with tarfile.open(
                    os.path.join(root, "tmp", "%s_webroot.tar" % name),
                    'r'
                ) as webroot_files:
            obj.container.put_archive(
                "/usr/share/nginx/html", webroot_files.read()
            )

    @classmethod
    def copy_files_to_mounted_webroot(cls, name: str, *files):
        r"""A version with individually passed files, mounted to a host folder.

        The *files should be strings representing the paths of files to be
        copied recursively.

        The resulting folder will be mounted at
        /usr/share/quick_deployments/static/{name}/webroot.
        The default nginx configuration will be copied to
        /usr/share/quick_deployments/static/{name}/configuration
        """
        network = cls.get_network(name)
        parent_dir = cls.get_parent_dir(name)
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
        obj = cls(
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
        obj.mounts = (confdir, webroot)
        return obj

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
