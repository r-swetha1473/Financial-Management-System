import { Pipe, PipeTransform } from '@angular/core';

import { formatCurrencyInr } from '../../core/utils/money.util';

@Pipe({ name: 'inr', standalone: true })
export class InrPipe implements PipeTransform {
  transform(value: string | number | null | undefined): string {
    return formatCurrencyInr(value);
  }
}
