import math
import django_filters
from django.db.models import Q

from apps.properties.models import Property, Room


class PropertyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    region = django_filters.NumberFilter(field_name="street__ward__district__region_id")
    region_id = django_filters.NumberFilter(field_name="street__ward__district__region_id")
    district = django_filters.NumberFilter(field_name="street__ward__district_id")
    district_id = django_filters.NumberFilter(field_name="street__ward__district_id")
    ward = django_filters.NumberFilter(field_name="street__ward_id")
    ward_id = django_filters.NumberFilter(field_name="street__ward_id")
    street = django_filters.NumberFilter(field_name="street_id")
    street_id = django_filters.NumberFilter(field_name="street_id")
    min_price = django_filters.NumberFilter(method="filter_min_price")
    max_price = django_filters.NumberFilter(method="filter_max_price")
    room_type = django_filters.CharFilter(method="filter_room_type")
    available_only = django_filters.BooleanFilter(method="filter_available_only")
    min_available_rooms = django_filters.NumberFilter(field_name="available_rooms", lookup_expr="gte")
    university = django_filters.NumberFilter(method="filter_by_university")
    university_id = django_filters.NumberFilter(method="filter_by_university")
    campus = django_filters.NumberFilter(method="filter_by_campus")
    campus_id = django_filters.NumberFilter(method="filter_by_campus")
    latitude = django_filters.NumberFilter(method="filter_no_op")
    longitude = django_filters.NumberFilter(method="filter_no_op")
    max_distance_km = django_filters.NumberFilter(method="filter_proximity")

    class Meta:
        model = Property
        fields = [
            "name",
            "region",
            "region_id",
            "district",
            "district_id",
            "ward",
            "ward_id",
            "street",
            "street_id",
            "min_price",
            "max_price",
            "room_type",
            "available_only",
            "min_available_rooms",
            "university",
            "university_id",
            "campus",
            "campus_id",
            "max_distance_km",
        ]

    def filter_no_op(self, queryset, name, value):
        return queryset

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(rooms__price__gte=value).distinct()

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(rooms__price__lte=value).distinct()

    def filter_room_type(self, queryset, name, value):
        return queryset.filter(rooms__room_type__iexact=value).distinct()

    def filter_available_only(self, queryset, name, value):
        if value:
            return queryset.filter(available_rooms__gt=0)
        return queryset

    def filter_by_university(self, queryset, name, value):
        return queryset.filter(
            Q(street__ward__district__universities__id=value)
            | Q(street__ward__campuses__university_id=value)
        ).distinct()

    def filter_by_campus(self, queryset, name, value):
        from apps.universities.models import Campus
        campus = Campus.objects.filter(pk=value).first()
        if not campus:
            return queryset.none()
        return queryset.filter(
            Q(street__ward_id=campus.ward_id)
            | Q(street__ward__district_id=campus.ward.district_id)
        ).distinct()

    def filter_proximity(self, queryset, name, value):
        if value is None:
            return queryset
        try:
            max_dist = float(value)
        except (ValueError, TypeError):
            return queryset

        target_lat = None
        target_lng = None

        lat_val = self.data.get("latitude")
        lng_val = self.data.get("longitude")
        if lat_val is not None and lng_val is not None:
            try:
                target_lat = float(lat_val)
                target_lng = float(lng_val)
            except (ValueError, TypeError):
                pass

        if target_lat is None:
            campus_id = self.data.get("campus_id") or self.data.get("campus")
            if campus_id:
                from apps.universities.models import Campus
                campus = Campus.objects.filter(pk=campus_id).first()
                if campus and campus.latitude is not None and campus.longitude is not None:
                    target_lat = float(campus.latitude)
                    target_lng = float(campus.longitude)

        if target_lat is None:
            university_id = self.data.get("university_id") or self.data.get("university")
            if university_id:
                from apps.universities.models import Campus
                campus = Campus.objects.filter(university_id=university_id).first()
                if campus and campus.latitude is not None and campus.longitude is not None:
                    target_lat = float(campus.latitude)
                    target_lng = float(campus.longitude)

        if target_lat is None or target_lng is None:
            return queryset

        lat_delta = max_dist / 111.0
        lng_delta = max_dist / (111.0 * max(0.01, math.cos(math.radians(target_lat))))

        candidates = queryset.filter(
            latitude__gte=target_lat - lat_delta,
            latitude__lte=target_lat + lat_delta,
            longitude__gte=target_lng - lng_delta,
            longitude__lte=target_lng + lng_delta,
        )

        matching_ids = []
        for prop in candidates:
            p_lat = float(prop.latitude)
            p_lng = float(prop.longitude)
            dlat = math.radians(p_lat - target_lat)
            dlng = math.radians(p_lng - target_lng)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(target_lat))
                * math.cos(math.radians(p_lat))
                * math.sin(dlng / 2) ** 2
            )
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist_km = 6371.0 * c
            if dist_km <= max_dist:
                matching_ids.append(prop.pk)

        return queryset.filter(pk__in=matching_ids)


class RoomFilter(django_filters.FilterSet):
    property = django_filters.NumberFilter(field_name="property_id")
    property_id = django_filters.NumberFilter(field_name="property_id")
    room_type = django_filters.CharFilter(field_name="room_type", lookup_expr="iexact")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    capacity = django_filters.NumberFilter(field_name="capacity")
    min_capacity = django_filters.NumberFilter(field_name="capacity", lookup_expr="gte")
    region_id = django_filters.NumberFilter(field_name="property__street__ward__district__region_id")
    district_id = django_filters.NumberFilter(field_name="property__street__ward__district_id")
    ward_id = django_filters.NumberFilter(field_name="property__street__ward_id")

    class Meta:
        model = Room
        fields = [
            "property",
            "property_id",
            "room_type",
            "min_price",
            "max_price",
            "status",
            "capacity",
            "min_capacity",
            "region_id",
            "district_id",
            "ward_id",
        ]
