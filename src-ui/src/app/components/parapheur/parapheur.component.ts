import { CommonModule, DOCUMENT } from '@angular/common'
import {
  Component,
  DestroyRef,
  ElementRef,
  inject,
  OnInit,
  signal,
  ViewChild,
} from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { FormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import { NgbModal } from '@ng-bootstrap/ng-bootstrap'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import {
  SignatureRequest,
  SignatureRequestStatus,
  signatureRequestStatusName,
} from 'src/app/data/signature-request'
import {
  PdfRenderMode,
  PdfZoomLevel,
  PdfZoomScale,
  PngxPdfDocumentProxy,
} from '../common/pdf-viewer/pdf-viewer.types'
import {
  SignatureProfileService,
  SignatureRequestService,
  SignedDocumentService,
} from 'src/app/services/rest/signature-request.service'
import { SettingsService } from 'src/app/services/settings.service'
import { ToastService } from 'src/app/services/toast.service'
import { WebsocketStatusService } from 'src/app/services/websocket-status.service'
import { PageHeaderComponent } from '../common/page-header/page-header.component'
import { PngxPdfViewerComponent } from '../common/pdf-viewer/pdf-viewer.component'
import { SignatureProfileDialogComponent } from './signature-profile-dialog.component'
import { SignatureRejectionDialogComponent } from './signature-rejection-dialog.component'

@Component({
  selector: 'pngx-parapheur',
  standalone: true,
  templateUrl: './parapheur.component.html',
  styleUrls: ['./parapheur.component.scss'],
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    NgxBootstrapIconsModule,
    PageHeaderComponent,
    PngxPdfViewerComponent,
  ],
})
export class ParapheurComponent implements OnInit {
  private readonly requestsService = inject(SignatureRequestService)
  readonly profileService = inject(SignatureProfileService)
  readonly signedDocumentsService = inject(SignedDocumentService)
  private readonly settings = inject(SettingsService)
  private readonly toast = inject(ToastService)
  private readonly modal = inject(NgbModal)
  private readonly websocket = inject(WebsocketStatusService)
  private readonly document = inject<Document>(DOCUMENT)
  private readonly destroyRef = inject(DestroyRef)

  @ViewChild('viewerHost') viewerHost?: ElementRef<HTMLDivElement>
  @ViewChild('signatureBox') signatureBox?: ElementRef<HTMLDivElement>

  readonly requests = signal<SignatureRequest[]>([])
  readonly selected = signal<SignatureRequest>(null)
  readonly loading = signal(false)
  readonly signing = signal(false)
  readonly profileConfigured = signal(false)
  readonly SignatureRequestStatus = SignatureRequestStatus
  readonly signatureRequestStatusName = signatureRequestStatusName
  readonly PdfRenderMode = PdfRenderMode
  readonly PdfZoomScale = PdfZoomScale
  readonly PdfZoomLevel = PdfZoomLevel
  status: SignatureRequestStatus | null = null
  search = ''
  page = 1
  pageCount = 0
  documentUrl = ''

  get isSigner(): boolean {
    return !!this.settings.currentUser()?.is_signer
  }

  ngOnInit(): void {
    if (this.isSigner) {
      this.reload()
      this.profileService
        .getProfile()
        .subscribe((profile) => this.profileConfigured.set(profile.configured))
      this.websocket
        .onSignatureRequestUpdated()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(() => this.reload())
    }
  }

  reload(): void {
    this.loading.set(true)
    this.requestsService
      .list(1, 100, '-created', false, {
        status: this.status,
        search: this.search || null,
        assigned_to_me: true,
      })
      .subscribe({
        next: (result) => {
          this.requests.set(result.results)
          this.loading.set(false)
        },
        error: (error) => {
          this.loading.set(false)
          this.toast.showError($localize`Error retrieving signature requests`, error)
        },
      })
  }

  changeStatus(): void {
    this.selected.set(null)
    this.reload()
  }

  editSignature(): void {
    const dialog = this.modal.open(SignatureProfileDialogComponent, {
      backdrop: 'static',
      size: 'lg',
    })
    dialog.closed.subscribe(() => {
      this.profileService
        .getProfile()
        .subscribe((profile) => this.profileConfigured.set(profile.configured))
    })
  }

  open(request: SignatureRequest): void {
    if (!this.profileConfigured()) {
      this.editSignature()
      return
    }
    this.selected.set(request)
    this.page = 1
    this.documentUrl = this.requestsService.requestedDocumentUrl(request)
  }

  pdfLoaded(pdf: PngxPdfDocumentProxy): void {
    this.pageCount = pdf.numPages
    this.attachSignatureToPage()
  }

  pdfRendered(): void {
    this.attachSignatureToPage()
  }

  previousPage(): void {
    if (this.page > 1) {
      this.page--
      this.attachSignatureToPage()
    }
  }

  nextPage(): void {
    if (this.page < this.pageCount) {
      this.page++
      this.attachSignatureToPage()
    }
  }

  private currentPageElement(): HTMLElement | null {
    return (
      this.viewerHost?.nativeElement.querySelector(
        `.pdfViewer .page[data-page-number="${this.page}"]`
      ) || null
    )
  }

  attachSignatureToPage(): void {
    setTimeout(() => {
      const page = this.currentPageElement()
      const box = this.signatureBox?.nativeElement
      if (!page || !box) return
      page.appendChild(box)
      box.style.left = '5%'
      box.style.top = '5%'
      box.style.visibility = 'visible'
    })
  }

  pdfLoadError(error: unknown): void {
    this.toast.showError($localize`Unable to open the requested document`, error)
  }

  startDrag(event: PointerEvent): void {
    const box = this.signatureBox?.nativeElement
    const stage = this.currentPageElement()
    if (!box || !stage) return
    event.preventDefault()
    const startX = event.clientX
    const startY = event.clientY
    const initialLeft = box.offsetLeft
    const initialTop = box.offsetTop
    const move = (moveEvent: PointerEvent) => {
      box.style.left = `${Math.max(0, Math.min(stage.clientWidth - box.offsetWidth, initialLeft + moveEvent.clientX - startX))}px`
      box.style.top = `${Math.max(0, Math.min(stage.clientHeight - box.offsetHeight, initialTop + moveEvent.clientY - startY))}px`
    }
    const up = () => {
      this.document.removeEventListener('pointermove', move)
      this.document.removeEventListener('pointerup', up)
    }
    this.document.addEventListener('pointermove', move)
    this.document.addEventListener('pointerup', up)
  }

  confirmSignature(): void {
    if (this.signing()) return
    const request = this.selected()
    const box = this.signatureBox?.nativeElement
    const page = this.currentPageElement()
    if (!request || !box || !page) return
    const boxRect = box.getBoundingClientRect()
    const canvasRect = page.getBoundingClientRect()
    this.signing.set(true)
    this.requestsService
      .sign(request, {
        page: this.page,
        x: (boxRect.left - canvasRect.left) / canvasRect.width,
        y: (boxRect.top - canvasRect.top) / canvasRect.height,
        width: boxRect.width / canvasRect.width,
        height: boxRect.height / canvasRect.height,
      })
      .subscribe({
        next: () => {
          this.signing.set(false)
          this.selected.set(null)
          this.toast.showInfo($localize`Document signed and saved as a signed copy.`)
          this.reload()
        },
        error: (error) => {
          this.signing.set(false)
          this.toast.showError($localize`Unable to sign document`, error)
        },
      })
  }

  reject(request: SignatureRequest): void {
    const dialog = this.modal.open(SignatureRejectionDialogComponent, {
      backdrop: 'static',
    })
    dialog.closed.subscribe((reason: string) => {
      this.requestsService.reject(request, reason).subscribe({
        next: () => {
          this.selected.set(null)
          this.reload()
        },
        error: (error) =>
          this.toast.showError($localize`Unable to reject request`, error),
      })
    })
  }
}
