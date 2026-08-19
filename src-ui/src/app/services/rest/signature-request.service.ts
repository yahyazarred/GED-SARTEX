import { Injectable, signal } from '@angular/core'
import { Observable, Subject, tap } from 'rxjs'
import {
  SignaturePlacement,
  SignatureProfile,
  SignatureRequest,
  SignatureUser,
  SignedDocument,
} from 'src/app/data/signature-request'
import { environment } from 'src/environments/environment'
import { AbstractPaperlessService } from './abstract-paperless-service'

@Injectable({ providedIn: 'root' })
export class SignatureRequestService extends AbstractPaperlessService<SignatureRequest> {
  private readonly changed = new Subject<void>()

  constructor() {
    super()
    this.resourceName = 'signature_requests'
  }

  signers(document: number): Observable<SignatureUser[]> {
    return this.http.get<SignatureUser[]>(this.getResourceUrl(null, 'signers'), {
      params: { document },
    })
  }

  requestSignature(data: {
    document: number
    requested_version: number
    signer_id: number
    message?: string
  }): Observable<SignatureRequest> {
    return this.http
      .post<SignatureRequest>(this.getResourceUrl(), data)
      .pipe(tap(() => this.changed.next()))
  }

  sign(request: SignatureRequest, placement: SignaturePlacement) {
    return this.http
      .post<SignatureRequest>(this.getResourceUrl(request.id, 'sign'), placement)
      .pipe(tap(() => this.changed.next()))
  }

  reject(request: SignatureRequest, reason = '') {
    return this.http
      .post<SignatureRequest>(this.getResourceUrl(request.id, 'reject'), {
        reason,
      })
      .pipe(tap(() => this.changed.next()))
  }

  cancel(request: SignatureRequest) {
    return this.http
      .post<SignatureRequest>(this.getResourceUrl(request.id, 'cancel'), {})
      .pipe(tap(() => this.changed.next()))
  }

  onChanged(): Observable<void> {
    return this.changed.asObservable()
  }

  requestedDocumentUrl(request: SignatureRequest): string {
    return this.getResourceUrl(request.id, 'document')
  }
}

@Injectable({ providedIn: 'root' })
export class SignatureProfileService extends AbstractPaperlessService<any> {
  private readonly previewRevision = signal(Date.now())

  constructor() {
    super()
    this.resourceName = 'signature_profile'
  }

  getProfile(): Observable<SignatureProfile> {
    return this.http.get<SignatureProfile>(this.getResourceUrl())
  }

  upload(file: File): Observable<SignatureProfile> {
    const form = new FormData()
    form.append('signature', file)
    return this.http
      .post<SignatureProfile>(this.getResourceUrl(), form)
      .pipe(tap(() => this.previewRevision.set(Date.now())))
  }

  fileUrl(): string {
    return `${environment.apiBaseUrl}signature_profile/file/`
  }

  previewUrl(): string {
    return `${environment.apiBaseUrl}signature_profile/preview/?revision=${this.previewRevision()}`
  }
}

@Injectable({ providedIn: 'root' })
export class SignedDocumentService extends AbstractPaperlessService<SignedDocument> {
  constructor() {
    super()
    this.resourceName = 'signed_documents'
  }

  fileUrl(id: number): string {
    return this.getResourceUrl(id, 'file')
  }
}
