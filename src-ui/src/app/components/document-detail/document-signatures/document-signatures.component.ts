import { CommonModule } from '@angular/common'
import { Component, DestroyRef, inject, Input, OnChanges, signal } from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { FormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import { NgbModal } from '@ng-bootstrap/ng-bootstrap'
import {
  SignatureRequest,
  SignatureRequestStatus,
  SignatureUser,
  SignedDocument,
} from 'src/app/data/signature-request'
import {
  PermissionAction,
  PermissionsService,
  PermissionType,
} from 'src/app/services/permissions.service'
import {
  SignatureRequestService,
  SignedDocumentService,
} from 'src/app/services/rest/signature-request.service'
import { SettingsService } from 'src/app/services/settings.service'
import { ToastService } from 'src/app/services/toast.service'
import { WebsocketStatusService } from 'src/app/services/websocket-status.service'
import { ConfirmDialogComponent } from '../../common/confirm-dialog/confirm-dialog.component'
import { PermissionsDialogComponent } from '../../common/permissions-dialog/permissions-dialog.component'

@Component({
  selector: 'pngx-document-signatures',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './document-signatures.component.html',
  styleUrls: ['./document-signatures.component.scss'],
})
export class DocumentSignaturesComponent implements OnChanges {
  @Input({ required: true }) documentId!: number
  @Input({ required: true }) versionId!: number

  private readonly service = inject(SignatureRequestService)
  readonly signedDocumentsService = inject(SignedDocumentService)
  private readonly permissions = inject(PermissionsService)
  readonly settings = inject(SettingsService)
  private readonly toast = inject(ToastService)
  private readonly websocket = inject(WebsocketStatusService)
  private readonly destroyRef = inject(DestroyRef)
  private readonly modal = inject(NgbModal)
  private subscribed = false

  readonly requests = signal<SignatureRequest[]>([])
  readonly signers = signal<SignatureUser[]>([])
  readonly signedDocuments = signal<SignedDocument[]>([])
  readonly saving = signal(false)
  readonly SignatureRequestStatus = SignatureRequestStatus
  signerId: number | null = null
  message = ''
  activeView: 'requests' | 'signed' = 'requests'

  signerName(signer: SignatureUser): string {
    return [signer.first_name, signer.last_name].filter(Boolean).join(' ') || signer.username
  }

  sourceVersionName(signedDocument: SignedDocument): string {
    if (signedDocument.source_version_label) {
      return signedDocument.source_version_label
    }
    if (signedDocument.source_version_index != null) {
      return $localize`Version ${signedDocument.source_version_index}`
    }
    return $localize`Original document`
  }

  signerSelected(id: number): boolean {
    return this.signerId === id
  }

  selectSigner(id: number): void {
    this.signerId = this.signerSelected(id) ? null : id
  }

  get canRequest(): boolean {
    return this.permissions.currentUserCan(
      PermissionAction.Add,
      PermissionType.SignatureRequest
    )
  }

  ngOnChanges(): void {
    if (!this.documentId) return
    if (!this.subscribed) {
      this.subscribed = true
      this.websocket
        .onSignatureRequestUpdated()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe((event) => {
          if (event.document_id === this.documentId) {
            this.reload()
            this.reloadSignedDocuments()
          }
        })
    }
    this.reload()
    this.reloadSignedDocuments()
    if (this.canRequest) {
      this.service
        .signers(this.documentId)
        .subscribe((signers) => this.signers.set(signers))
    }
  }

  reload(): void {
    this.service
      .list(1, 100, '-created', false, { document: this.documentId })
      .subscribe({
        next: (result) => this.requests.set(result.results),
        error: (error) =>
          this.toast.showError($localize`Error retrieving signature requests`, error),
      })
  }

  reloadSignedDocuments(): void {
    this.signedDocumentsService
      .list(1, 100, 'created', true, { document: this.documentId })
      .subscribe({
        next: (result) => this.signedDocuments.set(result.results),
        error: (error) =>
          this.toast.showError($localize`Error retrieving signed copies`, error),
      })
  }

  requestSignature(): void {
    if (!this.signerId) return
    this.saving.set(true)
    this.service
      .requestSignature({
        document: this.documentId,
        requested_version: this.versionId || this.documentId,
        signer_id: this.signerId,
        message: this.message,
      })
      .subscribe({
        next: () => {
          this.saving.set(false)
          this.signerId = null
          this.message = ''
          this.toast.showInfo($localize`Signature requested.`)
          this.reload()
          this.reloadSignedDocuments()
        },
        error: (error) => {
          this.saving.set(false)
          this.toast.showError($localize`Unable to request signature`, error)
        },
      })
  }

  canCancel(request: SignatureRequest): boolean {
    return (
      request.status === SignatureRequestStatus.Pending &&
      (request.requester?.id === this.settings.currentUser()?.id ||
        this.permissions.currentUserCan(
          PermissionAction.Change,
          PermissionType.SignatureRequest
        ))
    )
  }

  cancel(request: SignatureRequest): void {
    this.service.cancel(request).subscribe({
      next: () => this.reload(),
      error: (error) => this.toast.showError($localize`Unable to cancel request`, error),
    })
  }

  canManageSignedDocument(signedDocument: SignedDocument): boolean {
    return this.permissions.currentUserHasObjectPermissions(
      PermissionAction.Change,
      signedDocument
    )
  }

  editSignedDocumentPermissions(signedDocument: SignedDocument): void {
    const modal = this.modal.open(PermissionsDialogComponent, {
      backdrop: 'static',
    })
    const dialog = modal.componentInstance as PermissionsDialogComponent
    if (signedDocument.owner !== this.settings.currentUser()?.id) {
      dialog.protectedUserId = this.settings.currentUser()?.id
    }
    dialog.object = signedDocument
    dialog.note.set(
      $localize`Access to the source document does not grant access to this signed copy.`
    )
    dialog.confirmClicked.subscribe(({ permissions }) => {
      dialog.buttonsEnabled.set(false)
      this.signedDocumentsService
        .patch({
          ...signedDocument,
          set_permissions: permissions.set_permissions,
        })
        .subscribe({
          next: () => {
            modal.close()
            this.reloadSignedDocuments()
          },
          error: (error) => {
            dialog.buttonsEnabled.set(true)
            this.toast.showError($localize`Unable to update permissions`, error)
          },
        })
    })
  }

  deleteSignedDocument(signedDocument: SignedDocument): void {
    const modal = this.modal.open(ConfirmDialogComponent, {
      backdrop: 'static',
    })
    modal.componentInstance.title = $localize`Delete signed copy`
    modal.componentInstance.messageBold = $localize`This permanently deletes the signed PDF.`
    modal.componentInstance.message = $localize`The signer may then be requested to sign this version again.`
    modal.componentInstance.btnClass = 'btn-danger'
    modal.componentInstance.btnCaption = $localize`Delete`
    modal.componentInstance.confirmClicked.subscribe(() => {
      modal.componentInstance.buttonsEnabled = false
      this.signedDocumentsService.delete(signedDocument).subscribe({
        next: () => {
          modal.close()
          this.reload()
          this.reloadSignedDocuments()
        },
        error: (error) => {
          modal.componentInstance.buttonsEnabled = true
          this.toast.showError($localize`Unable to delete signed copy`, error)
        },
      })
    })
  }
}
