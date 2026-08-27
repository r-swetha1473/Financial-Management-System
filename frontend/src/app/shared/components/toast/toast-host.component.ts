import { Component, inject } from '@angular/core';

import { ToastService } from '../../../core/ui/toast.service';

@Component({
  selector: 'app-toast-host',
  standalone: true,
  template: `
    <div class="toast-container" aria-live="polite">
      @for (toast of toasts.toasts(); track toast.id) {
        <div class="toast" [class]="'toast toast--' + toast.kind">
          <strong>{{ toast.title }}</strong>
          @if (toast.body) {
            <p>{{ toast.body }}</p>
          }
        </div>
      }
    </div>
  `,
})
export class ToastHostComponent {
  readonly toasts = inject(ToastService);
}
