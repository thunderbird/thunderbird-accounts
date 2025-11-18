type TicketFieldType = 'text'
  | 'textarea'
  | 'checkbox'
  | 'date'
  | 'integer'
  | 'decimal'
  | 'regexp'
  | 'partialcreditcard'
  | 'multiselect'
  | 'tagger'
  | 'lookup'
  | 'subject'
  | 'description';

export type TicketForm = {
  id: number
}

export type TicketField = {
  id: number,
  title: string,
  description: string,
  required: boolean,
  type: TicketFieldType,
  custom_field_options?: { id: number, name: string, value: string }[]
}

export interface ContactFieldsAPIResponse {
  success: boolean,
  ticket_form: TicketForm,
  ticket_fields: TicketField[],
}