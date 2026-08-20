import { Injectable } from '@angular/core'
import { Observable } from 'rxjs'
import { CircuitRun, CircuitTask, WorkflowStep } from 'src/app/data/circuit'
import { AbstractPaperlessService } from './abstract-paperless-service'

@Injectable({ providedIn: 'root' })
export class CircuitTaskService extends AbstractPaperlessService<CircuitTask> {
  constructor() {
    super()
    this.resourceName = 'circuit_tasks'
  }

  approve(task: CircuitTask, comment = ''): Observable<CircuitRun> {
    return this.http.post<CircuitRun>(
      this.getResourceUrl(task.id, 'approve'),
      { comment }
    )
  }

  reject(task: CircuitTask, comment: string): Observable<CircuitRun> {
    return this.http.post<CircuitRun>(
      this.getResourceUrl(task.id, 'reject'),
      { comment }
    )
  }
}

@Injectable({ providedIn: 'root' })
export class CircuitRunService extends AbstractPaperlessService<CircuitRun> {
  constructor() {
    super()
    this.resourceName = 'circuit_runs'
  }

  cancel(run: CircuitRun): Observable<CircuitRun> {
    return this.http.post<CircuitRun>(this.getResourceUrl(run.id, 'cancel'), {})
  }

  skip(run: CircuitRun, reason: string): Observable<CircuitRun> {
    return this.http.post<CircuitRun>(this.getResourceUrl(run.id, 'skip'), {
      reason,
    })
  }

  restartFromStep(
    run: CircuitRun,
    step: number,
    reason: string
  ): Observable<CircuitRun> {
    return this.http.post<CircuitRun>(
      this.getResourceUrl(run.id, 'restart-from-step'),
      { step, reason }
    )
  }
}

@Injectable({ providedIn: 'root' })
export class WorkflowStepService extends AbstractPaperlessService<WorkflowStep> {
  constructor() {
    super()
    this.resourceName = 'workflow_steps'
  }

}
