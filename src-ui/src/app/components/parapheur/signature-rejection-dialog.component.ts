import { Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'

@Component({
  selector: 'pngx-signature-rejection-dialog',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="modal-header">
      <h4 class="modal-title" i18n>Reject signature request</h4>
      <button type="button" class="btn-close" aria-label="Close" i18n-aria-label (click)="activeModal.dismiss()"></button>
    </div>
    <div class="modal-body">
      <label class="form-label" for="rejectionReason" i18n>Reason (optional)</label>
      <textarea id="rejectionReason" class="form-control" rows="4" maxlength="1000" [(ngModel)]="reason"></textarea>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline-secondary" type="button" (click)="activeModal.dismiss()" i18n>Cancel</button>
      <button class="btn btn-danger" type="button" (click)="activeModal.close(reason)" i18n>Reject request</button>
    </div>
  `,
})
export class SignatureRejectionDialogComponent {
  readonly activeModal = inject(NgbActiveModal)
  reason = ''
}
