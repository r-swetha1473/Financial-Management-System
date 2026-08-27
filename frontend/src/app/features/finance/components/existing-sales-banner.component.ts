import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-existing-sales-banner',
  standalone: true,
  template: `
    <section class="workflow-banner">
      <div>
        <div class="workflow-banner__title">Existing sales records</div>
        <p class="workflow-banner__desc">
          Customer → Booking → Invoice → Receipt. These records are separate from O2C sales invoices and collections.
        </p>
        <div class="workflow-steps">
          @for (step of steps; track step) {
            <span class="workflow-step" [class.is-current]="step === currentStep">{{ step }}</span>
          }
        </div>
      </div>
    </section>
  `,
})
export class ExistingSalesBannerComponent {
  @Input() currentStep = '';
  readonly steps = ['Customer', 'Booking', 'Invoice', 'Receipt'];
}
