#
# 
#

import base64
import hashlib
import hmac
import pickle
from typing import Any, IO

from megacodist.singleton import SingletonMeta


class BadConfigFileError(Exception):
    """
    This error will be raised if the content of the config file
    cannot be interpreted as expected.
    """
    pass


class AppSettings(object, metaclass=SingletonMeta):
    """
    Encapsulates APIs for persistence settings between different sessions
    of the application.

    ### Characteristics
    1. This class implements the singleton design pattern, meaning one and
    only one object of this class can be instantiated.

    ### Work flow
    1. Subclass it and add default values for your app settings as class
    attributes.
    2. Instantiate the class with a secret key:
       `settings = MyAppSettings(secret_key=b'your-unique-and-secret-key')`.
       Because this is a singleton, the key is set *only* when the first
       instance is created. Subsequent calls to the constructor will be ignored.
    3. Open a file in binary read mode (`'rb'`) and pass the stream to
       `settings.load(stream)`.
    4. Read and/or write attributes at the object level.
    5. Open a file in binary write mode (`'wb'`) and pass the stream to
       `settings.save(stream)` to save the settings.

    ### Example
    ```python
    # Define your settings class
    class MyAppSettings(AppSettings):
        username: str = "default_user"
        theme: str = "dark"

    SECRET_KEY = b'a-very-secret-key-for-my-app-!@#$'
    settings_file = "my_app.conf"

    # Instantiate the settings object with the key
    settings = MyAppSettings(secret_key=SECRET_KEY)

    # Load settings
    try:
        with open(settings_file, "rb") as f:
            settings.load(f)
    except (FileNotFoundError, BadConfigFileError):
        print("Settings file not found or corrupt, using defaults.")

    # Use and modify settings
    print(f"Current theme: {settings.theme}")
    settings.theme = "light"

    # Save settings
    with open(settings_file, "wb") as f:
        settings.save(f)
    ```
    """

    def __init__(self, secret_key: bytes) -> None:
        """
        Initializes the settings object.

        Args:
            `secret_key`: A secret byte string used to sign and verify the
                integrity of the settings file.
        """
        self._secret_key = secret_key

    def load(self, stream: IO[bytes]) -> None:
        """
        Loads app settings from the given binary stream into the singleton
        object. The caller is responsible for opening and closing the
        stream.

        Exceptions:
            `megacodist.settings.BadConfigFileError`:
                Raised if the content of the stream cannot be interpreted
                (e.g., bad signature or corrupt data).
        """
        # Reading settings from the stream...
        try:
            raw_settings = stream.read()
            # The first 44 bytes are the base64 encoded signature
            signature_from_file = raw_settings[:44]
            payload = raw_settings[44:]

            # Checking the signature...
            expected_signature = hmac.digest(
                key=self._secret_key,
                msg=payload,
                digest=hashlib.sha256)
            expected_signature = base64.b64encode(expected_signature)

            if hmac.compare_digest(signature_from_file, expected_signature):
                decoded_settings = base64.b64decode(payload)
                settings: dict[str, Any] = pickle.loads(decoded_settings)
            else:
                raise BadConfigFileError("Signature mismatch.")
            
            # Ensure loaded settings are a subset of defined attributes
            if not set(settings.keys()).issubset(
                    self._GetClassAttrsName()):
                raise BadConfigFileError(
                    "Config file contains unknown attributes.")
        except Exception as e:
            # An error occurred checking signature or decoding the settings
            raise BadConfigFileError(f"Failed to read settings: {e}")
        else:
            for attr, value in settings.items():
                setattr(self, attr, value)

    def save(self, stream: IO[bytes]) -> None:
        """
        Saves settings to the given binary stream. The caller is
        responsible for opening and closing the stream.
        """
        settings: dict[str, Any] = {}
        for attr in self._GetObjAttrsName():
            settings[attr] = getattr(self, attr)
        
        # Turning 'settings' to bytes (pickling and encoding)...
        binSettings = pickle.dumps(settings)
        binSettings = base64.b64encode(binSettings)
        
        # Signing the settings...
        signature_ = hmac.digest(
            key=self._secret_key,
            msg=binSettings,
            digest=hashlib.sha256)
        signature_ = base64.b64encode(signature_)
        
        # Writing signature and settings to the stream...
        stream.write(signature_)
        stream.write(binSettings)

    def _GetClassAttrsName(self) -> tuple[str, ...]:
        """Returns a tuple of all class attributes names."""
        return self._GetAttrsName(self.__class__)
    
    def _GetObjAttrsName(self) -> tuple[str, ...]:
        """Returns a tuple of all instance attributes names."""
        return self._GetAttrsName(self)

    def _GetAttrsName(self, obj: object) -> tuple[str, ...]:
        """Returns a tuple of public, non-callable attributes for an object."""
        attrs = [
            attr for attr in dir(obj)
            if not callable(getattr(obj, attr)) and not attr.startswith('_')]
        attrs.sort()
        return tuple(attrs)
