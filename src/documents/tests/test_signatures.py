import base64

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document
from documents.models import SignatureProfile
from documents.models import SignatureRequest
from paperless.models import BuiltInGroup


class SignatureApiTest(APITestCase):
    def setUp(self):
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
        self.assertTrue(SignatureProfile.objects.filter(user=self.signer).exists())

        self.client.force_authenticate(self.requester)
        response = self.client.get("/api/signature_profile/file/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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

    def test_requester_cannot_request_own_signature(self):
        self.requester.groups.add(self.signers_group)
        self.client.force_authenticate(self.requester)

        signers = self.client.get("/api/signature_requests/signers/")
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
