import { ObjectWithId } from './object-with-id'

export enum CircuitStatus {
  Running = 'running',
  Waiting = 'waiting',
  Completed = 'completed',
  Rejected = 'rejected',
  Cancelled = 'cancelled',
  Failed = 'failed',
}

export enum CircuitTaskStatus {
  Pending = 'pending',
  Approved = 'approved',
  Rejected = 'rejected',
  Cancelled = 'cancelled',
}

export function workflowStatusName(status: string): string {
  const names: Record<string, string> = {
    running: $localize`:@@workflowStatusRunning:Running`,
    waiting: $localize`:@@workflowStatusWaiting:Waiting`,
    completed: $localize`:@@workflowStatusCompleted:Completed`,
    pending: $localize`:@@workflowStatusPending:Pending`,
    approved: $localize`:@@workflowStatusApproved:Approved`,
    rejected: $localize`:@@workflowStatusRejected:Rejected`,
    cancelled: $localize`:@@workflowStatusCancelled:Cancelled`,
    failed: $localize`:@@workflowStatusFailed:Failed`,
    not_started: $localize`:@@workflowStatusNotStarted:Not started`,
    succeeded: $localize`:@@workflowStatusSucceeded:Succeeded`,
    skipped: $localize`:@@workflowStatusSkipped:Skipped`,
  }
  return names[status] ?? status
}

export function workflowStepTypeName(type: WorkflowStepType): string {
  const names: Record<WorkflowStepType, string> = {
    action: $localize`:@@workflowStepTypeAction:Action`,
    approval: $localize`:@@workflowStepTypeApproval:Approval`,
    signature: $localize`:@@workflowStepTypeSignature:Signature request`,
    matching: $localize`:@@workflowStepTypeMatching:Automatic matching`,
  }
  return names[type]
}

export interface CircuitTask extends ObjectWithId {
  run: number
  step: number
  step_name: string
  document: number | null
  document_title?: string
  workflow_name: string
  assigned_to: number
  assigned_to_username: string
  status: CircuitTaskStatus
  comment: string
  decided_by?: number
  created: string
  completed?: string
  attempt: number
}

export interface CircuitRun extends ObjectWithId {
  workflow: number
  workflow_name: string
  document: number | null
  document_title?: string
  trigger_type?: number
  current_step?: number
  current_step_name?: string
  status: CircuitStatus
  started_by?: number
  started: string
  modified: string
  completed?: string
  failure_message: string
  tasks: CircuitTask[]
  steps: CircuitStepSummary[]
}

export type CircuitStepExecutionStatus =
  | 'not_started'
  | 'running'
  | 'waiting'
  | 'succeeded'
  | 'rejected'
  | 'failed'
  | 'skipped'
  | 'cancelled'

export interface CircuitStepExecution extends ObjectWithId {
  attempt: number
  status: Exclude<CircuitStepExecutionStatus, 'not_started'>
  started: string
  completed?: string
  actor?: number
  actor_username?: string
  detail: string
  error: string
}

export interface CircuitStepSummary extends ObjectWithId {
  name: string
  type: WorkflowStepType
  order: number
  display_number: string
  is_rejection_branch: boolean
  branch_parent_number?: string
  status: CircuitStepExecutionStatus
  executions: CircuitStepExecution[]
  approval_tasks: Array<{
    id: number; assigned_to: string; status: CircuitTaskStatus; comment: string
    decided_by?: string; created: string; completed?: string; attempt: number
  }>
  signature_requests: Array<{
    id: number; signer: string; requester: string; status: string
    rejection_reason: string; failure_message: string; created: string; completed?: string
  }>
}

export type WorkflowStepType = 'action' | 'approval' | 'signature' | 'matching'
export type ApprovalMode = 'one' | 'all'
export type TemporaryAccess = 'none' | 'view' | 'change'
export type MatchingMode = 'all' | 'tags' | 'cabinet'

export interface WorkflowStep extends ObjectWithId {
  workflow: number
  name: string
  order: number
  type: WorkflowStepType
  action?: number
  approval_user?: number
  approval_group?: number
  approval_mode: ApprovalMode
  temporary_access: TemporaryAccess
  signature_signer?: number
  matching_mode: MatchingMode
  rejection_step?: number
}
