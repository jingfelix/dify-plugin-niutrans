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
            help="您的应用唯一标识，在'控制台->API应用'中查看",
            placeholder="请输入您的App ID",
            type=CredentialType.secret_input,
            required=True,
        ),
    ] = ""

    apikey: Annotated[
        str,
        Credential(
            name="apikey",
            label="API Key",
            help="您的API密钥，在'控制台->API应用'中查看",
            placeholder="请输入您的API Key",
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
            raise Exception(f"凭据验证失败: {str(e)}")

    @tool(
        name="translate_text",
        label="翻译文本",
        description="将文本从一种语言翻译为另一种语言",
    )
    def translate_text(
        self,
        text: Annotated[
            str,
            Param(
                name="text",
                label="待翻译文本",
                description="需要翻译的文本内容",
                llm_description="需要翻译的文本内容",
                type=ParamType.string,
                required=True,
            ),
        ],
        from_language: Annotated[
            str,
            Param(
                name="from_language",
                label="源语言",
                description="源语言代码，例如：zh(中文)、en(英文)、ja(日文)、ko(韩文)等",
                llm_description="源语言代码，例如：zh(中文)、en(英文)、ja(日文)、ko(韩文)等。如果不提供，系统将自动检测",
                type=ParamType.string,
                required=False,
            ),
        ] = "",
        to_language: Annotated[
            str,
            Param(
                name="to_language",
                label="目标语言",
                description="目标语言代码，例如：zh(中文)、en(英文)、ja(日文)、ko(韩文)等",
                llm_description="目标语言代码，例如：zh(中文)、en(英文)、ja(日文)、ko(韩文)等",
                type=ParamType.string,
                required=True,
            ),
        ] = "en",
    ) -> Generator:
        """翻译文本"""
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
                raise Exception(f"翻译失败: {result.errorMsg}")

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
            raise Exception(f"翻译请求失败: {str(e)}")


plugin = NiuTransPlugin(
    meta=MetaInfo(
        name="niutrans",
        author="langgenius",
        description="使用小牛翻译API进行文本翻译",
        version="0.1.0",
        label="小牛翻译",
        icon="icon.svg",
    )
)
