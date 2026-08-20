import {
  Component,
  Input,
  computed,
  forwardRef,
  inject,
  signal,
} from '@angular/core'
import { toSignal } from '@angular/core/rxjs-interop'
import {
  FormsModule,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
} from '@angular/forms'
import { NgSelectComponent } from '@ng-select/ng-select'
import { map } from 'rxjs/operators'
import { User } from 'src/app/data/user'
import { UserService } from 'src/app/services/rest/user.service'
import { AbstractInputComponent } from '../../abstract-input'

@Component({
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => PermissionsUserComponent),
      multi: true,
    },
  ],
  selector: 'pngx-permissions-user',
  templateUrl: './permissions-user.component.html',
  styleUrls: ['./permissions-user.component.scss'],
  imports: [NgSelectComponent, FormsModule, ReactiveFormsModule],
})
export class PermissionsUserComponent extends AbstractInputComponent<User[]> {
  private readonly excludedUserIdsSignal = signal<number[]>([])

  @Input()
  set excludedUserIds(value: number[]) {
    const next = value ?? []
    const current = this.excludedUserIdsSignal()
    if (
      current.length !== next.length ||
      current.some((id, index) => id !== next[index])
    ) {
      this.excludedUserIdsSignal.set([...next])
    }
  }

  get excludedUserIds(): number[] {
    return this.excludedUserIdsSignal()
  }

  private readonly userService = inject(UserService)
  readonly users = toSignal(
    this.userService.listAll().pipe(map((result) => result.results)),
    { initialValue: undefined as User[] }
  )
  readonly availableUsers = computed(() =>
    (this.users() ?? []).filter(
      (user) => !this.excludedUserIdsSignal().includes(user.id)
    )
  )
}
