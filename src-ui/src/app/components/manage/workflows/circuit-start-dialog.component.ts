import { Component, Input, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'
import { Workflow } from 'src/app/data/workflow'
import { WorkflowService } from 'src/app/services/rest/workflow.service'
import { ToastService } from 'src/app/services/toast.service'

@Component({
  selector: 'pngx-circuit-start-dialog',
  standalone: true,
  template: `
    <div class="modal-header">
      <h4 class="modal-title" i18n>Start workflow</h4>
      <button class="btn-close" type="button" (click)="modal.dismiss()"></button>
    </div>
    <div class="modal-body">
      <p i18n>Start “{{ workflow.name }}” for a document.</p>
      <label class="form-label" for="circuit-document-id" i18n>Document ID</label>
      <input
        id="circuit-document-id"
        class="form-control"
        type="number"
        min="1"
        [(ngModel)]="document"
      />
    </div>
    <div class="modal-footer">
      <button
        class="btn btn-outline-secondary"
        type="button"
        (click)="modal.dismiss()"
        i18n
      >Cancel</button>
      <button
        class="btn btn-primary"
        type="button"
        (click)="start()"
        [disabled]="!document || saving"
        i18n
      >Start workflow</button>
    </div>
  `,
  imports: [FormsModule],
})
export class CircuitStartDialogComponent {
  @Input() workflow: Workflow
  readonly modal = inject(NgbActiveModal)
  private readonly workflows = inject(WorkflowService)
  private readonly toast = inject(ToastService)
  document: number | null = null
  saving = false

  start(): void {
    if (!this.document) return
    const document = this.document
    this.saving = true
    this.workflows.start(this.workflow, document).subscribe({
      next: (run) => {
        this.toast.showInfo($localize`Workflow started for “${run.document_title}”.`)
        this.modal.close(run)
      },
      error: (error) => this.toast.showError($localize`Unable to start this workflow.`, error),
      complete: () => (this.saving = false),
    })
  }
}
