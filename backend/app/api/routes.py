from fastapi import APIRouter, Depends, Query

from app.adapters.base import NetworkDataProvider
from app.auth import Principal, require_principal
from app.config import get_settings
from app.dependencies import get_provider
from app.schemas.api import (
    AssetResponse,
    CircuitPathResponse,
    DemoOverviewResponse,
    FieldActionPlanRequest,
    FieldActionPlanResponse,
    NavigatorCapabilitiesResponse,
    NavigatorIntakeRequest,
    NavigatorIntakeResponse,
    NearbyAssetResponse,
    OTDRCorrelationRequest,
    OTDRCorrelationResponse,
    OutageImpactResponse,
    SearchResult,
)
from app.services.analysis import correlate_otdr
from app.services.navigator import navigator_capabilities, run_navigator_intake
from app.services.reports import build_field_action_plan

router = APIRouter(prefix="/api", dependencies=[Depends(require_principal)])


@router.get("/navigator/capabilities", response_model=NavigatorCapabilitiesResponse)
async def get_navigator_capabilities():
    return navigator_capabilities(get_settings())


@router.post("/navigator/intake", response_model=NavigatorIntakeResponse)
async def navigator_intake(
    request: NavigatorIntakeRequest,
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await run_navigator_intake(
        provider=provider,
        settings=get_settings(),
        messages=[message.model_dump() for message in request.messages],
    )


@router.get("/auth/me")
async def current_identity(principal: Principal = Depends(require_principal)):
    return {
        "subject": principal.subject,
        "tenant_id": principal.tenant_id,
        "display_name": principal.display_name,
        "username": principal.username,
        "scopes": principal.scopes,
        "roles": principal.roles,
    }


@router.get("/demo/overview", response_model=DemoOverviewResponse)
async def demo_overview(provider: NetworkDataProvider = Depends(get_provider)):
    return await provider.get_overview()


@router.get("/assets/search", response_model=list[SearchResult])
async def search_assets(
    q: str = Query(min_length=1, max_length=120),
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await provider.search_assets(q)


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await provider.get_asset(asset_id)


@router.get("/assets/{asset_id}/nearby", response_model=list[NearbyAssetResponse])
async def get_nearby_assets(
    asset_id: str,
    radius_ft: float = Query(default=500, gt=0, le=10000),
    provider: NetworkDataProvider = Depends(get_provider),
):
    asset = await provider.get_asset(asset_id)
    return await provider.get_assets_nearby(asset["latitude"], asset["longitude"], radius_ft)


@router.get("/circuits/{circuit_id}/path", response_model=CircuitPathResponse)
async def get_circuit_path(
    circuit_id: str,
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await provider.get_circuit_path(circuit_id)


@router.get("/service-locations/{service_location_id}/path", response_model=CircuitPathResponse)
async def get_service_path(
    service_location_id: str,
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await provider.get_service_path(service_location_id)


@router.post("/analysis/otdr-correlate", response_model=OTDRCorrelationResponse)
async def otdr_correlate(
    request: OTDRCorrelationRequest,
    provider: NetworkDataProvider = Depends(get_provider),
):
    path = await provider.get_circuit_path(request.circuit_id)
    if path["segments"][0]["start_asset_id"] != request.launch_asset_id:
        raise ValueError(f"Launch asset {request.launch_asset_id} is not the mapped path origin")
    asset_ids = {
        asset_id
        for segment in path["segments"]
        for asset_id in (segment["start_asset_id"], segment["end_asset_id"])
    }
    assets = {asset_id: await provider.get_asset(asset_id) for asset_id in asset_ids}
    return correlate_otdr(
        path,
        assets,
        request.fault_distance_ft,
        request.tolerance_ft,
    )


@router.get("/analysis/outage-impact/{asset_id}", response_model=OutageImpactResponse)
async def outage_impact(
    asset_id: str,
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await provider.calculate_outage_impact(asset_id)


@router.post("/reports/field-action-plan", response_model=FieldActionPlanResponse)
async def field_action_plan(
    request: FieldActionPlanRequest,
    provider: NetworkDataProvider = Depends(get_provider),
):
    return await build_field_action_plan(
        provider=provider,
        settings=get_settings(),
        circuit_id=request.circuit_id,
        launch_asset_id=request.launch_asset_id,
        fault_distance_ft=request.fault_distance_ft,
        tolerance_ft=request.tolerance_ft,
        impact_asset_id=request.impact_asset_id,
    )
