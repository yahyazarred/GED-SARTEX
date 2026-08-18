import { ObjectWithId } from './object-with-id'

export interface Group extends ObjectWithId {
  name?: string

  user_count?: number // not implemented yet

  permissions?: string[]
  built_in?: boolean
  built_in_key?: string
}
