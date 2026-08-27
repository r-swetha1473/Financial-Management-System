import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-finance-banner',
  standalone: true,
  template: `
    <section class="workflow-banner">
      <div>
        <div class="workflow-banner__title">Finance</div>
        <p class="workflow-banner__desc">{{ description }}</p>
      </div>
    </section>
  `,
})
export class FinanceBannerComponent {
  @Input() description = 'Operational expenses, income documents, accounts, GST totals, and reconciliation for this organization.';
}
