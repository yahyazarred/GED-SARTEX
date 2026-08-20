import { CommonModule } from '@angular/common'
import { Component, Input, OnInit, inject, signal } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'
import { CircuitRun, WorkflowStep } from 'src/app/data/circuit'
import {
  CircuitRunService,
  WorkflowStepService,
} from 'src/app/services/rest/circuit.service'
import { ToastService } from 'src/app/services/toast.service'

export type CircuitManagementAction = 'skip' | 'restart'

@Component({
  selector: 'pngx-circuit-manage-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-header">
      <h4 class="modal-title">{{ title }}</h4>
      <button class="btn-close" type="button" (click)="modal.dismiss()"></button>
    </div>
    <div class="modal-body">
      <p><strong>{{ run.workflow_name }}</strong> · {{ run.document_title }}</p>
      @if (action === 'restart') {
        <label class="form-label" for="restart-step" i18n>Restart from step</label>
        <select id="restart-step" class="form-select mb-3" [(ngModel)]="step">
          @for (candidate of steps(); track candidate.id) {
            <option [ngValue]="candidate.id">
              {{ candidate.order + 1 }}. {{ candidate.name }}
            </option>
          }
        </select>
      }
      <label class="form-label" for="management-reason" i18n>Reason</label>
      <textarea id="management-reason" class="form-control" rows="3" maxlength="2000" [(ngModel)]="reason"></textarea>
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
        (click)="submit()"
        [disabled]="!valid || saving"
        i18n
      >Confirm</button>
    </div>
  `,
})
export class CircuitManageDialogComponent implements OnInit {
  @Input() run: CircuitRun
  @Input() action: CircuitManagementAction
  readonly modal = inject(NgbActiveModal)
  private readonly runs = inject(CircuitRunService)
  private readonly workflowSteps = inject(WorkflowStepService)
  private readonly toast = inject(ToastService)
  readonly steps = signal<WorkflowStep[]>([])
  step: number | null = null
  reason = ''
  saving = false

  get title(): string {
    return {
      skip: $localize`Skip current step`,
      restart: $localize`Restart workflow`,
    }[this.action]
  }

  get valid(): boolean {
    if (this.action === 'restart') return !!this.step && !!this.reason.trim()
    return !!this.reason.trim()
  }

  ngOnInit(): void {
    if (this.action === 'restart') {
      this.workflowSteps
        .list(1, 1000, 'order', false, { workflow: this.run.workflow })
        .subscribe((result) => {
          this.steps.set(result.results)
          this.step = result.results[0]?.id
        })
    }
  }

  submit(): void {
    if (!this.valid) return
    this.saving = true
    const operation = this.action === 'skip'
      ? this.runs.skip(this.run, this.reason.trim())
      : this.runs.restartFromStep(this.run, this.step!, this.reason.trim())
    operation.subscribe({
      next: (run) => this.modal.close(run),
      error: (error) => this.toast.showError($localize`Unable to manage this workflow.`, error),
      complete: () => (this.saving = false),
    })
  }
}
