import {
  Component,
  EventEmitter,
  Input,
  Output,
  inject,
  signal,
} from '@angular/core'
import { toSignal } from '@angular/core/rxjs-interop'
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'
import { map } from 'rxjs'
import { ObjectWithPermissions } from 'src/app/data/object-with-permissions'
import { User } from 'src/app/data/user'
import { UserService } from 'src/app/services/rest/user.service'
import { PermissionsFormComponent } from '../input/permissions/permissions-form/permissions-form.component'
import { SwitchComponent } from '../input/switch/switch.component'

@Component({
  selector: 'pngx-permissions-dialog',
  templateUrl: './permissions-dialog.component.html',
  styleUrls: ['./permissions-dialog.component.scss'],
  imports: [
    SwitchComponent,
    PermissionsFormComponent,
    FormsModule,
    ReactiveFormsModule,
  ],
})
export class PermissionsDialogComponent {
  activeModal = inject(NgbActiveModal)
  private userService = inject(UserService)

  readonly users = toSignal(
    this.userService.listAll().pipe(map((r) => r.results)),
    { initialValue: undefined as User[] }
  )
  readonly title = signal($localize`Set permissions`)
  readonly note = signal<string>(null)
  readonly buttonsEnabled = signal(true)
  private o: ObjectWithPermissions = undefined
  protectedUserId: number = null

  visibleUsers(): User[] {
    return (this.users() ?? []).filter(
      (user) => user.id !== this.protectedUserId
    )
  }

  @Output()
  public confirmClicked = new EventEmitter()

  @Input()
  set object(o: ObjectWithPermissions) {
    this.o = o
    this.title.set($localize`Edit permissions for ` + o['name'])
    const permissions = structuredClone(o.permissions)
    if (this.protectedUserId && permissions) {
      permissions.view.users = permissions.view.users.filter(
        (id) => id !== this.protectedUserId
      )
      permissions.change.users = permissions.change.users.filter(
        (id) => id !== this.protectedUserId
      )
    }
    this.form.patchValue({
      merge: true,
      permissions_form: {
        owner: o.owner,
        set_permissions: permissions,
      },
    })
  }

  get object(): ObjectWithPermissions {
    return this.o
  }

  public form = new FormGroup({
    permissions_form: new FormControl(),
    merge: new FormControl(true),
  })

  get permissions() {
    const setPermissions = this.form.get('permissions_form').value
      ?.set_permissions ?? {
      view: { users: [], groups: [] },
      change: { users: [], groups: [] },
    }
    if (this.protectedUserId) {
      for (const action of ['view', 'change'] as const) {
        setPermissions[action].users = Array.from(
          new Set([...(setPermissions[action].users ?? []), this.protectedUserId])
        )
      }
    }
    return {
      owner: this.form.get('permissions_form').value?.owner ?? null,
      set_permissions: setPermissions,
    }
  }

  get hint(): string {
    if (this.object) return null
    return this.form.get('merge').value
      ? $localize`Existing owner, user and group permissions will be merged with these settings.`
      : $localize`Any and all existing owner, user and group permissions will be replaced.`
  }

  cancelClicked() {
    this.activeModal.close()
  }

  confirm() {
    this.confirmClicked.emit({
      permissions: this.permissions,
      merge: this.form.get('merge').value,
    })
  }
}
