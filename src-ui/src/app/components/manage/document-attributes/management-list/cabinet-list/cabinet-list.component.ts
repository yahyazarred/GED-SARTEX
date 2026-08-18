import { NgClass, NgTemplateOutlet } from '@angular/common'
import { Component, inject } from '@angular/core'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import {
  NgbDropdownModule,
  NgbPaginationModule,
} from '@ng-bootstrap/ng-bootstrap'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { CabinetEditDialogComponent } from 'src/app/components/common/edit-dialog/cabinet-edit-dialog/cabinet-edit-dialog.component'
import { Cabinet } from 'src/app/data/cabinet'
import { FILTER_HAS_CABINET_ANY } from 'src/app/data/filter-rule-type'
import { IfPermissionsDirective } from 'src/app/directives/if-permissions.directive'
import { SortableDirective } from 'src/app/directives/sortable.directive'
import { PermissionType } from 'src/app/services/permissions.service'
import { CabinetService } from 'src/app/services/rest/cabinet.service'
import { ManagementListComponent } from '../management-list.component'

@Component({
  selector: 'pngx-cabinet-list',
  templateUrl: './../management-list.component.html',
  styleUrls: ['./../management-list.component.scss'],
  imports: [
    SortableDirective,
    IfPermissionsDirective,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    NgClass,
    NgTemplateOutlet,
    NgbDropdownModule,
    NgbPaginationModule,
    NgxBootstrapIconsModule,
  ],
})
export class CabinetListComponent extends ManagementListComponent<Cabinet> {
  constructor() {
    super()
    this.service = inject(CabinetService)
    this.editDialogComponent = CabinetEditDialogComponent
    this.filterRuleType = FILTER_HAS_CABINET_ANY
    this.typeName = $localize`cabinet`
    this.typeNamePlural = $localize`cabinets`
    this.permissionType = PermissionType.Cabinet
  }

  getDeleteMessage(object: Cabinet) {
    return $localize`Do you really want to delete the cabinet "${object.name}"?`
  }
}
