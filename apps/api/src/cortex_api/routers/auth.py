"""Authentication and bootstrap token issuance endpoints."""

from typing import Annotated

from cortex_auth import TokenIssueInput, TokenIssueResult, TokenIssuerService
from cortex_contracts import TokenIssueRequest, TokenIssueResponse
from cortex_contracts.openapi_examples import TOKEN_ISSUE_REQUEST_EXAMPLES
from fastapi import APIRouter, Body, Depends

from ..dependencies.auth import get_bootstrap_issuer_secret
from ..dependencies.runtime import get_token_issuer_service

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


def _to_token_issue_input(request: TokenIssueRequest) -> TokenIssueInput:
    return TokenIssueInput(
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


def _to_token_issue_response(result: TokenIssueResult) -> TokenIssueResponse:
    return TokenIssueResponse(
        access_token=result.access_token,
        issued_token_format=result.issued_token_format,  # type: ignore[arg-type]
        expires_in=result.expires_in,
        issued_at=result.issued_at,
        expires_at=result.expires_at,
        scope=result.scope,
        subject=result.subject,
        tenant_id=result.tenant_id,
        issuer=result.issuer,
        audience=result.audience,
    )


@router.post(
    "/token",
    response_model=TokenIssueResponse,
    operation_id="issueAccessToken",
    summary="Issue access token",
    description=(
        "Issue a bootstrap bearer token for local, self-hosted, "
        "or operator-driven environments. Use the "
        "`X-Cortex-Issuer-Secret` security header and copy "
        "one of the request examples directly."
    ),
)
async def issue_access_token(
    request: Annotated[
        TokenIssueRequest,
        Body(
            openapi_examples=TOKEN_ISSUE_REQUEST_EXAMPLES,
            description=(
                "Bootstrap token issuance request. Required fields are "
                "`subject`, `tenant_id`, and `scopes`; "
                "most other fields may be omitted to use the documented defaults."
            ),
        ),
    ],
    token_issuer_service: Annotated[TokenIssuerService, Depends(get_token_issuer_service)],
    bootstrap_secret: Annotated[str | None, Depends(get_bootstrap_issuer_secret)],
) -> TokenIssueResponse:
    result = token_issuer_service.issue_token(
        bootstrap_secret=bootstrap_secret,
        token_input=_to_token_issue_input(request),
    )
    return _to_token_issue_response(result)
