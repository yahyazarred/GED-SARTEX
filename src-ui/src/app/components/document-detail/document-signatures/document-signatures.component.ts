import { CommonModule } from '@angular/common'
import { Component, DestroyRef, inject, Input, OnChanges, signal } from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { FormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import {
  SignatureRequest,
  SignatureRequestStatus,
  SignatureUser,
} from 'src/app/data/signature-request'
import {
  PermissionAction,
  PermissionsService,
  PermissionType,
} from 'src/app/services/permissions.service'
import { SignatureRequestService } from 'src/app/services/rest/signature-request.service'
import { SettingsService } from 'src/app/services/settings.service'
import { ToastService } from 'src/app/services/toast.service'
import { WebsocketStatusService } from 'src/app/services/websocket-status.service'

@Component({
  selector: 'pngx-document-signatures',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './document-signatures.component.html',
})
export class DocumentSignaturesComponent implements OnChanges {
  @Input({ required: true }) documentId!: number
  @Input({ required: true }) versionId!: number

  private readonly service = inject(SignatureRequestService)
  private readonly permissions = inject(PermissionsService)
  readonly settings = inject(SettingsService)
  private readonly toast = inject(ToastService)
  private readonly websocket = inject(WebsocketStatusService)
  private readonly destroyRef = inject(DestroyRef)
  private subscribed = false

  readonly requests = signal<SignatureRequest[]>([])
  readonly signers = signal<SignatureUser[]>([])
  readonly saving = signal(false)
  readonly SignatureRequestStatus = SignatureRequestStatus
  signerIds: number[] = []
  message = ''

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
          if (event.document_id === this.documentId) this.reload()
        })
    }
    this.reload()
    if (this.canRequest) {
      this.service.signers().subscribe((signers) => this.signers.set(signers))
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

  requestSignature(): void {
    if (!this.signerIds.length) return
    this.saving.set(true)
    this.service
      .requestMany({
        document: this.documentId,
        requested_version: this.versionId || this.documentId,
        signer_ids: this.signerIds,
        message: this.message,
      })
      .subscribe({
        next: () => {
          this.saving.set(false)
          this.signerIds = []
          this.message = ''
          this.toast.showInfo($localize`Signature requested.`)
          this.reload()
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
}
