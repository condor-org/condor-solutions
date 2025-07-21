# apps/pagos_core/filters.py

import django_filters
from apps.pagos_core.models import ComprobantePago

class ComprobantePagoFilter(django_filters.FilterSet):
    desde = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    hasta = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = ComprobantePago
        fields = ["valido", "turno__id"]
