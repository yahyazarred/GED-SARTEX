from django.contrib.auth.models import User
from django.test import TestCase
from guardian.shortcuts import assign_perm

from documents.matching import match_cabinets
from documents.models import Cabinet
from documents.models import Document
from documents.models import MatchingModel
from documents.models import WorkflowAction
from documents.permissions import has_perms_owner_aware
from documents.permissions import permitted_document_ids
from documents.workflows.mutations import apply_assignment_to_document
from documents.workflows.mutations import apply_removal_to_document


class CabinetPermissionsTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner")
        self.viewer = User.objects.create_user("viewer")
        self.denied = User.objects.create_user("denied")
        self.cabinet = Cabinet.objects.create(name="Finance", owner=self.owner)
        self.document = Document.objects.create(
            title="Invoice",
            content="finance invoice",
            mime_type="application/pdf",
            checksum="cabinet-permission-test",
            owner=self.owner,
            cabinet=self.cabinet,
            inherit_cabinet_permissions=True,
        )

    def test_inherited_view_permission(self):
        assign_perm("view_cabinet", self.viewer, self.cabinet)

        self.assertIn(self.document.pk, permitted_document_ids(self.viewer))
        self.assertNotIn(self.document.pk, permitted_document_ids(self.denied))

    def test_disabling_inheritance_uses_document_permissions(self):
        assign_perm("view_cabinet", self.viewer, self.cabinet)
        self.document.inherit_cabinet_permissions = False
        self.document.save(update_fields=("inherit_cabinet_permissions",))

        self.assertNotIn(self.document.pk, permitted_document_ids(self.viewer))
        assign_perm("view_document", self.viewer, self.document)
        self.assertIn(self.document.pk, permitted_document_ids(self.viewer))

    def test_inherited_change_permission(self):
        assign_perm("change_cabinet", self.viewer, self.cabinet)
        self.assertTrue(
            has_perms_owner_aware(self.viewer, "change_document", self.document),
        )
        self.assertFalse(
            has_perms_owner_aware(self.denied, "change_document", self.document),
        )

    def test_delete_permission_is_not_inherited(self):
        assign_perm("delete_cabinet", self.viewer, self.cabinet)
        self.assertFalse(
            has_perms_owner_aware(self.viewer, "delete_document", self.document),
        )

        assign_perm("delete_document", self.viewer, self.document)
        self.assertTrue(
            has_perms_owner_aware(self.viewer, "delete_document", self.document),
        )


class CabinetMatchingTest(TestCase):
    def test_rule_based_matching(self):
        cabinet = Cabinet.objects.create(
            name="Invoices",
            match="invoice",
            matching_algorithm=MatchingModel.MATCH_ANY,
        )
        document = Document(
            title="Invoice",
            content="Quarterly invoice",
            mime_type="application/pdf",
            checksum="cabinet-matching-test",
        )

        self.assertEqual(match_cabinets(document, None), [cabinet])


class CabinetWorkflowMutationTest(TestCase):
    def setUp(self):
        self.cabinet = Cabinet.objects.create(name="Legal")
        self.document = Document.objects.create(
            title="Contract",
            mime_type="application/pdf",
            checksum="cabinet-workflow-test",
        )

    def test_assignment_sets_cabinet_and_inheritance(self):
        action = WorkflowAction.objects.create(
            assign_cabinet=self.cabinet,
            assign_inherit_cabinet_permissions=False,
        )
        for annotation in (
            "has_assign_tags",
            "has_assign_view_users",
            "has_assign_view_groups",
            "has_assign_change_users",
            "has_assign_change_groups",
            "has_assign_custom_fields",
        ):
            setattr(action, annotation, False)

        apply_assignment_to_document(action, self.document, None)

        self.assertEqual(self.document.cabinet, self.cabinet)
        self.assertFalse(self.document.inherit_cabinet_permissions)

    def test_removal_clears_cabinet_and_inheritance(self):
        self.document.cabinet = self.cabinet
        self.document.inherit_cabinet_permissions = True
        action = WorkflowAction.objects.create(
            type=WorkflowAction.WorkflowActionType.REMOVAL,
            remove_all_cabinets=True,
        )
        for annotation in (
            "has_remove_view_users",
            "has_remove_view_groups",
            "has_remove_change_users",
            "has_remove_change_groups",
            "has_remove_custom_fields",
        ):
            setattr(action, annotation, False)

        apply_removal_to_document(action, self.document)

        self.assertIsNone(self.document.cabinet)
        self.assertFalse(self.document.inherit_cabinet_permissions)
