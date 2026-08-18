import { CommonModule } from '@angular/common'
import { Component, inject, OnInit, signal } from '@angular/core'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'
import { SignatureProfile } from 'src/app/data/signature-request'
import { SignatureProfileService } from 'src/app/services/rest/signature-request.service'
import { ToastService } from 'src/app/services/toast.service'

@Component({
  selector: 'pngx-signature-profile-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal-header">
      <h4 class="modal-title" i18n>My signature</h4>
      <button type="button" class="btn-close" aria-label="Close" i18n-aria-label (click)="activeModal.dismiss()"></button>
    </div>
    <div class="modal-body">
      <p class="text-muted" i18n>Your signature is private. Only you can retrieve or replace the source file.</p>
      @if (profile()?.configured) {
        <div class="border rounded p-3 text-center mb-3 signature-preview">
          <img [src]="service.previewUrl()" alt="Current signature" i18n-alt />
        </div>
        <div class="small text-muted mb-3">{{ profile().original_filename }}</div>
      }
      <label class="form-label" for="signatureFile" i18n>{{ profile()?.configured ? 'Replace signature' : 'Upload signature' }}</label>
      <input id="signatureFile" class="form-control" type="file" accept="image/png,image/jpeg,application/pdf" (change)="selected($event)" />
      <div class="form-text" i18n>PNG, JPEG or a one-page PDF, up to 10 MB.</div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline-secondary" type="button" (click)="activeModal.close()" i18n>Close</button>
      <button class="btn btn-primary" type="button" [disabled]="!file || saving()" (click)="save()">
        @if (saving()) { <span class="spinner-border spinner-border-sm me-1"></span> }
        <ng-container i18n>Save signature</ng-container>
      </button>
    </div>
  `,
  styles: [
    `.signature-preview img { max-width: 100%; max-height: 240px; object-fit: contain; }`,
  ],
})
export class SignatureProfileDialogComponent implements OnInit {
  readonly activeModal = inject(NgbActiveModal)
  readonly service = inject(SignatureProfileService)
  private readonly toast = inject(ToastService)
  readonly profile = signal<SignatureProfile>(null)
  readonly saving = signal(false)
  file?: File

  ngOnInit(): void {
    this.service.getProfile().subscribe((profile) => this.profile.set(profile))
  }

  selected(event: Event): void {
    this.file = (event.target as HTMLInputElement).files?.[0]
  }

  save(): void {
    if (!this.file) return
    this.saving.set(true)
    this.service.upload(this.file).subscribe({
      next: (profile) => {
        this.profile.set(profile)
        this.saving.set(false)
        this.file = undefined
        this.toast.showInfo($localize`Signature saved.`)
      },
      error: (error) => {
        this.saving.set(false)
        this.toast.showError($localize`Unable to save signature`, error)
      },
    })
  }
}
