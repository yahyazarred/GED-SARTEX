import { Component, inject } from '@angular/core'
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms'
import { EditDialogComponent } from 'src/app/components/common/edit-dialog/edit-dialog.component'
import { Cabinet } from 'src/app/data/cabinet'
import { DEFAULT_MATCHING_ALGORITHM } from 'src/app/data/matching-model'
import { IfOwnerDirective } from 'src/app/directives/if-owner.directive'
import { CabinetService } from 'src/app/services/rest/cabinet.service'
import { UserService } from 'src/app/services/rest/user.service'
import { SettingsService } from 'src/app/services/settings.service'
import { CheckComponent } from '../../input/check/check.component'
import { PermissionsFormComponent } from '../../input/permissions/permissions-form/permissions-form.component'
import { SelectComponent } from '../../input/select/select.component'
import { TextComponent } from '../../input/text/text.component'

@Component({
  selector: 'pngx-cabinet-edit-dialog',
  templateUrl: './cabinet-edit-dialog.component.html',
  imports: [
    CheckComponent,
    SelectComponent,
    PermissionsFormComponent,
    TextComponent,
    IfOwnerDirective,
    FormsModule,
    ReactiveFormsModule,
  ],
})
export class CabinetEditDialogComponent extends EditDialogComponent<Cabinet> {
  constructor() {
    super()
    this.service = inject(CabinetService)
    this.userService = inject(UserService)
    this.settingsService = inject(SettingsService)
  }

  getCreateTitle() {
    return $localize`Create new cabinet`
  }

  getEditTitle() {
    return $localize`Edit cabinet`
  }

  getForm(): FormGroup {
    return new FormGroup({
      name: new FormControl(''),
      matching_algorithm: new FormControl(DEFAULT_MATCHING_ALGORITHM),
      match: new FormControl(''),
      is_insensitive: new FormControl(true),
      permissions_form: new FormControl(null),
    })
  }
}
