import hashlib
import time
from typing import Annotated, Generator, Optional

import httpx
from dify_easy.model import (
    BasePlugin,
    Credential,
    CredentialType,
    MetaInfo,
    Param,
    ParamType,
    provider,
    tool,
)
from pydantic import BaseModel, Field


class TransResponse(BaseModel):
    from_: Optional[str] = Field(..., alias="from")
    to: Optional[str] = ""
    tgtText: Optional[str] = ""
    srcText: Optional[str] = ""
    errorCode: Optional[str] = ""
    errorMsg: Optional[str] = ""


# class MemResponse(BaseModel):
#     code: int
#     msg: Optional[str] = ""
#     data: Optional[dict] = {}


class NiuTransCredentials(BaseModel):
    app_id: Annotated[
        str,
        Credential(
            name="app_id",
            label="App ID",
            help="Your unique application identifier, view in 'Console->API Applications'",
            placeholder="Please enter your App ID",
            type=CredentialType.secret_input,
            required=True,
        ),
    ] = ""

    apikey: Annotated[
        str,
        Credential(
            name="apikey",
            label="API Key",
            help="Your API key, view in 'Console->API Applications'",
            placeholder="Please enter your API Key",
            type=CredentialType.secret_input,
            required=True,
        ),
    ] = ""


class NiuTransPlugin(BasePlugin):
    credentials: NiuTransCredentials = NiuTransCredentials()
    api_url: str = "https://api.niutrans.com"
    trans_url: str = api_url + "/v2/text/translate"
    mem_db_url: str = api_url + "/v2/memory_db"

    def generate_auth_str(self, params: dict) -> str:
        sorted_params = sorted(
            list(params.items()) + [("apikey", self.credentials.apikey)],
            key=lambda x: x[0],
        )
        param_str = "&".join([f"{key}={value}" for key, value in sorted_params])
        md5 = hashlib.md5()
        md5.update(param_str.encode("utf-8"))
        auth_str = md5.hexdigest()
        return auth_str

    @provider
    def verify(self):
        try:
            data = {
                "from": "en",
                "to": "zh",
                "srcText": "testing",
                "appId": self.credentials.app_id,
                "timestamp": int(time.time()),
            }

            auth_str = self.generate_auth_str(data)
            data["authStr"] = auth_str

            response = httpx.post(self.trans_url, data=data, timeout=30)
            response.raise_for_status()

            result = TransResponse(**response.json())
            code = result.errorCode
            if code != "":
                raise Exception(f"Error code: {code}, message: {result.errorMsg}")

        except Exception as e:
            raise Exception(f"Credential verification failed: {str(e)}")

    @tool(
        name="translate_text",
        label="Translate Text",
        description="Translate text from one language to another",
    )
    def translate_text(
        self,
        text: Annotated[
            str,
            Param(
                name="text",
                label="Text to Translate",
                description="The text content to be translated",
                llm_description="The text content to be translated",
                type=ParamType.string,
                required=True,
            ),
        ],
        from_language: Annotated[
            str,
            Param(
                name="from_language",
                label="Source Language",
                description="Source language code, e.g.: zh(Chinese), en(English), ja(Japanese), ko(Korean), etc.",
                llm_description="Source language code, e.g.: zh(Chinese), en(English), ja(Japanese), ko(Korean), etc. If not provided, the system will auto-detect",
                type=ParamType.string,
                required=False,
            ),
        ] = "",
        to_language: Annotated[
            str,
            Param(
                name="to_language",
                label="Target Language",
                description="Target language code, e.g.: zh(Chinese), en(English), ja(Japanese), ko(Korean), etc.",
                llm_description="Target language code, e.g.: zh(Chinese), en(English), ja(Japanese), ko(Korean), etc.",
                type=ParamType.string,
                required=True,
            ),
        ] = "en",
    ) -> Generator:
        """Translate text"""
        data = {
            "from": from_language,
            "to": to_language,
            "appId": self.credentials.app_id,
            "timestamp": int(time.time()),
            "srcText": text,
        }

        auth_str = self.generate_auth_str(data)
        data["authStr"] = auth_str

        try:
            response = httpx.post(self.trans_url, data=data, timeout=30)
            response.raise_for_status()

            result = TransResponse(**response.json())

            if result.errorCode != "":
                raise Exception(f"Translation failed: {result.errorMsg}")

            translated_text = result.tgtText

            yield {
                "translated_text": translated_text,
                "source_language": from_language or "auto",
                "target_language": to_language,
                "original_text": text,
                "error_code": result.errorCode,
                "error_msg": result.errorMsg,
            }
            yield translated_text

        except Exception as e:
            raise Exception(f"Translation request failed: {str(e)}")


plugin = NiuTransPlugin(
    meta=MetaInfo(
        name="niutrans",
        author="langgenius",
        description="Text translation using NiuTrans API",
        version="0.1.0",
        label="NiuTrans",
        icon="icon.svg",
    )
)
