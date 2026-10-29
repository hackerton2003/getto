from decimal import Decimal, InvalidOperation
import logging

from services.system import SystemService

logger = logging.getLogger(__name__)


class VisitorTrackingMiddleware:
    """
    Middleware that captures incoming HTTP requests and safely records
    visitor metadata in VisitorLog via SystemService.record_visit.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Skip static, media, favicon, and admin assets
        path = request.path_info
        if not (
            path.startswith("/static/")
            or path.startswith("/media/")
            or path.startswith("/admin/")
            or path == "/favicon.ico"
        ):
            self._record_visit_safely(request)

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _record_visit_safely(self, request):
        try:
            ip_address = self._get_client_ip(request)
            user_agent = (
                request.META.get("HTTP_USER_AGENT", "")[:500]
                if request.META.get("HTTP_USER_AGENT")
                else None
            )

            # Optional client/proxy geolocation headers
            lat_str = request.META.get("HTTP_X_LATITUDE")
            lon_str = request.META.get("HTTP_X_LONGITUDE")
            location_name = request.META.get("HTTP_X_LOCATION_NAME")

            latitude = None
            longitude = None
            if lat_str:
                try:
                    latitude = Decimal(str(lat_str))
                except (InvalidOperation, TypeError, ValueError):
                    pass
            if lon_str:
                try:
                    longitude = Decimal(str(lon_str))
                except (InvalidOperation, TypeError, ValueError):
                    pass

            SystemService.record_visit(
                ip_address=ip_address,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
                user_agent=user_agent,
            )
        except Exception:
            # Visitor logging is best-effort and must not fail the request, but
            # infrastructure or programming errors should remain observable.
            logger.exception("Failed to record visitor log")
