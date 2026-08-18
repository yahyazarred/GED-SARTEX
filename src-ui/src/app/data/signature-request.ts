import { ObjectWithId } from './object-with-id'

export interface SignatureUser {
  id: number
  username: string
  first_name?: string
  last_name?: string
}

export enum SignatureRequestStatus {
  Pending = 'pending',
  Processing = 'processing',
  Signed = 'signed',
  Rejected = 'rejected',
  Cancelled = 'cancelled',
  Failed = 'failed',
}

export interface SignatureRequest extends ObjectWithId {
  document: number
  document_title?: string
  requested_version: number
  signed_version?: number
  requester?: SignatureUser
  signer?: SignatureUser
  signer_id?: number
  status?: SignatureRequestStatus
  message?: string
  rejection_reason?: string
  failure_message?: string
  created?: string
  viewed?: string
  completed?: string
  source_is_latest?: boolean
}

export interface SignatureProfile {
  configured: boolean
  original_filename?: string
  mime_type?: string
  modified?: string
}

export interface SignaturePlacement {
  page: number
  x: number
  y: number
  width: number
  height: number
}
