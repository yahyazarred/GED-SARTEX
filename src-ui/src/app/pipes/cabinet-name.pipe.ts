import { inject, Pipe, PipeTransform } from '@angular/core'
import {
  PermissionsService,
  PermissionType,
} from '../services/permissions.service'
import { CabinetService } from '../services/rest/cabinet.service'
import { ObjectNamePipe } from './object-name.pipe'

@Pipe({
  name: 'cabinetName',
})
export class CabinetNamePipe extends ObjectNamePipe implements PipeTransform {
  constructor() {
    super()
    this.permissionsService = inject(PermissionsService)
    this.permissionType = PermissionType.Cabinet
    this.objectService = inject(CabinetService)
  }
}
