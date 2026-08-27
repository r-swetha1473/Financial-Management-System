import { Component, Input } from '@angular/core';

import { P2P_WORKFLOW_STEPS } from '../../../core/navigation/nav.config';

@Component({
  selector: 'app-p2p-banner',
  standalone: true,
  template: `
    <section class="workflow-banner workflow-banner--p2p">
      <div>
        <div class="workflow-banner__title">Procure-to-Pay</div>
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
export class P2pBannerComponent {
  @Input() currentStep = '';
  @Input() description = 'Vendor → Request → Order → Receipt → Supplier invoice → Payment → Payables';
  readonly steps = P2P_WORKFLOW_STEPS;
}
