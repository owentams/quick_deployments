"""A quick deployment for a basic NginX web page, with webroot provided."""
import os
from os import sep as root
import tarfile
from shutil import copy
from textwrap import dedent
from typing import Iterable
from docker.types import Mount
from docker.models.networks import Network
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
        super().__init__(
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
        super().__init__(
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


class SiteWithDockerVolumes_Mixin():
    """Methods for all BasicNginXSite objects that have docker volumes."""
    @staticmethod
    def check_vol_for_files(volume_name: str, files: Iterable[str]) -> str:
        """Check volume for files, creating a tar archive of the missing ones.

        Works by comparing the sha256 hashes of each file in the `files` param
        to a list of the hashes of the files in the volume. If the volume
        does not yet exist, all files are added to the archive.

        type: volume_name:  str
        type: files:        Iterable of strings
        param: volume_name: The name of the docker volume.
        param: files:       An iterable of filepaths to check for.
        return: str:        The location of a tar archive with the missing
                            files, for use with self.container.put_archive
        """
        with tarfile.open(os.path.join(
                    root, "tmp", "%s.tar" % volume_name
                ), 'w') as volume_files:
            if volume_name in [
                        v.name for v in Config.client.volumes.list()
                    ]:
                filehashes = [
                    hash_of_file(f) for f in os.listdir(
                        Config.client.api.inspect_volume(
                            "%s_webroot_vol"
                        )['Mountpoint']
                    )
                ]
                for f in files:
                    if hash_of_file(f) not in filehashes:
                        if isinstance(f, str):
                            volume_files.add(f)
                        elif isinstance(f, TextIOWrapper):
                            volume_files.addfile(f)
            else:
                for f in files:
                    if isinstance(f, str):
                        volume_files.add(f)
                    elif isinstance(f, TextIOWrapper):
                        volume_files.addfile(f)
        return os.path.join(
            root,
            "tmp",
            "%s.tar" % volume_name
        )


class FolderCopiedToVolume_BasicNginXSite(
            SiteWithDockerVolumes_Mixin, BasicNginXSite
        ):
    def __init__(self, name: str, webroot: str):
        """A version with docker volumes, from a provded webroot folder.

        "webroot" should be a string representing a filepath to a directory
            containing the webroot to be recursively copied into the "webroot"
            docker volume mounted to the resulting container.
        """
        pass


class SpecifiedFilesCopiedToVolume_BasicNginXSite(
            SiteWithDockerVolumes_Mixin, BasicNginXSite
        ):
    def __init__(self, name, *files):
        """A version with individually passed files, mounted to a docker volume.

        The files should be either strings or file-like objects, or a mixture.
        """
        network = self.get_network(name)
        webroot_volume_name = "%s_webroot_vol" % name
        config_volume_name = "%s_configuration_vol" % name
        webroot_files = self.check_vol_for_files(webroot_volume_name, files)
        conf_dir_files = self.check_vol_for_files(
            volume_name=config_volume_name,
            files=[
                os.path.join(dp, f) for dp, dn, fn in os.walk(
                    Config.default_nginx_config
                ) for f in fn
            ]
        )
        webroot = Mount(
            target=os.path.join(root, 'usr', 'share', 'nginx', 'html'),
            source=webroot_volume_name,
            type="volume",
            read_only=True
        )
        confdir = Mount(
            target=os.path.join(root, 'etc', 'nginx'),
            source=config_volume_name,
            type="volume",
            read_only=True
        )
        super().__init__(
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
        with tarfile.open(webroot_files) as wf:
            self.container.put_archive(
                "/usr/share/nginx/html", wf.read()
            )
        with tarfile.open(conf_dir_files) as cf:
            self.container.put_archive(
                os.path.join(root, 'etc', 'nginx'), cf.read()
            )
