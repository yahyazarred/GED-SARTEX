import { CommonModule } from '@angular/common'
import { Component, OnInit, inject, signal } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import { NgbModal } from '@ng-bootstrap/ng-bootstrap'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { IfPermissionsDirective } from 'src/app/directives/if-permissions.directive'
import {
  CircuitRun,
  CircuitStepSummary,
  CircuitStatus,
  workflowStatusName,
  workflowStepTypeName,
} from 'src/app/data/circuit'
import { CircuitRunService } from 'src/app/services/rest/circuit.service'
import { ToastService } from 'src/app/services/toast.service'
import {
  PermissionAction,
  PermissionType,
  PermissionsService,
} from 'src/app/services/permissions.service'
import { PageHeaderComponent } from '../../common/page-header/page-header.component'
import {
  CircuitManageDialogComponent,
  CircuitManagementAction,
} from './circuit-manage-dialog.component'

@Component({
  selector: 'pngx-circuit-runs',
  standalone: true,
  templateUrl: './circuit-runs.component.html',
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    NgxBootstrapIconsModule,
    IfPermissionsDirective,
    PageHeaderComponent,
  ],
})
export class CircuitRunsComponent implements OnInit {
  private readonly service = inject(CircuitRunService)
  private readonly toast = inject(ToastService)
  private readonly permissions = inject(PermissionsService)
  private readonly modal = inject(NgbModal)
  readonly runs = signal<CircuitRun[]>([])
  readonly loading = signal(false)
  readonly CircuitStatus = CircuitStatus
  readonly workflowStatusName = workflowStatusName
  readonly workflowStepTypeName = workflowStepTypeName
  readonly PermissionAction = PermissionAction
  readonly PermissionType = PermissionType
  readonly expandedRuns = signal<Set<number>>(new Set())
  readonly selectedSteps = signal<Record<number, number>>({})
  status: CircuitStatus | null = null

  get canManage(): boolean {
    return this.permissions.currentUserCan(
      PermissionAction.Change,
      PermissionType.WorkflowActivity
    )
  }

  ngOnInit(): void {
    this.reload()
  }

  reload(): void {
    this.loading.set(true)
    this.service.clearCache()
    this.service
      .list(1, 100, 'started', true, { status: this.status })
      .subscribe({
        next: (result) => this.runs.set(result.results),
        error: (error) =>
          this.toast.showError($localize`Unable to load workflow activity.`, error),
        complete: () => this.loading.set(false),
      })
  }

  cancel(run: CircuitRun): void {
    this.service.cancel(run).subscribe({
      next: () => this.reload(),
      error: (error) =>
        this.toast.showError($localize`Unable to cancel this workflow.`, error),
    })
  }

  toggleRun(run: CircuitRun): void {
    const expanded = new Set(this.expandedRuns())
    expanded.has(run.id) ? expanded.delete(run.id) : expanded.add(run.id)
    this.expandedRuns.set(expanded)
  }

  selectStep(run: CircuitRun, step: CircuitStepSummary): void {
    this.selectedSteps.update((selected) => ({ ...selected, [run.id]: step.id }))
  }

  selectedStep(run: CircuitRun): CircuitStepSummary | undefined {
    return run.steps.find((step) => step.id === this.selectedSteps()[run.id])
  }

  mainSteps(run: CircuitRun): CircuitStepSummary[] {
    return run.steps.filter((step) => !step.is_rejection_branch)
  }

  branchParents(run: CircuitRun): string[] {
    return [
      ...new Set(
        run.steps
          .filter((step) => step.is_rejection_branch)
          .map((step) => step.branch_parent_number!)
      ),
    ]
  }

  branchSteps(run: CircuitRun, parent: string): CircuitStepSummary[] {
    return run.steps.filter(
      (step) => step.is_rejection_branch && step.branch_parent_number === parent
    )
  }

  manage(run: CircuitRun, action: CircuitManagementAction): void {
    const modal = this.modal.open(CircuitManageDialogComponent, {
      backdrop: 'static',
    })
    modal.componentInstance.run = run
    modal.componentInstance.action = action
    modal.closed.subscribe(() => this.reload())
  }
}
