from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django_filters.rest_framework import BooleanFilter
from django_filters.rest_framework import FilterSet

from documents.filters import CHAR_KWARGS


class UserFilterSet(FilterSet):
    is_signer = BooleanFilter(method="filter_is_signer")

    def filter_is_signer(self, queryset, name, value):
        if value:
            return queryset.filter(groups__built_in_identity__key="signers").distinct()
        return queryset.exclude(groups__built_in_identity__key="signers").distinct()

    class Meta:
        model = User
        fields = {"username": CHAR_KWARGS}


class GroupFilterSet(FilterSet):
    class Meta:
        model = Group
        fields = {"name": CHAR_KWARGS}
