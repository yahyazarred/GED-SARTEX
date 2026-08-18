import { Injectable } from '@angular/core'
import { Cabinet } from 'src/app/data/cabinet'
import { AbstractNameFilterService } from './abstract-name-filter-service'

@Injectable({ providedIn: 'root' })
export class CabinetService extends AbstractNameFilterService<Cabinet> {
  constructor() {
    super()
    this.resourceName = 'cabinets'
  }
}
