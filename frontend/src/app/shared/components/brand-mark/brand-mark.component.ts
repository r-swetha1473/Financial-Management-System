import { Component, Input } from '@angular/core';

import { APP_ICON_PATH } from '../../../core/brand/brand';

@Component({
  selector: 'app-brand-mark',
  standalone: true,
  template: `
    <img
      class="brand-mark"
      [class.brand-mark--sm]="size === 'sm'"
      [class.brand-mark--md]="size === 'md'"
      [class.brand-mark--lg]="size === 'lg'"
      [src]="src"
      width="512"
      height="512"
      alt="LedgerFlow"
    />
  `,
})
export class BrandMarkComponent {
  readonly src = APP_ICON_PATH;

  @Input() size: 'sm' | 'md' | 'lg' = 'sm';
}
