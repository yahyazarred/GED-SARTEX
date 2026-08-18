import { Injectable } from '@angular/core'
import { Observable, Subject, tap } from 'rxjs'
import {
  SignaturePlacement,
  SignatureProfile,
  SignatureRequest,
  SignatureUser,
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

  signers(): Observable<SignatureUser[]> {
    return this.http.get<SignatureUser[]>(this.getResourceUrl(null, 'signers'))
  }

  requestMany(data: {
    document: number
    requested_version: number
    signer_ids: number[]
    message?: string
  }): Observable<SignatureRequest[]> {
    return this.http
      .post<SignatureRequest[]>(this.getResourceUrl(null, 'batch'), data)
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
    return this.http.post<SignatureProfile>(this.getResourceUrl(), form)
  }

  fileUrl(): string {
    return `${environment.apiBaseUrl}signature_profile/file/`
  }

  previewUrl(): string {
    return `${environment.apiBaseUrl}signature_profile/preview/`
  }
}
