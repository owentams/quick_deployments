"""Tests for the BasicNginXSite."""
import os
import tarfile
from os import sep as root
from docker.models.networks import Network
from docker.errors import APIError
from textwrap import dedent
from requests import get, ConnectionError
from pytest import raises
from src.config import Config
from src.basic_nginx_site import BasicNginXSite, BlankMounted_BasicNginXSite
from src.basic_nginx_site import CopyFoldersToMounts
from src.misc_functions import hash_of_file, perms, hash_of_str
from shutil import rmtree
from strict_hint import strict


class TestBasicNginXSite:
    """Tests that apply to all of the variations on BasicNginXSite."""
    @strict
    @property
    def instance_name(self) -> str:
        return "test_nginx_site"

    @strict
    @property
    def index_path(self) -> str:
        """The path for the default index file."""
        return os.path.join(Config.default_nginx_webroot, 'index.html')

    @strict
    @property
    def errpage_path(self) -> str:
        return os.path.join(Config.default_nginx_webroot, '50x.html')

    @strict
    @property
    def container_network(self) -> Network:
        """Aquire a test network based on the name of this instance."""
        if "%s_network" % self.instance_name in [
                    net.name for net in Config.client.networks.list()
                ]:
            # A network for this name exists, get it.
            networks = [
                net.id for net in Config.client.networks.list(
                    names="%s_network" % self.instance_name
                )
            ]
            assert len(networks) == 1, dedent("""
                Apparently it's possible to have more than one network with the
                same name. I did not know that."""
            )
            return networks[0]
        else:
            # A network for this name doesn't yet exist
            return Config.client.networks.create(
                name="%s_network" % self.instance_name
            )

    @property
    @strict
    def instance(self) -> BasicNginXSite:
        """Aquire a BasicNginXSite based on the name and other args passed."""
        return BasicNginXSite(
            image="nginx:latest",
            name=self.instance_name,
            auto_remove=True,
            network=self.container_network,
            ports={
                80:     80,
                443:    443
            }
        )

    def teardown_method(self):
        """Remove the test container.

        Because the BasicNginXSite has auto_remove set to true, it just needs
        stopped.
        """
        try:
            self.instance.container.stop()
        except APIError:
            # if the container isn't running it will throw an error for
            # attempting to stop it.
            self.instance.container.remove()

    @staticmethod
    @strict
    def check_file(
                test_file: str,
                original_file: str,
                permission_bits: int=0o100644
            ) -> bool:
        """Check that a file matches its original, and permissions."""
        if not os.access(test_file, os.F_OK):
            return False
        if perms(test_file) != permission_bits:
            return False
        if hash_of_file(test_file) != hash_of_file(original_file):
            return False
        return True

    @staticmethod
    @strict
    def inspect(container_id: int) -> dict:
        """Inspect the given container."""
        return Config.client.api.inspect_container(container_id)

    def test_for_network(self):
        """Test that the network is properly configured."""
        assert "%s_network" % self.instance_name in [
                net for net in self.inspect(
                    self.instance.container.id
                )['NetworkSettings']['Networks']
            ]

    def test_ports(self):
        """Test that the right ports are open."""
        port_bindings = self.inspect(
                self.instance.container.id
            )['HostConfig']['PortBindings']
        assert "443/tcp" in port_bindings.keys()
        assert "80/tcp" in port_bindings.keys()
        assert len(port_bindings.keys()) == 2
        assert {"HostIp": "", "HostPort": "443"} in port_bindings["443/tcp"]
        assert {"HostIp": "", "HostPort": "80"} in port_bindings["80/tcp"]
        assert len(port_bindings["80/tcp"]) == 1
        assert len(port_bindings["443/tcp"]) == 1

    def test_image(self):
        """Make sure the retrieved container is an NginX container."""
        assert "nginx:latest" in self.instance.container.image.tags

    def test_inspection(self):
        """Check to be sure instance.state is the same as inspect()."""
        assert self.instance.state == self.inspect(self.instance.container.id)

    def test_get_request(self):
        """Start the container and check the results of an HTTP request.

        Performs requests on 80 and 443.
        """
        self.instance.container.start()
        http_result = get("http://localhost")
        assert http_result.status_code == 200
        assert hash_of_str(
                http_result.content.decode()
            ) == hash_of_file(self.index_path)
        with raises(ConnectionError):
            # No cert, no HTTPS. Throws an error.
            get("https://localhost")

    def test_configuration_files(self):
        """Test that the configuration files are correct.

        They should match up to a default NginX configuration.

        Note that 0o100644 (octal 100644, the mask for rw-r--r--) is equal to
        decimal 33188.
        """
        conf_dir = os.path.join(
            os.sep,
            "usr",
            "share",
            "quick_deployments",
            "static",
            self.instance_name,
            "configuration"
        )
        assert self.check_file(
            os.path.join(conf_dir, "fastcgi_params"),
            os.path.join(Config.default_nginx_config, "fastcgi_params")
        )
        assert self.check_file(
            os.path.join(conf_dir, "koi-utf"),
            os.path.join(Config.default_nginx_config, "koi-utf")
        )
        assert self.check_file(
            os.path.join(conf_dir, "koi-win"),
            os.path.join(Config.default_nginx_config, "koi-win")
        )
        assert self.check_file(
            os.path.join(conf_dir, "mime.types"),
            os.path.join(Config.default_nginx_config, "mime.types")
        )
        assert self.check_file(
            os.path.join(conf_dir, "nginx.conf"),
            os.path.join(Config.default_nginx_config, "nginx.conf")
        )
        assert self.check_file(
            os.path.join(conf_dir, "scgi_params"),
            os.path.join(Config.default_nginx_config, "scgi_params")
        )
        assert self.check_file(
            os.path.join(conf_dir, "uwsgi_params"),
            os.path.join(Config.default_nginx_config, "uwsgi_params")
        )
        assert self.check_file(
            os.path.join(conf_dir, "win-utf"),
            os.path.join(Config.default_nginx_config, "win-utf")
        )
        assert os.path.isdir(os.path.join(conf_dir, "conf.d"))
        assert self.check_file(
            os.path.join(conf_dir, "conf.d", "default.conf"),
            os.path.join(Config.default_nginx_config, "conf.d", "default.conf")
        )

    def test_webroot_files(self):
        """Test that the configuration files are correct.

        They should match up to a default NginX configuration.
        """
        webroot_dir = os.path.join(
            os.sep,
            "usr",
            "share",
            "quick_deployments",
            "static",
            self.instance_name,
            "webroot"
        )
        assert self.check_file(
            os.path.join(webroot_dir, "50x.html"),
            os.path.join(Config.default_nginx_webroot, "50x.html")
        )
        assert self.check_file(
            os.path.join(webroot_dir, "index.html"),
            os.path.join(Config.default_nginx_webroot, "index.html")
        )

    def test_that_files_are_placed_if_not_present(self):
        """Delete the webroot & confdir then check for the files to be back.

        They should be checked for and repopulated every time
        get_test_instance is called.
        """
        for mount in self.instance.mounts:
            rmtree(mount['Source'])
        self.test_webroot_files()
        self.test_configuration_files()

    def test_container_stays_running(self):
        """Start the container then check for it in the list of running."""
        self.instance.container.start()
        assert self.instance.container.id in [
            c.id for c in Config.client.containers.list()
        ], "The instance was started but doesn't seem to be running."


class TestBlankMounted(TestBasicNginXSite):
    """Test the blank_mounted constructor for a BasicNginXSite."""
    @strict
    @property
    def instance_name(self) -> str:
        return "test-blank_mounted"

    @property
    @strict
    def instance(self) -> BasicNginXSite:
        """Aquire a test version of the object."""
        return BlankMounted_BasicNginXSite(name=self.instance_name)


class TestCopyFoldersToMounts_1():
    """Tests for the CopyFoldersToMounts variant, version 1.

    This is tests with only specifying the webroot.
    """
    @strict
    @property
    def instance_name(self) -> str:
        return "test-files2mount_1-nginx"

    @strict
    @property
    def instance(self) -> CopyFoldersToMounts:
        return CopyFoldersToMounts(
            self.instance_name,
            Config.default_nginx_webroot
        )


class TestCopyFoldersToMounts_2():
    """Tests for the CopyFoldersToMounts variant, version 2.

    This is tests with the webroot and the configuration directory specified.
    """
    @strict
    @property
    def instance_name(self) -> str:
        return "test-files2mount_2-nginx"

    @strict
    @property
    def instance(self) -> CopyFoldersToMounts:
        return CopyFoldersToMounts(
            self.instance_name,
            Config.default_nginx_webroot,
            Config.default_nginx_config
        )


class TestCopyFoldersToMounts_3():
    """Tests for the CopyFoldersToMounts variant, version 3.

    This is tests with the webroot, configuration directory, and an additional
    test directory defined."""
    @strict
    @property
    def instance_name(self) -> str:
        return "test-files2mount-nginx"

    @strict
    @property
    def folder_1(self) -> Dict[str, str]:
        return {
            'host_mnt': os.path.join(
                root,
                'usr',
                'share',
                'quick_deployments',
                self.instance_name,
                'test_dir_from_archive'
            ),
            'destination': os.path.join(root, 'tmp', 'test_folder_1'),
            'incoming_data': os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "test_archive.tar"
            )
        }

    @strict
    @property
    def folder_2(self) -> Dict[str, str]:
        return {
            'host_mnt': os.path.join(
                root,
                'usr',
                'share',
                'quick_deployments',
                self.instance_name,
                'test_dir_from_folder'
            ),
            'destination': os.path.join(root, 'tmp', 'test_folder_2'),
            'incoming_data': os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "test_document_folder"
            )
        }

    @strict
    @property
    def instance(self) -> CopyFoldersToMounts:
        return CopyFoldersToMounts(
            self.instance_name,
            webroot=Config.default_nginx_webroot,
            confdir=Config.default_nginx_config,
            other_mounts=[
                self.test_folder_1['host_mnt']: {
                    "destination": self.test_folder_1['destination'],
                    "incoming_data": self.test_folder_1['incoming_data']
                },
                self.test_folder_2['host_mnt']: {
                    "destination": self.test_folder_2['destination']
                    "incoming_data": self.test_folder_2['incoming_data']
                }
            ]
        )

    def test_folder_1(self):
        """Test that the files are the same for the archive-copy version."""
        self.instance.container.start()
        assert self.instance.container.id in [
            c.id for c in Config.client.containers.list()
        ], "The instance was started but doesn't seem to be running."
        # to get similar output to the `tar tf` command we can use `find`
        assert runcmd(
                "tar tf %s" % folder_1['incoming_data']
            ) == self.instance.container.exec_run(
                "find %s" % folder_1['destination']
            ).output.decode()

    def test_folder_2(self):
        """Test that the files are the same for the folder-copy version."""
