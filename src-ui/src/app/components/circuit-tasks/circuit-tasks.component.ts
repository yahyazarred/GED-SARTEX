import { CommonModule } from '@angular/common'
import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { FormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { CircuitTask, CircuitTaskStatus } from 'src/app/data/circuit'
import { CircuitTaskService } from 'src/app/services/rest/circuit.service'
import { ToastService } from 'src/app/services/toast.service'
import { WebsocketStatusService } from 'src/app/services/websocket-status.service'
import { PageHeaderComponent } from '../common/page-header/page-header.component'

@Component({
  selector: 'pngx-circuit-tasks',
  standalone: true,
  templateUrl: './circuit-tasks.component.html',
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    NgxBootstrapIconsModule,
    PageHeaderComponent,
  ],
})
export class CircuitTasksComponent implements OnInit {
  private readonly service = inject(CircuitTaskService)
  private readonly toast = inject(ToastService)
  private readonly websocket = inject(WebsocketStatusService)
  private readonly destroyRef = inject(DestroyRef)
  readonly tasks = signal<CircuitTask[]>([])
  readonly loading = signal(false)
  readonly deciding = signal<number>(null)
  readonly CircuitTaskStatus = CircuitTaskStatus
  status: CircuitTaskStatus | null = CircuitTaskStatus.Pending
  rejectionTask: number | null = null
  rejectionReason = ''

  ngOnInit(): void {
    this.reload()
    this.websocket
      .onCircuitTaskUpdated()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.reload())
  }

  reload(): void {
    this.loading.set(true)
    this.service.clearCache()
    this.service
      .list(1, 100, '-created', false, { status: this.status })
      .subscribe({
        next: (result) => this.tasks.set(result.results),
        error: (error) => this.toast.showError($localize`Unable to load approval tasks.`, error),
        complete: () => this.loading.set(false),
      })
  }

  approve(task: CircuitTask): void {
    this.deciding.set(task.id)
    this.service.approve(task).subscribe({
      next: () => {
        this.toast.showInfo($localize`Approval recorded.`)
        this.reload()
      },
      error: (error) => this.toast.showError($localize`Unable to approve this step.`, error),
      complete: () => this.deciding.set(null),
    })
  }

  reject(task: CircuitTask): void {
    const reason = this.rejectionReason.trim()
    if (!reason) return
    this.deciding.set(task.id)
    this.service.reject(task, reason).subscribe({
      next: () => {
        this.rejectionTask = null
        this.rejectionReason = ''
        this.toast.showInfo($localize`Rejection recorded.`)
        this.reload()
      },
      error: (error) => this.toast.showError($localize`Unable to reject this step.`, error),
      complete: () => this.deciding.set(null),
    })
  }
}
