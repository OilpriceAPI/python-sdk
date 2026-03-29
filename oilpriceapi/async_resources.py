from __future__ import annotations

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date

from .models import DieselPrice, DieselStationsResponse, PriceAlert
from .exceptions import ValidationError
from .resource_validators import VALID_OPERATORS, format_date


class AsyncDieselResource:
    def __init__(self, client):
        self.client = client

    async def get_price(self, state: str) -> DieselPrice:
        if not isinstance(state, str):
            raise ValidationError(message="State code must be a string", field="state", value=state)
        if len(state) != 2:
            raise ValidationError(
                message="State code must be a 2-letter US state code (e.g., 'CA', 'TX')",
                field="state", value=state
            )
        response = await self.client.request(
            method="GET", path="/v1/diesel-prices", params={"state": state.upper()}
        )
        if "regional_average" in response:
            price_data = response["regional_average"]
        elif "data" in response:
            price_data = response["data"]
        else:
            price_data = response
        return DieselPrice(**price_data)

    async def get_stations(self, lat: float, lng: float, radius: Optional[float] = 8047) -> DieselStationsResponse:
        if not isinstance(lat, (int, float)):
            raise ValidationError(message="Latitude must be a number", field="lat", value=lat)
        if not isinstance(lng, (int, float)):
            raise ValidationError(message="Longitude must be a number", field="lng", value=lng)
        if lat < -90 or lat > 90:
            raise ValidationError(message="Latitude must be between -90 and 90", field="lat", value=lat)
        if lng < -180 or lng > 180:
            raise ValidationError(message="Longitude must be between -180 and 180", field="lng", value=lng)
        if radius is not None:
            if not isinstance(radius, (int, float)):
                raise ValidationError(message="Radius must be a number", field="radius", value=radius)
            if radius < 0 or radius > 50000:
                raise ValidationError(
                    message="Radius must be between 0 and 50000 meters", field="radius", value=radius
                )
        response = await self.client.request(
            method="POST", path="/v1/diesel-prices/stations",
            json_data={"lat": lat, "lng": lng, "radius": radius}
        )
        return DieselStationsResponse(**response)


class AsyncAlertsResource:
    def __init__(self, client):
        self.client = client

    async def list(self) -> List[PriceAlert]:
        response = await self.client.request(method="GET", path="/v1/alerts")
        if isinstance(response, list):
            alerts_data = response
        elif "alerts" in response:
            alerts_data = response["alerts"]
        elif "data" in response:
            alerts_data = response["data"]
        else:
            alerts_data = []
        return [PriceAlert(**a) for a in alerts_data]

    async def get(self, alert_id: str) -> PriceAlert:
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string", field="alert_id", value=alert_id
            )
        response = await self.client.request(method="GET", path=f"/v1/alerts/{alert_id}")
        if isinstance(response, dict) and "id" in response:
            alert_data = response
        elif "alert" in response:
            alert_data = response["alert"]
        elif "data" in response:
            alert_data = response["data"]
        else:
            alert_data = response
        return PriceAlert(**alert_data)

    async def create(
        self,
        name: str,
        commodity_code: str,
        condition_operator: str,
        condition_value: float,
        webhook_url: Optional[str] = None,
        enabled: bool = True,
        cooldown_minutes: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PriceAlert:
        if not name or not isinstance(name, str):
            raise ValidationError(
                message="Alert name is required and must be a string", field="name", value=name
            )
        if len(name) < 1 or len(name) > 100:
            raise ValidationError(message="Alert name must be 1-100 characters", field="name", value=name)
        if not commodity_code or not isinstance(commodity_code, str):
            raise ValidationError(
                message="Commodity code is required and must be a string",
                field="commodity_code", value=commodity_code
            )
        if not condition_operator:
            raise ValidationError(
                message="Condition operator is required", field="condition_operator", value=condition_operator
            )
        if condition_operator not in VALID_OPERATORS:
            raise ValidationError(
                message=f"Invalid operator. Must be one of: {', '.join(VALID_OPERATORS)}",
                field="condition_operator", value=condition_operator
            )
        if not isinstance(condition_value, (int, float)):
            raise ValidationError(
                message="Condition value must be a number", field="condition_value", value=condition_value
            )
        if condition_value <= 0 or condition_value > 1_000_000:
            raise ValidationError(
                message="Condition value must be greater than 0 and less than or equal to 1,000,000",
                field="condition_value", value=condition_value
            )
        if webhook_url is not None:
            if not isinstance(webhook_url, str):
                raise ValidationError(
                    message="Webhook URL must be a string", field="webhook_url", value=webhook_url
                )
            if webhook_url and not webhook_url.startswith('https://'):
                raise ValidationError(
                    message="Webhook URL must use HTTPS protocol", field="webhook_url", value=webhook_url
                )
        if not isinstance(cooldown_minutes, int):
            raise ValidationError(
                message="Cooldown minutes must be an integer", field="cooldown_minutes", value=cooldown_minutes
            )
        if cooldown_minutes < 0 or cooldown_minutes > 1440:
            raise ValidationError(
                message="Cooldown minutes must be between 0 and 1440 (24 hours)",
                field="cooldown_minutes", value=cooldown_minutes
            )
        response = await self.client.request(
            method="POST", path="/v1/alerts",
            json_data={"price_alert": {
                "name": name, "commodity_code": commodity_code,
                "condition_operator": condition_operator, "condition_value": condition_value,
                "webhook_url": webhook_url, "enabled": enabled,
                "cooldown_minutes": cooldown_minutes, "metadata": metadata
            }}
        )
        if isinstance(response, dict) and "id" in response:
            alert_data = response
        elif "alert" in response:
            alert_data = response["alert"]
        elif "data" in response:
            alert_data = response["data"]
        else:
            alert_data = response
        return PriceAlert(**alert_data)

    async def update(
        self,
        alert_id: str,
        name: Optional[str] = None,
        commodity_code: Optional[str] = None,
        condition_operator: Optional[str] = None,
        condition_value: Optional[float] = None,
        webhook_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        cooldown_minutes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PriceAlert:
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string", field="alert_id", value=alert_id
            )
        update_data: Dict[str, Any] = {}
        if name is not None:
            if not isinstance(name, str) or len(name) < 1 or len(name) > 100:
                raise ValidationError(
                    message="Alert name must be 1-100 characters", field="name", value=name
                )
            update_data["name"] = name
        if commodity_code is not None:
            update_data["commodity_code"] = commodity_code
        if condition_operator is not None:
            if condition_operator not in VALID_OPERATORS:
                raise ValidationError(
                    message=f"Invalid operator. Must be one of: {', '.join(VALID_OPERATORS)}",
                    field="condition_operator", value=condition_operator
                )
            update_data["condition_operator"] = condition_operator
        if condition_value is not None:
            if not isinstance(condition_value, (int, float)):
                raise ValidationError(
                    message="Condition value must be a number", field="condition_value", value=condition_value
                )
            if condition_value <= 0 or condition_value > 1_000_000:
                raise ValidationError(
                    message="Condition value must be greater than 0 and less than or equal to 1,000,000",
                    field="condition_value", value=condition_value
                )
            update_data["condition_value"] = condition_value
        if webhook_url is not None:
            if webhook_url and (not isinstance(webhook_url, str) or not webhook_url.startswith('https://')):
                raise ValidationError(
                    message="Webhook URL must be a valid HTTPS URL", field="webhook_url", value=webhook_url
                )
            update_data["webhook_url"] = webhook_url
        if enabled is not None:
            update_data["enabled"] = enabled
        if cooldown_minutes is not None:
            if not isinstance(cooldown_minutes, int) or cooldown_minutes < 0 or cooldown_minutes > 1440:
                raise ValidationError(
                    message="Cooldown minutes must be between 0 and 1440 (24 hours)",
                    field="cooldown_minutes", value=cooldown_minutes
                )
            update_data["cooldown_minutes"] = cooldown_minutes
        if metadata is not None:
            update_data["metadata"] = metadata
        response = await self.client.request(
            method="PATCH", path=f"/v1/alerts/{alert_id}",
            json_data={"price_alert": update_data}
        )
        if isinstance(response, dict) and "id" in response:
            alert_data = response
        elif "alert" in response:
            alert_data = response["alert"]
        elif "data" in response:
            alert_data = response["data"]
        else:
            alert_data = response
        return PriceAlert(**alert_data)

    async def delete(self, alert_id: str) -> None:
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string", field="alert_id", value=alert_id
            )
        await self.client.request(method="DELETE", path=f"/v1/alerts/{alert_id}")

    async def test(self, alert_id: str) -> Dict[str, Any]:
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string", field="alert_id", value=alert_id
            )
        response = await self.client.request(method="POST", path=f"/v1/alerts/{alert_id}/test")
        if "data" in response:
            return response["data"]
        return response

    async def triggers(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/alerts/triggers", params=params)
        if isinstance(response, list):
            return response
        elif "triggers" in response:
            return response["triggers"]
        elif "data" in response:
            return response["data"]
        return []

    async def analytics_history(self, **params) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/alerts/analytics_history", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncCommoditiesResource:
    def __init__(self, client):
        self.client = client

    async def list(self) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/commodities")
        if "data" in response:
            return response["data"]
        return response

    async def get(self, code: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/commodities/{code}")
        if "data" in response:
            return response["data"]
        return response

    async def categories(self) -> Dict[str, List[Dict[str, Any]]]:
        response = await self.client.request(method="GET", path="/v1/commodities/categories")
        if "data" in response:
            return response["data"]
        return response


class AsyncFuturesResource:
    def __init__(self, client):
        self.client = client

    async def latest(self, contract: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/futures/{contract}")
        if "data" in response:
            return response["data"]
        return response

    async def historical(
        self,
        contract: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        params = {}
        if start_date:
            params["start_date"] = format_date(start_date)
        if end_date:
            params["end_date"] = format_date(end_date)
        response = await self.client.request(
            method="GET", path=f"/v1/futures/{contract}/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def ohlc(self, contract: str, date: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if date:
            params["date"] = date
        response = await self.client.request(
            method="GET", path=f"/v1/futures/{contract}/ohlc", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def intraday(self, contract: str) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path=f"/v1/futures/{contract}/intraday")
        if "data" in response:
            return response["data"]
        return response

    async def spreads(self, contract1: str, contract2: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/futures/spreads",
            params={"contract1": contract1, "contract2": contract2}
        )
        if "data" in response:
            return response["data"]
        return response

    async def curve(self, contract: str) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path=f"/v1/futures/{contract}/curve")
        if "data" in response:
            return response["data"]
        return response

    async def continuous(self, contract: str, months: int = 12) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path=f"/v1/futures/{contract}/continuous", params={"months": months}
        )
        if "data" in response:
            return response["data"]
        return response

class AsyncStorageResource:
    def __init__(self, client):
        self.client = client

    async def all(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/storage")
        if "data" in response:
            return response["data"]
        return response

    async def cushing(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/storage/cushing")
        if "data" in response:
            return response["data"]
        return response

    async def spr(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/storage/spr")
        if "data" in response:
            return response["data"]
        return response

    async def regional(self, region: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if region:
            params["region"] = region
        response = await self.client.request(method="GET", path="/v1/storage/regional", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def history(
        self,
        code: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        params = {}
        if start_date:
            params["start_date"] = format_date(start_date)
        if end_date:
            params["end_date"] = format_date(end_date)
        response = await self.client.request(
            method="GET", path=f"/v1/storage/{code}/history", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncRigCountsResource:
    def __init__(self, client):
        self.client = client

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/rig-counts/latest")
        if "data" in response:
            return response["data"]
        return response

    async def current(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/rig-counts/current")
        if "data" in response:
            return response["data"]
        return response

    async def historical(
        self,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        params = {}
        if start_date:
            params["start_date"] = format_date(start_date)
        if end_date:
            params["end_date"] = format_date(end_date)
        response = await self.client.request(
            method="GET", path="/v1/rig-counts/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def trends(self, period: str = "monthly") -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/rig-counts/trends", params={"period": period}
        )
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/rig-counts/summary")
        if "data" in response:
            return response["data"]
        return response



class AsyncBunkerFuelsResource:
    def __init__(self, client):
        self.client = client

    async def all(self) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/bunker-fuels")
        if "data" in response:
            return response["data"]
        return response

    async def port(self, code: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/bunker-fuels/ports/{code}")
        if "data" in response:
            return response["data"]
        return response

    async def compare(self, ports: List[str]) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/bunker-fuels/compare", params={"ports": ",".join(ports)}
        )
        if "data" in response:
            return response["data"]
        return response

    async def spreads(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/bunker-fuels/spreads")
        if "data" in response:
            return response["data"]
        return response

    async def historical(
        self,
        port: str,
        fuel_type: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"port": port, "fuel_type": fuel_type}
        if start_date:
            params["start_date"] = format_date(start_date)
        if end_date:
            params["end_date"] = format_date(end_date)
        response = await self.client.request(
            method="GET", path="/v1/bunker-fuels/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def export(self, format: str = "json") -> Any:
        response = await self.client.request(
            method="GET", path="/v1/bunker-fuels/export", params={"format": format}
        )
        if format != "json":
            return response
        if "data" in response:
            return response["data"]
        return response


class AsyncAnalyticsResource:
    def __init__(self, client):
        self.client = client

    async def performance(self, commodity: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        params: Dict[str, Any] = {"days": days}
        if commodity:
            params["commodity"] = commodity
        response = await self.client.request(
            method="GET", path="/v1/analytics/performance", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def statistics(self, commodity: str, days: int = 30) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/analytics/statistics",
            params={"commodity": commodity, "days": days}
        )
        if "data" in response:
            return response["data"]
        return response

    async def correlation(self, commodity1: str, commodity2: str, days: int = 90) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/analytics/correlation",
            params={"commodity1": commodity1, "commodity2": commodity2, "days": days}
        )
        if "data" in response:
            return response["data"]
        return response

    async def trend(self, commodity: str, days: int = 30) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/analytics/trend",
            params={"commodity": commodity, "days": days}
        )
        if "data" in response:
            return response["data"]
        return response

    async def spread(self, commodity1: str, commodity2: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/analytics/spread",
            params={"commodity1": commodity1, "commodity2": commodity2}
        )
        if "data" in response:
            return response["data"]
        return response

    async def forecast(self, commodity: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/analytics/forecast", params={"commodity": commodity}
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncForecastsResource:
    def __init__(self, client):
        self.client = client

    async def monthly(self, commodity: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if commodity:
            params["commodity"] = commodity
        response = await self.client.request(
            method="GET", path="/v1/forecasts/monthly", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def accuracy(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/forecasts/accuracy")
        if "data" in response:
            return response["data"]
        return response

    async def archive(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        params = {}
        if year:
            params["year"] = year
        response = await self.client.request(
            method="GET", path="/v1/forecasts/archive", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def get(self, period: str, commodity: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if commodity:
            params["commodity"] = commodity
        response = await self.client.request(
            method="GET", path=f"/v1/forecasts/monthly/{period}", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncDataQualityResource:
    def __init__(self, client):
        self.client = client

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/data-quality/summary")
        if "data" in response:
            return response["data"]
        return response

    async def reports(self) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/data-quality/reports")
        if "data" in response:
            return response["data"]
        return response

    async def report(self, code: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/data-quality/reports/{code}")
        if "data" in response:
            return response["data"]
        return response


class AsyncDrillingIntelligenceResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/drilling-intelligence/latest")
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/drilling-intelligence/summary")
        if "data" in response:
            return response["data"]
        return response

    async def trends(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence/trends", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def frac_spreads(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence/frac-spreads", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def well_permits(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence/well-permits", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def duc_wells(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence/duc-wells", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def completions(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence/completions", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def wells_drilled(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/drilling-intelligence/wells-drilled", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def basin(self, name: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path=f"/v1/drilling-intelligence/basin/{name}"
        )
        if "data" in response:
            return response["data"]
        return response


# EI sub-resources

class AsyncEIRigCountsResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/ei/rig_counts", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/ei/rig_counts/{id}")
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/rig_counts/latest")
        if "data" in response:
            return response["data"]
        return response

    async def by_basin(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/rig_counts/by_basin", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def by_state(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/rig_counts/by_state", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def historical(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/rig_counts/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncEIOilInventoriesResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/ei/oil_inventories", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/ei/oil_inventories/{id}")
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/oil_inventories/latest")
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/oil_inventories/summary")
        if "data" in response:
            return response["data"]
        return response

    async def by_product(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/oil_inventories/by_product", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def historical(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/oil_inventories/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def cushing(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/oil_inventories/cushing")
        if "data" in response:
            return response["data"]
        return response


class AsyncEIOpecProductionResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/ei/opec_productions", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/ei/opec_productions/{id}")
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/opec_productions/latest")
        if "data" in response:
            return response["data"]
        return response

    async def total(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/opec_productions/total")
        if "data" in response:
            return response["data"]
        return response

    async def by_country(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/opec_productions/by_country", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def historical(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/opec_productions/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def top_producers(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/opec_productions/top_producers", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncEIDrillingProductivityResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path=f"/v1/ei/drilling_productivities/{id}"
        )
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities/latest"
        )
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities/summary"
        )
        if "data" in response:
            return response["data"]
        return response

    async def duc_wells(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities/duc_wells", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def by_basin(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities/by_basin", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def historical(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def trends(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/drilling_productivities/trends", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncEIForecastsResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/ei/forecasts", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/ei/forecasts/{id}")
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/forecasts/latest")
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/forecasts/summary")
        if "data" in response:
            return response["data"]
        return response

    async def prices(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/forecasts/prices", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def production(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/forecasts/production", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def historical(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/forecasts/historical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def compare(self, **params) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path="/v1/ei/forecasts/compare", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncEIWellPermitsResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/ei/well-permits", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/ei/well-permits/{id}")
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/well-permits/latest")
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/well-permits/summary")
        if "data" in response:
            return response["data"]
        return response

    async def by_state(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/well-permits/by-state", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def by_operator(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/well-permits/by-operator", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def by_formation(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/well-permits/by-formation", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def search(self, query: str, **params) -> List[Dict[str, Any]]:
        params["query"] = query
        response = await self.client.request(
            method="GET", path="/v1/ei/well-permits/search", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncEIFracFocusResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/ei/frac-focus", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/ei/frac-focus/{id}")
        if "data" in response:
            return response["data"]
        return response

    async def latest(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/frac-focus/latest")
        if "data" in response:
            return response["data"]
        return response

    async def summary(self) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path="/v1/ei/frac-focus/summary")
        if "data" in response:
            return response["data"]
        return response

    async def by_state(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/frac-focus/by-state", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def by_operator(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/frac-focus/by-operator", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def by_chemical(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path="/v1/ei/frac-focus/by-chemical", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def search(self, query: str, **params) -> List[Dict[str, Any]]:
        params["query"] = query
        response = await self.client.request(
            method="GET", path="/v1/ei/frac-focus/search", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def chemicals(self, id: str) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path=f"/v1/ei/frac-focus/{id}/chemicals"
        )
        if "data" in response:
            return response["data"]
        return response

    async def for_well(self, api_number: str) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path=f"/v1/ei/frac-focus/for-well/{api_number}"
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncEnergyIntelligenceResource:
    def __init__(self, client):
        self.client = client
        self.rig_counts = AsyncEIRigCountsResource(client)
        self.oil_inventories = AsyncEIOilInventoriesResource(client)
        self.opec_production = AsyncEIOpecProductionResource(client)
        self.drilling_productivity = AsyncEIDrillingProductivityResource(client)
        self.forecasts = AsyncEIForecastsResource(client)
        self.well_permits = AsyncEIWellPermitsResource(client)
        self.frac_focus = AsyncEIFracFocusResource(client)

    async def well_timeline(self, api_number: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path=f"/v1/ei/wells/{api_number}/timeline"
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncWebhooksResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/webhooks", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, webhook_id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/webhooks/{webhook_id}")
        if "data" in response:
            return response["data"]
        return response

    async def create(
        self,
        url: str,
        events: List[str],
        description: Optional[str] = None,
        secret: Optional[str] = None,
        enabled: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        json_data: Dict[str, Any] = {"url": url, "events": events, "enabled": enabled}
        if description:
            json_data["description"] = description
        if secret:
            json_data["secret"] = secret
        json_data.update(kwargs)
        response = await self.client.request(method="POST", path="/v1/webhooks", json_data=json_data)
        if "data" in response:
            return response["data"]
        return response

    async def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        secret: Optional[str] = None,
        enabled: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        json_data: Dict[str, Any] = {}
        if url is not None:
            json_data["url"] = url
        if events is not None:
            json_data["events"] = events
        if description is not None:
            json_data["description"] = description
        if secret is not None:
            json_data["secret"] = secret
        if enabled is not None:
            json_data["enabled"] = enabled
        json_data.update(kwargs)
        response = await self.client.request(
            method="PATCH", path=f"/v1/webhooks/{webhook_id}", json_data=json_data
        )
        if "data" in response:
            return response["data"]
        return response

    async def delete(self, webhook_id: str) -> None:
        await self.client.request(method="DELETE", path=f"/v1/webhooks/{webhook_id}")

    async def test(self, webhook_id: str) -> Dict[str, Any]:
        response = await self.client.request(method="POST", path=f"/v1/webhooks/{webhook_id}/test")
        if "data" in response:
            return response["data"]
        return response

    async def events(self, webhook_id: str, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path=f"/v1/webhooks/{webhook_id}/events", params=params
        )
        if "data" in response:
            return response["data"]
        return response


class AsyncDataSourcesResource:
    def __init__(self, client):
        self.client = client

    async def list(self, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(method="GET", path="/v1/data-sources", params=params)
        if "data" in response:
            return response["data"]
        return response

    async def get(self, source_id: str) -> Dict[str, Any]:
        response = await self.client.request(method="GET", path=f"/v1/data-sources/{source_id}")
        if "data" in response:
            return response["data"]
        return response

    async def create(
        self,
        name: str,
        source_type: str,
        credentials: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        json_data: Dict[str, Any] = {
            "name": name, "source_type": source_type,
            "credentials": credentials, "enabled": enabled
        }
        if config:
            json_data["config"] = config
        json_data.update(kwargs)
        response = await self.client.request(
            method="POST", path="/v1/data-sources", json_data=json_data
        )
        if "data" in response:
            return response["data"]
        return response

    async def update(
        self,
        source_id: str,
        name: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        json_data: Dict[str, Any] = {}
        if name is not None:
            json_data["name"] = name
        if credentials is not None:
            json_data["credentials"] = credentials
        if config is not None:
            json_data["config"] = config
        if enabled is not None:
            json_data["enabled"] = enabled
        json_data.update(kwargs)
        response = await self.client.request(
            method="PATCH", path=f"/v1/data-sources/{source_id}", json_data=json_data
        )
        if "data" in response:
            return response["data"]
        return response

    async def delete(self, source_id: str) -> None:
        await self.client.request(method="DELETE", path=f"/v1/data-sources/{source_id}")

    async def test(self, source_id: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="POST", path=f"/v1/data-sources/{source_id}/test"
        )
        if "data" in response:
            return response["data"]
        return response

    async def logs(self, source_id: str, **params) -> List[Dict[str, Any]]:
        response = await self.client.request(
            method="GET", path=f"/v1/data-sources/{source_id}/logs", params=params
        )
        if "data" in response:
            return response["data"]
        return response

    async def health(self, source_id: str) -> Dict[str, Any]:
        response = await self.client.request(
            method="GET", path=f"/v1/data-sources/{source_id}/health"
        )
        if "data" in response:
            return response["data"]
        return response

    async def rotate_credentials(self, source_id: str, new_credentials: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.client.request(
            method="POST", path=f"/v1/data-sources/{source_id}/rotate_credentials",
            json_data={"credentials": new_credentials}
        )
        if "data" in response:
            return response["data"]
        return response
