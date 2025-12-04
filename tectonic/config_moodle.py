import tectonic.validate as validate

class TectonicConfigMoodle(object):
    """Class to store Tectonic Moodle configuration."""

    def __init__(self):
        self._version = "MOODLE_405_STABLE"
        self._internal_port = 443
        self._external_port = 8443
        self._site_fullname = "Tectonic Moodle"
        self._site_shortname = "Tectonic"
        self._admin_email = "admin@tectonic.local"

    @property
    def version(self):
        return self._version
    
    @property
    def internal_port(self):
        return self._internal_port
    
    @property
    def external_port(self):
        return self._external_port
    
    @property
    def site_fullname(self):
        return self._site_fullname
    
    @property
    def site_shortname(self):
        return self._site_shortname
    
    @property
    def admin_email(self):
        return self._admin_email

    @version.setter
    def version(self, value):
        if not (value.startswith("MOODLE_") and value.endswith("_STABLE")):
            raise ValueError(f"Invalid Moodle version format: {value}")
        self._version = value

    @internal_port.setter
    def internal_port(self, value):
        validate.number("Moodle internal port", value)
        self._internal_port = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Moodle external port", value)
        self._external_port = value
    
    @site_fullname.setter
    def site_fullname(self, value):
        if not isinstance(value, str) or len(value) == 0:
            raise ValueError(f"Invalid Moodle site fullname: {value}. Must be a non-empty string.")
        if len(value) > 255:
            raise ValueError(f"Invalid Moodle site fullname: {value}. Must be 255 characters or less.")
        self._site_fullname = value
    
    @site_shortname.setter
    def site_shortname(self, value):
        if not isinstance(value, str) or len(value) == 0:
            raise ValueError(f"Invalid Moodle site shortname: {value}. Must be a non-empty string.")
        if len(value) > 100:
            raise ValueError(f"Invalid Moodle site shortname: {value}. Must be 100 characters or less.")
        validate.regex("Moodle site shortname", value, r"^[a-zA-Z0-9_-]+$")
        self._site_shortname = value
    
    @admin_email.setter
    def admin_email(self, value):
        if not isinstance(value, str) or len(value) == 0:
            raise ValueError(f"Invalid Moodle admin email: {value}. Must be a non-empty string.")
        validate.regex("Moodle admin email", value, r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self._admin_email = value
