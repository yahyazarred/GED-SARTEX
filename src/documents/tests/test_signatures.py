import base64
from io import BytesIO
from unittest import mock

from auditlog.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from guardian.shortcuts import assign_perm
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from documents import bulk_edit
from documents.models import Document
from documents.models import SignatureProfile
from documents.models import SignatureRequest
from documents.models import SignedDocument
from documents.signatures import normalize_signature
from documents.tests.utils import DirectoriesMixin
from paperless.models import BuiltInGroup


class SignatureApiTest(DirectoriesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.requester = User.objects.create_user("requester")
        self.signer = User.objects.create_user("signer")
        self.other_signer = User.objects.create_user("other-signer")
        self.signers_group = Group.objects.create(name="Signers test")
        BuiltInGroup.objects.update_or_create(
            key=BuiltInGroup.Key.SIGNERS,
            defaults={"group": self.signers_group},
        )
        self.signer.groups.add(self.signers_group)
        self.other_signer.groups.add(self.signers_group)
        view_document = Permission.objects.get(codename="view_document")
        self.signer.user_permissions.add(view_document)
        self.other_signer.user_permissions.add(view_document)
        self.requester.user_permissions.add(
            Permission.objects.get(codename="add_signaturerequest"),
        )
        self.document = Document.objects.create(
            title="Contract",
            checksum="signature-root",
            mime_type="application/pdf",
            owner=self.requester,
        )

    def test_only_signer_can_upload_and_retrieve_raw_signature(self):
        signature = SimpleUploadedFile(
            "signature.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            ),
            content_type="image/png",
        )
        self.client.force_authenticate(self.signer)
        response = self.client.post(
            "/api/signature_profile/",
            {"signature": signature},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = SignatureProfile.objects.get(user=self.signer)
        self.assertTrue(profile.processed_file)

        self.client.force_authenticate(self.requester)
        response = self.client.get("/api/signature_profile/file/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_signature_background_is_made_transparent(self):
        source = Image.new("RGB", (40, 30), "white")
        for x in range(10, 30):
            source.putpixel((x, 15), (0, 0, 0))
        upload = BytesIO()
        source.save(upload, format="PNG")

        normalized = normalize_signature(upload.getvalue(), "image/png")

        with Image.open(BytesIO(normalized)) as result:
            self.assertEqual(result.mode, "RGBA")
            self.assertLess(result.width, source.width)
            self.assertEqual(result.getchannel("A").getextrema(), (0, 255))

    def test_request_is_visible_only_to_participants(self):
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
        )
        outsider = User.objects.create_user("outsider")
        self.client.force_authenticate(outsider)

        response = self.client.get("/api/signature_requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(signature_request.id, [item["id"] for item in response.data["results"]])

    def test_parapheur_only_returns_requests_assigned_to_current_signer(self):
        assigned = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
        )
        SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.other_signer,
        )
        self.signer.user_permissions.add(
            Permission.objects.get(codename="view_signaturerequest"),
            Permission.objects.get(codename="view_document"),
        )
        self.client.force_authenticate(self.signer)

        response = self.client.get(
            "/api/signature_requests/?assigned_to_me=true",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [assigned.id],
        )

    def test_duplicate_pending_request_is_rejected(self):
        payload = {
            "document": self.document.id,
            "requested_version": self.document.id,
            "signer_id": self.signer.id,
        }
        self.client.force_authenticate(self.requester)

        first = self.client.post("/api/signature_requests/", payload, format="json")
        second = self.client.post("/api/signature_requests/", payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SignatureRequest.objects.count(), 1)

    def _create_profile(self):
        return SignatureProfile.objects.create(
            user=self.signer,
            signature_file=SimpleUploadedFile("signature.png", b"signature"),
            processed_file=SimpleUploadedFile("signature-transparent.png", b"processed"),
            original_filename="signature.png",
            mime_type="image/png",
            checksum="signature-checksum",
        )

    @mock.patch("documents.views.create_signed_document", return_value=b"%PDF-1.4 signed")
    def test_signing_creates_private_signed_copy_not_document_version(self, create_signed):
        self._create_profile()
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
        )
        document_count = Document.global_objects.count()
        self.client.force_authenticate(self.signer)

        response = self.client.post(
            f"/api/signature_requests/{signature_request.id}/sign/",
            {"page": 1, "x": 0.1, "y": 0.2, "width": 0.2, "height": 0.1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Document.global_objects.count(), document_count)
        signed_document = SignedDocument.objects.get()
        self.assertEqual(response.data["signed_document"], signed_document.id)
        self.assertEqual(signed_document.source_version, self.document)
        self.assertEqual(signed_document.signer, self.signer)
        create_signed.assert_called_once()

    @mock.patch("documents.views.create_signed_document", return_value=b"%PDF-1.4 signed")
    def test_signed_copy_blocks_same_signer_until_copy_is_deleted(self, _create_signed):
        self._create_profile()
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
        )
        self.client.force_authenticate(self.signer)
        self.client.post(
            f"/api/signature_requests/{signature_request.id}/sign/",
            {"page": 1, "x": 0.1, "y": 0.2, "width": 0.2, "height": 0.1},
            format="json",
        )

        self.client.force_authenticate(self.requester)
        duplicate = self.client.post(
            "/api/signature_requests/",
            {
                "document": self.document.id,
                "requested_version": self.document.id,
                "signer_id": self.signer.id,
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

        signed_document = SignedDocument.objects.get()
        deleted = self.client.delete(f"/api/signed_documents/{signed_document.id}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        history = self.client.get(f"/api/signature_requests/{signature_request.id}/")
        self.assertTrue(history.data["signed_copy_deleted"])
        self.assertIsNone(history.data["signed_document"])
        retry = self.client.post(
            "/api/signature_requests/",
            {
                "document": self.document.id,
                "requested_version": self.document.id,
                "signer_id": self.signer.id,
            },
            format="json",
        )
        self.assertEqual(retry.status_code, status.HTTP_201_CREATED)

    def test_document_access_does_not_grant_signed_copy_access(self):
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
            status=SignatureRequest.Status.SIGNED,
        )
        signed_document = SignedDocument.objects.create(
            signature_request=signature_request,
            document=self.document,
            source_version=self.document,
            signer=self.signer,
            requester=self.requester,
            owner=self.requester,
            signed_file=SimpleUploadedFile("signed.pdf", b"%PDF-1.4 signed"),
            file_checksum="file-checksum",
            signature_checksum="signature-checksum",
            page=1,
            x=0.1,
            y=0.2,
            width=0.2,
            height=0.1,
        )
        outsider = User.objects.create_user("signed-copy-outsider")
        assign_perm("documents.view_document", outsider, self.document)
        outsider.user_permissions.add(
            Permission.objects.get(codename="view_signaturerequest"),
        )
        self.client.force_authenticate(outsider)

        hidden = self.client.get("/api/signed_documents/")
        self.assertNotIn(
            signed_document.id,
            [item["id"] for item in hidden.data["results"]],
        )
        self.assertEqual(
            self.client.get(f"/api/signed_documents/{signed_document.id}/file/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        request_history = self.client.get(
            f"/api/signature_requests/?document={self.document.id}",
        )
        self.assertIsNone(request_history.data["results"][0]["signed_document"])

        assign_perm("documents.view_signeddocument", outsider, signed_document)
        visible = self.client.get(
            f"/api/signed_documents/{signed_document.id}/file/",
        )
        self.assertEqual(visible.status_code, status.HTTP_200_OK)
        visible.close()
        request_history = self.client.get(
            f"/api/signature_requests/?document={self.document.id}",
        )
        self.assertEqual(
            request_history.data["results"][0]["signed_document"],
            signed_document.id,
        )

    def test_deleting_document_deletes_its_signed_copies(self):
        source_version = Document.objects.create(
            title="Contract revision",
            checksum="signature-version",
            mime_type="application/pdf",
            owner=self.requester,
            root_document=self.document,
            version_index=1,
        )
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=source_version,
            requester=self.requester,
            signer=self.signer,
            status=SignatureRequest.Status.SIGNED,
        )
        signed_document = SignedDocument.objects.create(
            signature_request=signature_request,
            document=self.document,
            source_version=source_version,
            signer=self.signer,
            requester=self.requester,
            owner=self.requester,
            signed_file=SimpleUploadedFile("signed.pdf", b"%PDF-1.4 signed"),
            file_checksum="file-checksum",
            signature_checksum="signature-checksum",
            page=1,
            x=0.1,
            y=0.2,
            width=0.2,
            height=0.1,
        )
        signed_file_name = signed_document.signed_file.name
        storage = signed_document.signed_file.storage
        self.requester.user_permissions.add(
            Permission.objects.get(codename="delete_document"),
        )
        self.client.force_authenticate(self.requester)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(f"/api/documents/{self.document.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SignedDocument.objects.filter(pk=signed_document.pk).exists())
        self.assertFalse(storage.exists(signed_file_name))
        trash = self.client.get("/api/trash/")
        self.assertEqual(
            [item["id"] for item in trash.data["results"]],
            [self.document.id],
        )

    def test_bulk_deleting_document_deletes_its_signed_copies(self):
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
            status=SignatureRequest.Status.SIGNED,
        )
        signed_document = SignedDocument.objects.create(
            signature_request=signature_request,
            document=self.document,
            source_version=self.document,
            signer=self.signer,
            requester=self.requester,
            owner=self.requester,
            signed_file=SimpleUploadedFile("signed.pdf", b"%PDF-1.4 signed"),
            file_checksum="file-checksum",
            signature_checksum="signature-checksum",
            page=1,
            x=0.1,
            y=0.2,
            width=0.2,
            height=0.1,
        )
        signed_file_name = signed_document.signed_file.name
        storage = signed_document.signed_file.storage

        with self.captureOnCommitCallbacks(execute=True):
            bulk_edit.delete([self.document.id])

        self.assertFalse(SignedDocument.objects.filter(pk=signed_document.pk).exists())
        self.assertFalse(SignatureRequest.objects.filter(pk=signature_request.pk).exists())
        self.assertFalse(storage.exists(signed_file_name))

    def test_change_permission_allows_deleting_signed_copy(self):
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
            status=SignatureRequest.Status.SIGNED,
        )
        signed_document = SignedDocument.objects.create(
            signature_request=signature_request,
            document=self.document,
            source_version=self.document,
            signer=self.signer,
            requester=self.requester,
            owner=self.requester,
            signed_file=SimpleUploadedFile("signed.pdf", b"%PDF-1.4 signed"),
            file_checksum="file-checksum",
            signature_checksum="signature-checksum",
            page=1,
            x=0.1,
            y=0.2,
            width=0.2,
            height=0.1,
        )
        manager = User.objects.create_user("signed-copy-manager")
        assign_perm("documents.view_signeddocument", manager, signed_document)
        assign_perm("documents.change_signeddocument", manager, signed_document)
        self.client.force_authenticate(manager)

        updated = self.client.patch(
            f"/api/signed_documents/{signed_document.id}/",
            {
                "set_permissions": {
                    "view": {"users": [], "groups": []},
                    "change": {"users": [], "groups": []},
                },
            },
            format="json",
        )
        response = self.client.delete(f"/api/signed_documents/{signed_document.id}/")

        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertTrue(manager.has_perm("documents.view_signeddocument", signed_document))
        self.assertTrue(manager.has_perm("documents.change_signeddocument", signed_document))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SignedDocument.objects.filter(pk=signed_document.pk).exists())

    def test_requester_cannot_request_own_signature(self):
        self.requester.groups.add(self.signers_group)
        self.client.force_authenticate(self.requester)

        signers = self.client.get(
            f"/api/signature_requests/signers/?document={self.document.id}",
        )
        response = self.client.post(
            "/api/signature_requests/batch/",
            {
                "document": self.document.id,
                "requested_version": self.document.id,
                "signer_ids": [self.requester.id],
            },
            format="json",
        )

        self.assertEqual(signers.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.requester.id, [user["id"] for user in signers.data])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_batch_endpoint_rejects_multiple_signers(self):
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            "/api/signature_requests/batch/",
            {
                "document": self.document.id,
                "requested_version": self.document.id,
                "signer_ids": [self.signer.id, self.other_signer.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signer_without_document_access_is_not_available(self):
        restricted_signer = User.objects.create_user("restricted-signer")
        restricted_signer.groups.add(self.signers_group)
        self.client.force_authenticate(self.requester)

        signers = self.client.get(
            f"/api/signature_requests/signers/?document={self.document.id}",
        )
        response = self.client.post(
            "/api/signature_requests/",
            {
                "document": self.document.id,
                "requested_version": self.document.id,
                "signer_id": restricted_signer.id,
            },
            format="json",
        )

        self.assertNotIn(restricted_signer.id, [user["id"] for user in signers.data])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_signer_cannot_reject_request(self):
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
        )
        self.client.force_authenticate(self.other_signer)

        response = self.client.post(
            f"/api/signature_requests/{signature_request.id}/reject/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.Status.PENDING)

    def test_requester_can_cancel_pending_request(self):
        signature_request = SignatureRequest.objects.create(
            document=self.document,
            requested_version=self.document,
            requester=self.requester,
            signer=self.signer,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            f"/api/signature_requests/{signature_request.id}/cancel/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.Status.CANCELLED)

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_request_and_cancellation_are_added_to_document_history(self):
        self.client.force_authenticate(self.requester)
        created = self.client.post(
            "/api/signature_requests/",
            {
                "document": self.document.id,
                "requested_version": self.document.id,
                "signer_id": self.signer.id,
            },
            format="json",
        )
        self.client.post(
            f"/api/signature_requests/{created.data['id']}/cancel/",
            {},
            format="json",
        )

        events = [
            entry.changes
            for entry in LogEntry.objects.get_for_object(self.document)
        ]
        self.assertTrue(any("Signature Requested" in event for event in events))
        self.assertTrue(
            any("Signature Request Cancelled" in event for event in events),
        )


class BuiltInGroupApiTest(APITestCase):
    def test_builtin_group_cannot_be_deleted(self):
        admin = User.objects.create_superuser("admin")
        group = Group.objects.create(name="Protected signers")
        BuiltInGroup.objects.update_or_create(
            key=BuiltInGroup.Key.SIGNERS,
            defaults={"group": group},
        )
        self.client.force_authenticate(admin)

        response = self.client.delete(f"/api/groups/{group.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Group.objects.filter(pk=group.pk).exists())
