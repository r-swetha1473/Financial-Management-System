import { Component, Input } from '@angular/core';

import { O2C_WORKFLOW_STEPS } from '../../../core/navigation/nav.config';

@Component({
  selector: 'app-o2c-banner',
  standalone: true,
  template: `
    <section class="workflow-banner workflow-banner--o2c">
      <div>
        <div class="workflow-banner__title">Order-to-Cash</div>
        <p class="workflow-banner__desc">{{ description }}</p>
        <div class="workflow-steps">
          @for (step of steps; track step) {
            <span class="workflow-step" [class.is-current]="step === currentStep">{{ step }}</span>
          }
        </div>
      </div>
    </section>
  `,
})
export class O2cBannerComponent {
  @Input() currentStep = '';
  @Input() description = 'Customer → Quotation → Sales order → Delivery/Service → Sales invoice → Collection → Receivables';
  readonly steps = O2C_WORKFLOW_STEPS;
}
