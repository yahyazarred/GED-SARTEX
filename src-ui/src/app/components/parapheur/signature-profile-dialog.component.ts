import { CommonModule } from '@angular/common'
import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core'
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser'
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
      @if (selectedPreviewUrl()) {
        <div class="border rounded p-3 text-center mb-3 signature-preview">
          @if (selectedFileIsPdf()) {
            <object [data]="selectedPdfPreviewUrl()" type="application/pdf" aria-label="Selected signature preview" i18n-aria-label></object>
          } @else {
            <img [src]="selectedPreviewUrl()" alt="Selected signature" i18n-alt />
          }
        </div>
        <div class="small text-muted mb-3">{{ file?.name }}</div>
      } @else if (profile()?.configured) {
        <div class="border rounded p-3 text-center mb-3 signature-preview checkerboard">
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
    `.signature-preview img, .signature-preview object { width: 100%; max-width: 100%; height: 240px; object-fit: contain; }`,
    `.checkerboard { background-color: #fff; background-image: linear-gradient(45deg, #eee 25%, transparent 25%), linear-gradient(-45deg, #eee 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #eee 75%), linear-gradient(-45deg, transparent 75%, #eee 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0; }`,
  ],
})
export class SignatureProfileDialogComponent implements OnInit, OnDestroy {
  readonly activeModal = inject(NgbActiveModal)
  readonly service = inject(SignatureProfileService)
  private readonly toast = inject(ToastService)
  private readonly sanitizer = inject(DomSanitizer)
  readonly profile = signal<SignatureProfile>(null)
  readonly saving = signal(false)
  readonly selectedPreviewUrl = signal<string>('')
  readonly selectedPdfPreviewUrl = signal<SafeResourceUrl>(null)
  readonly selectedFileIsPdf = signal(false)
  file?: File

  ngOnInit(): void {
    this.service.getProfile().subscribe((profile) => this.profile.set(profile))
  }

  selected(event: Event): void {
    this.clearSelectedPreview()
    this.file = (event.target as HTMLInputElement).files?.[0]
    if (!this.file) return
    const objectUrl = URL.createObjectURL(this.file)
    this.selectedPreviewUrl.set(objectUrl)
    this.selectedFileIsPdf.set(this.file.type === 'application/pdf')
    if (this.selectedFileIsPdf()) {
      this.selectedPdfPreviewUrl.set(
        this.sanitizer.bypassSecurityTrustResourceUrl(objectUrl)
      )
    }
  }

  save(): void {
    if (!this.file) return
    this.saving.set(true)
    this.service.upload(this.file).subscribe({
      next: (profile) => {
        this.profile.set(profile)
        this.saving.set(false)
        this.file = undefined
        this.clearSelectedPreview()
        this.toast.showInfo($localize`Signature saved.`)
      },
      error: (error) => {
        this.saving.set(false)
        this.toast.showError($localize`Unable to save signature`, error)
      },
    })
  }

  ngOnDestroy(): void {
    this.clearSelectedPreview()
  }

  private clearSelectedPreview(): void {
    const objectUrl = this.selectedPreviewUrl()
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    this.selectedPreviewUrl.set('')
    this.selectedPdfPreviewUrl.set(null)
    this.selectedFileIsPdf.set(false)
  }
}
