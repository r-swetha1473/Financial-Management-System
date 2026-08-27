import { Component, Input } from '@angular/core';

import { InrPipe } from '../../pipes/inr.pipe';

@Component({
  selector: 'app-summary-card',
  standalone: true,
  imports: [InrPipe],
  template: `
    <article class="card summary-card" [class]="toneClass">
      <span class="summary-card__label">{{ label }}</span>
      <span class="summary-card__value">{{ value | inr }}</span>
      @if (meta) {
        <span class="summary-card__meta">{{ meta }}</span>
      }
    </article>
  `,
})
export class SummaryCardComponent {
  @Input({ required: true }) label = '';
  @Input({ required: true }) value = '0.00';
  @Input() meta = '';
  @Input() tone: 'income' | 'expense' | 'cash' | 'receivable' | 'payable' = 'cash';

  get toneClass(): string {
    return `summary-card--${this.tone}`;
  }
}
