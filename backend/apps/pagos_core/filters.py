# apps/pagos_core/filters.py

import django_filters
from django.db.models import Exists, OuterRef
from apps.pagos_core.models import ComprobantePago, PagoIntento


class ComprobantePagoFilter(django_filters.FilterSet):
    desde = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    hasta = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")
    solo_preaprobados = django_filters.BooleanFilter(method="filter_solo_preaprobados")

    class Meta:
        model = ComprobantePago
        fields = ["valido", "turno__id", "solo_preaprobados"]

    def filter_solo_preaprobados(self, queryset, name, value):
        if value:
            subquery = PagoIntento.objects.filter(
                content_type__model="comprobantepago",
                object_id=OuterRef("pk"),
                estado="pre_aprobado"
            )
            return queryset.filter(Exists(subquery))
        return queryset
