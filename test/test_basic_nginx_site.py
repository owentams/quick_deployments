"""Tests for the BasicNginXSite."""
import os
from docker.models.networks import Network
from docker.errors import APIError
from textwrap import dedent
from hashlib import sha256
from requests import get, ConnectionError
from pytest import raises, fixture
from src.config import Config
from src.basic_nginx_site import BasicNginXSite


class TestBasicNginXSite():
    """Tests that apply to all of the variations on BasicNginXSite."""
    instance_name = "test_nginx_site"

    def get_test_network(self) -> Network:
        """Aquire a test network based on the name passed."""
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

    def get_test_instance(self) -> BasicNginXSite:
        """Aquire a BasicNginXSite based on the name and other args passed."""
        return BasicNginXSite(
            image="nginx:latest",
            name=self.instance_name,
            auto_remove=True,
            network=self.get_test_network(),
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
            self.get_test_instance().container.stop()
        except APIError:
            # if the container isn't running it will throw an error for
            # attempting to stop it.
            self.get_test_instance().container.remove()

    @staticmethod
    def inspect(container_id: int) -> dict:
        """Inspect the given container."""
        return Config.client.api.inspect_container(container_id)

    def test_network(self):
        """Test that the network is properly configured."""
        inst = self.get_test_instance()
        assert "%s_network" % self.instance_name in [
                net for net in self.inspect(
                    inst.container.id
                )['NetworkSettings']['Networks']
            ]

    def test_ports(self):
        """Test that the right ports are open."""
        inst = self.get_test_instance()
        port_bindings = self.inspect(
                inst.container.id
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
        assert "nginx:latest" in self.get_test_instance().container.image.tags

    def test_inspection(self):
        """Check to be sure instance.state is the same as inspect()."""
        instance = self.get_test_instance()
        assert instance.state == self.inspect(instance.container.id)


class TestBlankMounted(TestBasicNginXSite):
    """Test the blank_mounted constructor for a BasicNginXSite."""

    def get_test_instance(self) -> BasicNginXSite:
        """Aquire a test version of the object."""
        return BasicNginXSite.blank_mounted(name=self.instance_name)

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
        with open(os.path.join(conf_dir, "fastcgi_params"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "f37852d0113de30fa6bfc3d9b180ef99383c0673953"\
                "0dd482a8538503afd5a58"
        assert oct(os.stat(os.path.join(conf_dir, "fastcgi_params")).st_mode) \
            == '0o100644', \
            "fastcgi_params permissions are wrong."
        with open(os.path.join(conf_dir, "koi-utf"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "b5f8a6d411db5e5d11d151d50cd1e962444732593ad"\
                "ec0e1ef0a8c6eebec63ee"
        assert oct(os.stat(os.path.join(conf_dir, "koi-utf")).st_mode) \
            == '0o100644', \
            "koi-utf permissions are wrong."
        with open(os.path.join(conf_dir, "koi-win"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "de518a9eafe86c8bc705e296d0ef26135835b46bdc"\
                "0de01d1d50a630fa5d341e"
        assert oct(os.stat(os.path.join(conf_dir, "koi-win")).st_mode) \
            == '0o100644', \
            "koi-win permissions are wrong."
        with open(os.path.join(conf_dir, "mime.types"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "d61b7bdd17d561ea037812761e6903970c6bbe5c7d"\
                "ffd0fad069927f057c55a3"
        assert oct(os.stat(os.path.join(conf_dir, "mime.types")).st_mode) \
            == '0o100644', \
            "mime.types permissions are wrong."
        with open(os.path.join(conf_dir, "nginx.conf"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "772e914d404163a563e888730a3d4c5d86fbb1a5d3"\
                "ee6b8c58c7eeda9af1db5b"
        assert oct(os.stat(os.path.join(conf_dir, "nginx.conf")).st_mode) \
            == '0o100644', \
            "nginx.conf permissions are wrong."
        with open(os.path.join(conf_dir, "scgi_params"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "f27b2027c571ccafcfb0fbb3f54d7aeee11a984e3a"\
                "0f5a1fdf14629030fc9011"
        assert oct(os.stat(os.path.join(conf_dir, "scgi_params")).st_mode) \
            == '0o100644', \
            "scgi_params permissions are wrong."
        with open(os.path.join(conf_dir, "uwsgi_params"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "015cb581c2eb84b1a1ac9b575521d5881f791f632b"\
                "fa62f34b26ba97d70c0d4f"
        assert oct(os.stat(os.path.join(conf_dir, "uwsgi_params")).st_mode) \
            == '0o100644', \
            "uwsgi_params permissions are wrong."
        with open(os.path.join(conf_dir, "win-utf"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "55adf050bad0cb60cbfe18649f8f17cd405fece0cc"\
                "65eb78dac72c74c9dad944"
        assert oct(os.stat(os.path.join(conf_dir, "win-utf")).st_mode) \
            == '0o100644', \
            "win-utf permissions are wrong."
        assert os.path.isdir(os.path.join(conf_dir, "conf.d"))
        with open(os.path.join(conf_dir, "conf.d", "default.conf"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "ba015afe3042196e5d0bd117a9e18ac826f52e44cb"\
                "29321a9b08f7dbf48c62a5"
        assert oct(os.stat(
                os.path.join(conf_dir, "conf.d", "default.conf")
            ).st_mode) == '0o100644', \
            "conf.d/default.conf permissions are wrong."

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
        with open(os.path.join(webroot_dir, "50x.html"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "3c264d74770fd706d59c68d90ca1eb893ac379a666f"\
                "f136f9acc66ca01daec02"
        assert os.stat(os.path.join(webroot_dir, "50x.html")).st_mode \
            == 0o100644, \
            "50x.html permissions are wrong."
        with open(os.path.join(webroot_dir, "index.html"), 'r') as f:
            assert sha256(f.read().encode('ascii')).hexdigest()\
                == "38ffd4972ae513a0c79a8be4573403edcd709f0f572"\
                "105362b08ff50cf6de521"
        assert os.stat(os.path.join(webroot_dir, "index.html")).st_mode \
            == 0o100644, \
            "index.html permissions are wrong."

    def test_get_request(self):
        """Start the container and check the results of an HTTP request.

        Performs requests on 80 and 443.
        """
        self.get_test_instance().container.start()
        http_result = get("http://localhost")
        assert http_result.status_code == 200
        assert sha256(http_result.content.encode('ascii')) == \
            "38ffd4972ae513a0c79a8be4573403edcd709f0f572105362b08ff50cf6de521"
        with raises(ConnectionError):
            # No cert, no HTTPS. Throws an error.
            get("https://localhost")
