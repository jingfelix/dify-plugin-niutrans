from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from src.niutrans import *


class DifyPluginPdmTemplateProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            plugin = NiuTransPlugin(credentials=NiuTransCredentials(**credentials))
            plugin.verify()  # Call the verification method to validate credentials

        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
