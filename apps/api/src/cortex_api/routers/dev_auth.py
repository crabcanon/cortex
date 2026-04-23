"""Local development token issuance endpoints."""

from typing import Annotated

from cortex_auth import LocalDevTokenIssueInput, issue_local_dev_token
from cortex_common import CortexSettings
from cortex_contracts import LocalDevTokenIssueRequest, LocalDevTokenIssueResponse
from cortex_contracts.openapi_examples import LOCAL_DEV_TOKEN_REQUEST_EXAMPLES
from fastapi import APIRouter, Body, Depends

from ..dependencies.runtime import get_settings

router = APIRouter(prefix="/v1/dev/auth", tags=["Dev Auth"])


def _to_issue_input(request: LocalDevTokenIssueRequest) -> LocalDevTokenIssueInput:
    return LocalDevTokenIssueInput(
        subject=request.subject,
        tenant_id=request.tenant_id,
        actor_id=request.actor_id,
        actor_ref=request.actor_ref,
        actor_type=request.actor_type,
        display_name=request.display_name,
        client_id=request.client_id,
        scopes=tuple(request.scopes),
        roles=tuple(request.roles),
        groups=tuple(request.groups),
        expires_in=request.expires_in,
        additional_claims=request.additional_claims,
    )


@router.post(
    "/token",
    response_model=LocalDevTokenIssueResponse,
    operation_id="issueLocalDevAccessToken",
    summary="Issue local development access token / 签发本地开发访问令牌",
    description=(
        "Available only when `CORTEX_ENV=local` and `CORTEX_AUTH_MODE=dev`. Issues a local "
        "`dev:` bearer token for Swagger UI, curl, and smoke tests. This route is not mounted "
        "in non-local deployments. / 仅当 `CORTEX_ENV=local` 且 `CORTEX_AUTH_MODE=dev` "
        "时才会暴露。该接口用于生成本地 `dev:` Bearer token，便于 Swagger、curl 和"
        "冒烟测试使用；在非本地部署中不会挂载。"
    ),
    responses={
        200: {"description": "Local development token issued. / 已签发本地开发令牌。"},
        422: {"description": "Validation error. / 请求体验证失败。"},
    },
)
async def issue_local_development_access_token(
    request: Annotated[
        LocalDevTokenIssueRequest,
        Body(
            openapi_examples=LOCAL_DEV_TOKEN_REQUEST_EXAMPLES,
            description=(
                "Local development token request. In the simplest case only `subject` and "
                "`tenant_id` are required. / 本地开发令牌请求，最简单时只需要填写 "
                "`subject` 和 `tenant_id`。"
            ),
        ),
    ],
    settings: Annotated[CortexSettings, Depends(get_settings)],
) -> LocalDevTokenIssueResponse:
    result = issue_local_dev_token(settings.auth, _to_issue_input(request))
    return LocalDevTokenIssueResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        issued_at=result.issued_at,
        expires_at=result.expires_at,
        scope=result.scope,
        subject=result.subject,
        tenant_id=result.tenant_id,
        issuer=result.issuer,
        audience=result.audience,
        swagger_authorize_value=result.access_token,
        authorization_header=result.authorization_header,
    )
